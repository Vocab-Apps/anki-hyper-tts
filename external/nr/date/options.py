import abc
import datetime
import enum
import re
import typing as t
from dataclasses import dataclass


class DatetimeComponentType(enum.Enum):
    Date = enum.auto()
    Time = enum.auto()


class DatetimeComponent(enum.Enum):
    Year = "year"
    Month = "month"
    Day = "day"
    Hour = "hour"
    Minute = "minute"
    Second = "second"
    Microsecond = "microsecond"
    Timezone = "tzinfo"

    @property
    def type(self) -> DatetimeComponentType:
        if self in (DatetimeComponent.Year, DatetimeComponent.Month, DatetimeComponent.Day):
            return DatetimeComponentType.Date
        if self in (
            DatetimeComponent.Hour,
            DatetimeComponent.Minute,
            DatetimeComponent.Second,
            DatetimeComponent.Microsecond,
            DatetimeComponent.Timezone,
        ):
            return DatetimeComponentType.Time
        raise RuntimeError(f"unexpected Component enumeration value: {self!r}")


@dataclass
class _FormatOption:
    """
    Represents a special character in a date format string, which in turn represents a particular
    date or time component.
    """

    #: The character that the format option is represented in a format string. Must be a string of
    #: length 1 (one).
    char: str

    #: The component of a datetime construct that the format option represents.
    component: DatetimeComponent

    #: The regular expression that is used to capture the value represented by the format option
    #: when parsing a date/time string. This expression must not contain any capturing groups.
    regex: str


class IFormatOption(_FormatOption, metaclass=abc.ABCMeta):
    """
    Abstract metaclass on top of #_FormatOption, adding methods to the interface for parsing and
    formatting values represented by the format option.
    """

    @abc.abstractmethod
    def parse_string(self, s: str) -> t.Any:
        """Called to parse then value extracted by the *regex*."""

    @abc.abstractmethod
    def format_value(self, dt: datetime.datetime, v: t.Any) -> str:
        """Called to format the value of the respective #Component to a string."""


@dataclass
class NumericFormatOption(IFormatOption):
    """
    Default implementation for format options that represent a plain number component in the date.
    """

    format: t.Callable[[int], str]
    post_parse: t.Optional[t.Callable[[str], int]] = None

    def parse_string(self, s: str) -> t.Any:
        if self.post_parse is not None:
            return self.post_parse(s)
        return int(s)

    def format_value(self, dt: datetime.datetime, v: t.Any) -> str:
        assert isinstance(v, int), f"expected int to {self!r}.format_value()"
        return self.format(v)


@dataclass
class TimezoneFormatOption(IFormatOption):
    regex: str = r"(?:Z|[-+]\d{2}(?::?\d{2})?)"

    def parse_string(self, s: str) -> datetime.tzinfo:
        match = re.match(self.regex, s)
        if not match:
            raise ValueError("not a timezone string: {!r}".format(s))
        if s == "Z":
            return datetime.timezone.utc
        else:
            s = s.replace(":", "")
            sign = -1 if s[0] == "-" else 1
            hours = int(s[1:3])
            minutes = int(s[3:5] or "00")
            seconds = sign * (hours * 3600 + minutes * 60)
            return datetime.timezone(datetime.timedelta(seconds=seconds))

    def format_value(self, dt: datetime.datetime, v: t.Any) -> str:
        assert v is None or isinstance(v, datetime.tzinfo), f"expected datetime.tzinfo, got {v!r}"
        if v is None:
            return ""
        elif v == datetime.timezone.utc:
            return "Z"
        else:
            assert isinstance(v, datetime.tzinfo)
            utcoffset = v.utcoffset(dt)
            # NOTE Copied from CPython 3.7 datetime.py _format_offset()
            string = ""
            if utcoffset is not None:
                if utcoffset.days < 0:
                    sign = "-"
                    utcoffset = -utcoffset
                else:
                    sign = "+"
                off = utcoffset.total_seconds()
                hh, mm = divmod(off, 60 * 60)
                mm, ss = divmod(mm, 60)
                ss, ms = divmod(ss, 1)
                string += "%s%02d:%02d" % (sign, hh, mm)
                if ss or ms:
                    string += ":%02d" % ss
                    if ms:
                        string += ".%06d" % ms
            return string


class FormatOptions(enum.Enum):
    """
    Enumeration of all the available format options.
    """

    Year = NumericFormatOption("Y", DatetimeComponent.Year, r"\d{4}", lambda v: str(v).rjust(4, "0"))
    Month = NumericFormatOption("m", DatetimeComponent.Month, r"\d{2}", lambda v: str(v).rjust(2, "0"))
    Day = NumericFormatOption("d", DatetimeComponent.Day, r"\d{2}", lambda v: str(v).rjust(2, "0"))
    Hour = NumericFormatOption("H", DatetimeComponent.Hour, r"\d{2}", lambda v: str(v).rjust(2, "0"))
    Minute = NumericFormatOption("M", DatetimeComponent.Minute, r"\d{2}", lambda v: str(v).rjust(2, "0"))
    Second = NumericFormatOption("S", DatetimeComponent.Second, r"\d{2}", lambda v: str(v).rjust(2, "0"))
    Microsecond = NumericFormatOption(
        "f",
        DatetimeComponent.Microsecond,
        r"\d+",
        format=lambda v: str(v).rjust(6, "0").rstrip("0") or "0",
        post_parse=lambda v: int(str(int(v) * (10 ** max(6 - len(v), 0)))[:6]),
    )
    Timezone = TimezoneFormatOption("z", DatetimeComponent.Timezone)

    @classmethod
    def get(cls, char: str) -> t.Optional[IFormatOption]:
        # TODO(NiklasRosenstein): Room for optimization by caching available format options in dict.
        return next((x.value for x in cls if x.value.char == char), None)
