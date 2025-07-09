__version__ = "2.1.0"

__all__ = [
    "tzlocal",
    "duration",
    "date_format",
    "datetime_format",
    "time_format",
    "parse_date",
    "parse_datetime",
    "parse_time",
    "format_date",
    "format_datetime",
    "format_date",
    "format_set",
    "JAVA_OFFSET_DATETIME",
    "ISO_8601",
]

import datetime
import time
import typing as t

from .duration import duration
from .format import date_format, datetime_format, time_format
from .format_sets import ISO_8601, JAVA_OFFSET_DATETIME, format_set


def tzlocal() -> datetime.tzinfo:
    offset = time.altzone if time.daylight else time.timezone
    return datetime.timezone(datetime.timedelta(seconds=-offset))


def parse_date(fmt: t.Union[format_set, date_format, str], s: str) -> datetime.date:
    if isinstance(fmt, str):
        fmt = date_format.compile(fmt)
    return fmt.parse_date(s)


def parse_datetime(fmt: t.Union[format_set, datetime_format, str], s: str) -> datetime.datetime:
    if isinstance(fmt, str):
        fmt = datetime_format.compile(fmt)
    return fmt.parse_datetime(s)


def parse_time(fmt: t.Union[format_set, time_format, str], s: str) -> datetime.time:
    if isinstance(fmt, str):
        fmt = time_format.compile(fmt)
    return fmt.parse_time(s)


def format_date(fmt: t.Union[format_set, date_format, str], d: datetime.date) -> str:
    if isinstance(fmt, str):
        fmt = date_format.compile(fmt)
    return fmt.format_date(d)


def format_datetime(fmt: t.Union[format_set, datetime_format, str], dt: datetime.datetime) -> str:
    if isinstance(fmt, str):
        fmt = datetime_format.compile(fmt)
    return fmt.format_datetime(dt)


def format_time(fmt: t.Union[format_set, time_format, str], t: datetime.time) -> str:
    if isinstance(fmt, str):
        fmt = time_format.compile(fmt)
    return fmt.format_time(t)
