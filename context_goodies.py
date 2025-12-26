import contextvars
import copy
import logging
import re
import uuid
from typing import Any

try:
    import gevent
    from gevent import monkey
    from gevent.pool import Group

    # use gevent features if gevent module is installed AND monkey
    # patching is enabled; this prevents turning them on by accident
    # when eg. a third-party module pulls gevent as dependency
    have_gevent = monkey.is_module_patched('threading')
except ImportError:
    have_gevent = False


_request_id = contextvars.ContextVar[str | None]('request_id', default=None)
_logging_data = contextvars.ContextVar[dict]('logging_data')
_greenlet_group = contextvars.ContextVar[Any | None]('greenlet_group', default=None)


def set_current_request_id(request_id: str | None) -> None:
    _request_id.set(request_id)
    start_new_greenlet_group()


def get_current_request_id() -> str | None:
    return _request_id.get()


def set_current_logging_data(extra: dict) -> None:
    """
    Replace current logging data with `extra`. The data isn't cleared
    automatically, so you have to set it back to `{}` in the beginning
    or end of current request, eg. in middleware's response handler,
    or worker pre-process hook.
    """
    _logging_data.set(copy.deepcopy(extra))


def get_current_logging_data() -> dict:
    return _logging_data.get({})


def update_logging_context(**kwargs: Any) -> None:
    """
    Sets extra logging data for current request. After calling this
    function, every log record will have `kwargs` appended
    automatically, ie. `log.info("foo")` will be effectively
    `log.info("foo", extra=kwargs)`.

    Assumes `logging_filters.ExtraDataFilter` is enabled in logging
    configuration.
    """
    set_current_logging_data({**get_current_logging_data(), **kwargs})


def kill_current_greenlet_group() -> None:
    if not have_gevent:
        return
    current_group = get_greenlet_group()
    current_group.kill(block=False)


def start_new_greenlet_group() -> None:
    _greenlet_group.set(None)


def get_greenlet_group() -> 'Group':
    assert have_gevent, 'using get_greenlet_group, but gevent module is missing'

    group = _greenlet_group.get()
    if group is None:
        group = Group()
        _greenlet_group.set(group)
    return group


# special case uwsgi, sentry and newrelic helper threads
re_greenlet_whitelist = re.compile(r'uwsgi|NR-|sentry')


def greenlet_startup_hook(new_greenlet: 'gevent.Greenlet') -> None:
    if re_greenlet_whitelist.search(str(new_greenlet)):
        return

    # automatically add to this request's group, even if started with
    # gevent.spawn()
    current_group = get_greenlet_group()
    current_group.add(new_greenlet)

    # propagate contextvars to new greenlet
    ctx = contextvars.copy_context()
    original_run = new_greenlet.run

    def run_with_context(*args, **kwargs):
        return ctx.run(original_run, *args, **kwargs)

    new_greenlet.run = run_with_context  # type: ignore[method-assign]


if have_gevent:
    gevent.Greenlet.add_spawn_callback(greenlet_startup_hook)


RESERVED = frozenset(
    (
        'stack',
        'name',
        'module',
        'funcName',
        'args',
        'msg',
        'levelno',
        'exc_text',
        'exc_info',
        'data',
        'created',
        'levelname',
        'msecs',
        'relativeCreated',
        'tags',
        'thread',
        'process',
        'threadName',
        'filename',
        'processName',
        'params',
        'lineno',
        'pathname',
        'stack_info',
        'taskName',
    ),
)


class ExtraDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        extra = {**get_current_logging_data(), **getattr(record, 'data', {})}
        for k, v in vars(record).items():
            if k in RESERVED:
                continue
            if k.startswith('_'):
                continue
            if '.' not in k and k not in ('culprit', 'server_name'):
                extra[k] = v
        if extra:
            record.extra = ' [{}]'.format(' | '.join(f'{k}={v}' for k, v in extra.items()))
        else:
            record.extra = ''
        return True


# uuid separated by hyphens:
human_uuid_re = re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


def context_middleware(get_response):
    """
    Middleware that sets up common things such as current request.
    Adds request_id attribute on request object, and sets X-Request-Id on response header.
    If a request id is set and it is not in the expected format, a new one is generated.
    """

    def middleware(request):
        request_id = request.META.get('HTTP_X_REQUEST_ID')
        if not request_id or not human_uuid_re.match(request_id):
            request_id = str(uuid.uuid4())
        set_current_request_id(request_id)
        update_logging_context(request_id=request_id)

        try:
            response = get_response(request)
            response['X-Request-Id'] = request_id
            return response
        finally:
            kill_current_greenlet_group()
            set_current_request_id(None)
            set_current_logging_data({})

    return middleware
