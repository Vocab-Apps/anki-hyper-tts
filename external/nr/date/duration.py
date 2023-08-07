import datetime
import typing as t
from dataclasses import dataclass

from .re import MatchFullError, match_full

if t.TYPE_CHECKING:
    import dateutil.relativedelta

SECONDS_PER_DAY = 3600 * 24
DAYS_PER_MONTH = 30.4375
DAYS_PER_YEAR = 365.25


@dataclass
class duration:
    """
    Represents an ISO 8601 duration.
    """

    years: int = 0
    months: int = 0
    weeks: int = 0
    days: int = 0
    hours: int = 0
    minutes: int = 0
    seconds: int = 0

    _fields = ["years", "months", "weeks", "days", "hours", "minutes", "seconds"]

    def __post_init__(self) -> None:
        for k in self._fields:
            if getattr(self, k) < 0:
                raise ValueError("{} cannot be negative".format(k))

    def __str__(self) -> str:
        parts = ["P"]
        for value, char in [(self.years, "Y"), (self.months, "M"), (self.weeks, "W"), (self.days, "D")]:
            if value != 0:
                parts.append("{}{}".format(value, char))
        has_t = False
        for value, char in [(self.hours, "H"), (self.minutes, "M"), (self.seconds, "S")]:
            if value != 0:
                if not has_t:
                    parts.append("T")
                    has_t = True
                parts.append("{}{}".format(value, char))
        return "".join(parts)

    def total_seconds(self) -> float:
        """
        Computes the total number of seconds in this duration.
        """

        return (
            self.years * DAYS_PER_YEAR * SECONDS_PER_DAY
            + self.months * DAYS_PER_MONTH * SECONDS_PER_DAY
            + self.weeks * 7 * SECONDS_PER_DAY
            + self.days * SECONDS_PER_DAY
            + self.hours * 3600
            + self.minutes * 60
            + self.seconds
        )

    def as_timedelta(self) -> datetime.timedelta:
        """
        Returns the seconds represented by this duration as a #datetime.timedelta object. The arguments
        and keyword arguments are forwarded to the #total_seconds() method.
        """

        return datetime.timedelta(seconds=self.total_seconds())

    def as_relativedelta(self) -> "dateutil.relativedelta.relativedelta":
        """
        Converts the #duration object to a #dateutil.relativedelta.relativedelta object. Requires
        the `python-dateutil` module.
        """

        from dateutil.relativedelta import relativedelta

        return relativedelta(
            years=self.years,
            months=self.months,
            weeks=self.weeks,
            days=self.days,
            hours=self.hours,
            minutes=self.minutes,
            seconds=self.seconds,
        )

    @classmethod
    def parse(cls, s: str) -> "duration":
        """
        Parses an ISO 8601 duration string into a #duration object.

        Thanks to https://stackoverflow.com/a/35936407.
        See also https://en.wikipedia.org/wiki/ISO_8601#Durations
        """

        parts = s.split("T")
        if not s or s[0] != "P" or len(parts) > 2:
            raise ValueError("Not an ISO 8601 duration string: {!r}".format(s))

        part_one = parts[0][1:]
        part_two = parts[1] if len(parts) == 2 else ""

        fields = {}

        try:
            for number, unit in (x.groups() for x in match_full(r"(\d+)(D|W|M|Y)", part_one)):
                number = int(number)
                if unit == "Y":
                    fields["years"] = number
                elif unit == "M":
                    fields["months"] = number
                elif unit == "W":
                    fields["weeks"] = number
                elif unit == "D":
                    fields["days"] = number

            for number, unit in (x.groups() for x in match_full(r"(\d+)(S|H|M)", part_two)):
                number = int(number)
                if unit == "H":
                    fields["hours"] = number
                elif unit == "M":
                    fields["minutes"] = number
                elif unit == "S":
                    fields["seconds"] = number

        except MatchFullError:
            raise ValueError("Not an ISO 8601 duration string: {!r}".format(s))

        return cls(**fields)
