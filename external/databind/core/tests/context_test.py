import typing as t

from typeapi import TypeHint

from databind.core.context import Context, Direction, Location, format_context_trace
from databind.core.settings import Settings


def test_format_context_trace() -> None:
    settings = Settings()
    location = Location.EMPTY

    def no_convert(*a: t.Any) -> None:
        raise NotImplementedError

    ctx1 = Context(
        parent=None,
        direction=Direction.SERIALIZE,
        value={"a": 1},
        datatype=TypeHint(t.Dict[str, int]),
        settings=settings,
        key=Context.ROOT,
        location=location,
        convert_func=no_convert,
    )
    ctx2 = Context(
        parent=ctx1,
        direction=Direction.SERIALIZE,
        value=1,
        datatype=TypeHint(int),
        settings=settings,
        key="a",
        location=location,
        convert_func=no_convert,
    )
    assert format_context_trace(ctx1) == "  $: TypeHint(typing.Dict[str, int])"
    assert format_context_trace(ctx2) == "  $: TypeHint(typing.Dict[str, int])\n" "  .a: TypeHint(int)"
