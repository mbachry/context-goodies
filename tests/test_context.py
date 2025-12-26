import uuid

import gevent
import pytest

import context_goodies as context


@pytest.fixture
def request_id():
    return str(uuid.uuid4())


@pytest.fixture(autouse=True)
def current_context(request_id):
    context.set_current_request_id(request_id)


@pytest.fixture(autouse=True)
def cleanup_process_context():
    yield
    context.set_current_request_id(None)


class TestGreenletGroups:
    def test_get_greenlet_group(self):
        group = context.get_greenlet_group()
        assert group is not None
        assert len(group) == 0

    def test_inherits_logging_context(self, request_id):
        context.update_logging_context(foo=1)
        context.set_current_request_id(request_id)

        def child():
            context.update_logging_context(bar=2)
            return {
                'request_id': context.get_current_request_id(),
                'logging_data': context.get_current_logging_data(),
            }

        greenlet = gevent.spawn(child)
        child_local_data = greenlet.get()

        assert context.get_current_logging_data() == {'foo': 1}
        assert child_local_data == {
            'logging_data': {'foo': 1, 'bar': 2},
            'request_id': request_id,
        }

    def test_new_group_on_new_request(self):
        old_group = context.get_greenlet_group()
        assert old_group is not None
        context.set_current_request_id(None)
        new_group = context.get_greenlet_group()
        assert new_group is not None
        assert new_group != old_group

    def test_kill_current_group(self):
        greenlet_old_group = gevent.spawn(lambda: gevent.sleep(60))

        context.set_current_request_id(None)
        greenlet_new_group = gevent.spawn(lambda: gevent.sleep(60))

        context.kill_current_greenlet_group()

        assert not greenlet_old_group.dead
        assert greenlet_new_group.dead


class TestContext:
    def test_update_logging_context(self):
        context.set_current_logging_data({'a': 1})
        context.update_logging_context(b=2)
        assert context.get_current_logging_data() == {'a': 1, 'b': 2}
