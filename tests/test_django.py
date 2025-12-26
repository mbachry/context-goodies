import uuid
from unittest.mock import Mock

import context_goodies


def test_middleware_generates_request_id():
    get_response = Mock(return_value={})
    middleware = context_goodies.context_middleware(get_response)

    request = Mock()
    request.META = {}

    response = middleware(request)

    assert 'X-Request-Id' in response
    request_id = response['X-Request-Id']
    assert uuid.UUID(request_id)
    assert context_goodies.get_current_request_id() is None  # Should be cleared


def test_middleware_uses_existing_request_id():
    get_response = Mock(return_value={})
    middleware = context_goodies.context_middleware(get_response)

    req_id = str(uuid.uuid4())
    request = Mock()
    request.META = {'HTTP_X_REQUEST_ID': req_id}

    response = middleware(request)

    assert response['X-Request-Id'] == req_id


def test_middleware_context_cleanup():
    # Verify context is set during request and cleared after
    req_id_in_view = None

    def view(request):
        nonlocal req_id_in_view
        req_id_in_view = context_goodies.get_current_request_id()
        return {}

    middleware = context_goodies.context_middleware(view)
    request = Mock()
    request.META = {}

    middleware(request)

    assert req_id_in_view is not None
    assert context_goodies.get_current_request_id() is None
