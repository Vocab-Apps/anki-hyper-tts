"""
Utility functions for regular expressions. Builds on top of the standard library #re module.
"""

import re
import sys
import typing as t

if sys.version_info[:2] <= (3, 6):
    Pattern = t.Any
    Match = t.Any
else:
    Pattern = re.Pattern
    Match = re.Match


class MatchFullError(ValueError):
    """
    Raised when #match_full() cannot consume the full string.
    """

    def __init__(self, regex: "Pattern", string: str, endpos: int) -> None:
        self.regex = regex
        self.string = string
        self.endpos = endpos

    def __str__(self) -> str:
        return "could not consume whole string with regex {} (got until position {})".format(self.regex, self.endpos)


def match_full(expr: t.Union[str, "Pattern"], string: str) -> t.Iterable["Match"]:
    """
    Matches *expr* from the start of *string* and expects that it can be matched throughout.
    If it fails to consume the full string, a #MatchAllError will be raised.
    """

    if isinstance(expr, str):
        expr = re.compile(expr)

    offset = 0
    while offset < len(string):
        match = expr.match(string, offset)
        if not match:
            raise MatchFullError(expr, string, offset)
        offset = match.end()
        yield match
