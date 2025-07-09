""" The #databind.json package implements the capabilities to bind JSON payloads to objects and the reverse. """

import json
import typing as t

from databind.core import ObjectMapper, Setting, Settings
from databind.json.module import JsonModule
from databind.json.settings import JsonConverter

__version__ = "4.5.2"
__all__ = [
    "dump",
    "dumps",
    "get_object_mapper",
    "JsonConverter",
    "JsonModule",
    "JsonType",
    "load",
    "loads",
]

T = t.TypeVar("T")
JsonType = t.Union[
    None,
    bool,
    int,
    float,
    str,
    t.Dict[str, t.Any],
    t.List[t.Any],
]


def get_object_mapper(settings: "Settings | None" = None) -> "ObjectMapper[t.Any, JsonType]":
    mapper = ObjectMapper[t.Any, JsonType](settings)
    mapper.module.register(JsonModule())
    return mapper


@t.overload
def load(
    value: t.Any,
    type_: "t.Type[T]",
    filename: "str | None" = None,
    settings: "t.List[Setting] | None" = None,
) -> T:
    ...


@t.overload
def load(
    value: t.Any,
    type_: t.Any,
    filename: "str | None" = None,
    settings: "t.List[Setting] | None" = None,
) -> t.Any:
    ...


def load(
    value: t.Any,
    type_: t.Any,
    filename: "str | None" = None,
    settings: "t.List[Setting] | None" = None,
) -> t.Any:
    return get_object_mapper().deserialize(value, type_, filename, settings)


@t.overload
def loads(
    value: str,
    type_: "t.Type[T]",
    filename: "str | None" = None,
    settings: "t.List[Setting] | None" = None,
) -> T:
    ...


@t.overload
def loads(
    value: str,
    type_: t.Any,
    filename: "str | None" = None,
    settings: "t.List[Setting] | None" = None,
) -> t.Any:
    ...


def loads(
    value: str,
    type_: t.Any,
    filename: "str | None" = None,
    settings: "t.List[Setting] | None" = None,
) -> t.Any:
    return load(json.loads(value), type_, filename, settings)


def dump(
    value: t.Any,
    type_: t.Any,
    filename: "str | None" = None,
    settings: "t.List[Setting] | None" = None,
) -> JsonType:
    return get_object_mapper().serialize(value, type_, filename, settings)


def dumps(
    value: t.Any,
    type_: t.Any,
    filename: "str | None" = None,
    settings: "t.List[Setting] | None" = None,
    indent: t.Union[int, str, None] = None,
    sort_keys: bool = False,
) -> str:
    return json.dumps(dump(value, type_, filename, settings), indent=indent, sort_keys=sort_keys)
