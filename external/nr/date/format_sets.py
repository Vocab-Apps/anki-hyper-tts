import datetime
import typing as t
from dataclasses import dataclass, field

from .format import _datetime_format, date_format, datetime_format, time_format


def _formulate_parse_error(name: str, formats: t.Sequence[_datetime_format], s: str) -> ValueError:
    return ValueError(
        f'"{s}" does not match {name} date formats ({len(formats)}):'
        + "".join(f"\n  | {x.format_str}" for x in formats)
    )


@dataclass
class format_set:
    """
    Format sets represent a group of date, time and dateime formats. When formatting a value, it will
    use the first format defined in the group. When parsing, it will attempt to parse the value using
    all of the provided formats (stopping on the first successful parse).

    #format_datetime() can take into account the #date_formats and #time_formats as well if the
    *partial* parameter is set to #True.
    """

    name: str
    reference_url: t.Optional[str] = None
    date_formats: t.List[date_format] = field(default_factory=list)
    time_formats: t.List[time_format] = field(default_factory=list)
    datetime_formats: t.List[datetime_format] = field(default_factory=list)

    def parse_date(self, s: str) -> datetime.date:
        if not self.date_formats:
            raise ValueError(f"{self.name} has no date formats")
        for fmt in self.date_formats:
            try:
                return fmt.parse_date(s)
            except ValueError:
                pass
        raise _formulate_parse_error(self.name, self.date_formats, s)

    def format_date(self, d: datetime.date) -> str:
        if not self.date_formats:
            raise ValueError(f"{self.name} has no date formats")
        return self.date_formats[0].format_date(d)

    def parse_datetime(self, s: str, partial: bool = False) -> datetime.datetime:
        if not self.datetime_formats:
            raise ValueError(f"{self.name} has no datetime formats")
        for fmt in self.datetime_formats:
            try:
                return fmt.parse_datetime(s)
            except ValueError:
                pass
        if partial:
            try:
                return datetime.datetime.combine(self.parse_date(s), datetime.time.min)
            except ValueError:
                pass
            try:
                return datetime.datetime.combine(datetime.date.min, self.parse_time(s))
            except ValueError:
                pass
        raise _formulate_parse_error(self.name, self.datetime_formats, s)

    def format_datetime(self, dt: datetime.datetime) -> str:
        if not self.datetime_formats:
            raise ValueError(f"{self.name} has no datetime formats")
        return self.datetime_formats[0].format_datetime(dt)

    def parse_time(self, s: str) -> datetime.time:
        if not self.time_formats:
            raise ValueError(f"{self.name} has no time formats")
        for fmt in self.time_formats:
            try:
                return fmt.parse_time(s)
            except ValueError:
                pass
        raise _formulate_parse_error(self.name, self.time_formats, s)

    def format_time(self, t: datetime.time) -> str:
        if not self.time_formats:
            raise ValueError(f"{self.name} has no time formats")
        return self.time_formats[0].format_time(t)


#: Datetime format for parsing the format produced by `java.time.OffsetDateTime.toString()`.
JAVA_OFFSET_DATETIME = format_set(
    name="Java OffsetDateTime",
    reference_url="https://docs.oracle.com/javase/8/docs/api/java/time/OffsetDateTime.html#toString--",
    datetime_formats=[
        datetime_format.compile(r"%Y-%m-%dT%H:%M(:%S(\.%f)?)?%z?", regex_mode=True),
    ],
)


#: Date/time formats for parsing ISO 8601 dates and times.
#:
#: Supported ISO 8601 date formats are (implemented using the `%Y%m%d` format options):
#:
#: * `YYYY`
#: * `YYYY-MM` or `YYYYMM`
#: * `YYYY-MM-DD` or `YYYYMMDD`
#:
#: Note: ISO Week / ISO Week and day are not currently supported.
#:
#: Supported time formats are (implemented using the `%H%M%S%f` format options)
#:
#: * `hh`
#: * `hh:mm` or `hhmm`
#: * `hh:mm:ss` or `hhmmss`
#: * `hh:mm:ss.SSSSSS` (up to 6 sub-second digits)
#:
#: Supported timezone offset formats are (implemented using the `%z` format option):
#:
#: * `Z` (UTC)
#: * `+HH:MM` or `-HH:MM`
#: * `+HHMM` or `-HHMM`
#: * `+HH` or `-HH`
#:
#: Datetimes are simply concatenations of the possible date, time and offset formats, where
#: the date and time are separated by a `T`.
ISO_8601 = format_set(
    name="ISO 8061",
    reference_url="https://en.wikipedia.org/wiki/ISO_8601",
    date_formats=[
        date_format.compile(r"%Y(-%m(-%d)?)?", regex_mode=True),
        date_format.compile(r"%Y(%m%d?)?", regex_mode=True),
    ],
    time_formats=[
        time_format.compile(r"%H(:%M(:%S(\.%f)?)?)?%z?", regex_mode=True),
        time_format.compile(r"%H(%M%S??)?%z?", regex_mode=True),
    ],
    datetime_formats=[],
)

# Construct the datetime_formats, combining each element from the time and date formats.
for _i in range(2):
    ISO_8601.datetime_formats.append(
        datetime_format.compile(
            ISO_8601.date_formats[_i].format_str + "T" + ISO_8601.time_formats[_i].format_str,
            regex_mode=True,
        )
    )
del _i
