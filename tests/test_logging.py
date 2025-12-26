import logging

import context_goodies


def test_extra_data_filter():
    f = context_goodies.ExtraDataFilter()
    record = logging.LogRecord('name', logging.INFO, 'pathname', 1, 'msg', (), None)

    context_goodies.set_current_logging_data({'foo': 'bar'})

    assert f.filter(record)
    assert '[foo=bar]' in record.extra  # type: ignore[attr-defined]


def test_extra_data_filter_with_record_data():
    f = context_goodies.ExtraDataFilter()
    record = logging.LogRecord('name', logging.INFO, 'pathname', 1, 'msg', (), None)
    record.data = {'baz': 'qux'}

    context_goodies.set_current_logging_data({'foo': 'bar'})

    assert f.filter(record)
    assert 'foo=bar' in record.extra  # type: ignore[attr-defined]
    assert 'baz=qux' in record.extra  # type: ignore[attr-defined]


def test_extra_data_filter_reserved_keys():
    f = context_goodies.ExtraDataFilter()
    record = logging.LogRecord('name', logging.INFO, 'pathname', 1, 'msg', (), None)

    context_goodies.set_current_logging_data({})

    # Normally standard attributes are reserved.
    # Let's add a non-reserved attribute directly to record
    record.my_custom_attr = 123

    assert f.filter(record)
    assert 'my_custom_attr=123' in record.extra  # type: ignore[attr-defined]
