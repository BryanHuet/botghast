"""
Unit tests of log.py: timestamps are written in Europe/Paris time, daylight saving included.
"""

import datetime
import logging

import pytest

from log import ParisTimeFormatter, logger


def record_at(utc):
    record = logging.LogRecord('botghast', logging.INFO, __file__, 1, 'message', None, None)
    record.created = utc.replace(tzinfo=datetime.timezone.utc).timestamp()
    return record


@pytest.mark.parametrize('utc, paris', [
    (datetime.datetime(2026, 1, 15, 12, 0, 0), '2026-01-15 13:00:00'),   # winter: UTC+1
    (datetime.datetime(2026, 7, 15, 12, 0, 0), '2026-07-15 14:00:00'),   # summer: UTC+2
    (datetime.datetime(2026, 12, 31, 23, 30, 0), '2027-01-01 00:30:00'),  # day change
])
def test_time_is_converted_to_paris(utc, paris):
    assert ParisTimeFormatter().formatTime(record_at(utc)) == paris


def test_format_of_a_line():
    line = ParisTimeFormatter().format(record_at(datetime.datetime(2026, 7, 15, 12, 0, 0)))
    assert line == '2026-07-15 14:00:00 [INFO]: message'


def test_custom_date_format():
    record = record_at(datetime.datetime(2026, 7, 15, 12, 0, 0))
    assert ParisTimeFormatter().formatTime(record, datefmt='%H:%M') == '14:00'


def test_shared_logger_is_configured_once():
    import importlib

    import log

    handlers = list(logger.handlers)
    importlib.reload(log)
    assert log.logger is logger
    assert logger.handlers == handlers
    assert all(isinstance(handler.formatter, ParisTimeFormatter) for handler in handlers)
