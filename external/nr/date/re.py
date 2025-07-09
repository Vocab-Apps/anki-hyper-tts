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


def matchiter(expr: t.Union[str, "Pattern"], string: str, flags: int = 0) -> t.Iterable["Match"]:
    """
    Like #re.finditer(), but uses #re.match() instead of #re.search().
    """

    if isinstance(expr, str):
        expr = re.compile(expr, flags)

    start = 0
    while True:
        match = expr.match(string, start)
        if not match:
            break
        start = match.end()
        yield match


def match_full(expr: t.Union[str, "Pattern"], string: str, flags: int = 0) -> t.Iterable["Match"]:
    """
    Like #matchiter(), but raises a #MatchAllError if the *expr* does not match any number of
    times over the entire string from start to finish.
    """

    if isinstance(expr, str):
        expr = re.compile(expr, flags)

    end = 0
    for match in matchiter(expr, string, flags):
        yield match
        end = match.end()

    if end != len(string):
        raise MatchFullError(expr, string, end)
