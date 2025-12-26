# context-goodies

Helper functions to maintain process/thread/coroutine local data in
trusted microservices.

## Install

`pip install context-goodies`

You can also "vendor" the module by copying `context_goodies.py` to
your project. There are no pypi dependencies.

## Request ID

Call `set_current_request_id` to set a new request id. If using
Django, add `context_goodies.context_middleware` to
`MIDDLEWARES` to maintain request ids automatically. Note it assumes
an internal microservice API and trusted clients.

## Logging context

Call `update_logging_context` to add new data to every log line,
eg. `update_logging_context(user_id=user_id)`.

### Logging config example

Filter and formatter to log context data added with `update_logging_context`:

```
'filters': {
    'extra': {'()': 'context_goodies.ExtraDataFilter'},
},
'formatters': {'verbose': {'format': '[%(name)s][%(levelname)s] %(message)s%(extra)s'}},
'handlers': {
    'console': {
        'level': 'DEBUG',
        'class': 'logging.StreamHandler',
        'formatter': 'verbose',
        'filters': ['extra'],
    },
},
```

## Greenlet handling

Django middleware automatically groups all greenlets spawned during
request lifetime and kills the entire group in the request finalizer
to avoid memory leaks.
