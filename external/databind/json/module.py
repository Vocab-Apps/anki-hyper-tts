from typing import Iterator

from databind.core.context import Context
from databind.core.converter import Converter, Module
from databind.json.settings import JsonConverter


class JsonModule(Module):
    """The JSON module combines all converters provided by the #databind.json package in one usable module. The
    direction in which the converters should convert must be specified with the *direction* argument. Alternatively,
    use one of the convenience static methods #serializing() and #deserializing()."""

    def __init__(self) -> None:
        super().__init__(__name__ + ".JsonModule")

        import pathlib
        import uuid

        from nr.date import duration

        from databind.json.converters import (
            AnyConverter,
            CollectionConverter,
            DatetimeConverter,
            DecimalConverter,
            EnumConverter,
            LiteralConverter,
            MappingConverter,
            OptionalConverter,
            PlainDatatypeConverter,
            SchemaConverter,
            StringifyConverter,
            UnionConverter,
        )

        self.register(AnyConverter())
        self.register(CollectionConverter())
        self.register(DatetimeConverter())
        self.register(DecimalConverter())
        self.register(EnumConverter())
        self.register(MappingConverter())
        self.register(OptionalConverter())
        self.register(PlainDatatypeConverter())
        self.register(UnionConverter())
        self.register(SchemaConverter())
        self.register(StringifyConverter(uuid.UUID, name="JsonModule:uuid.UUID"), first=True)

        # NOTE(NiklasRosenstein): It is important that we have the converter for `Path` appear before the converter
        #       for `PurePath` for the `issubclass()` checks in the converter to match appropriately due to Liskov
        #       substition principle (otherwise you would end up deserializing a `Path` field as a `PurePath` but
        #       then actually serialize it as a `Path` which causes an error, "expected Path, got PurePath").
        self.register(StringifyConverter(pathlib.PurePath, name="JsonModule:pathlib.PurePath"), first=True)
        self.register(StringifyConverter(pathlib.Path, name="JsonModule:pathlib.Path"), first=True)
        self.register(StringifyConverter(duration, duration.parse, name="JsonModule:nr.date.duration"), first=True)
        self.register(LiteralConverter())

        self.register(JsonConverterSupport(), first=True)


class JsonConverterSupport(Module):
    """
    Handles the JsonConverter setting.
    """

    def __init__(self) -> None:
        super().__init__(__name__ + ".JsonConverterSupport")

    def get_converters(self, ctx: Context) -> Iterator[Converter]:
        converter_setting = ctx.get_setting(JsonConverter)
        if converter_setting is not None:
            yield converter_setting.supplier()
        yield from super().get_converters(ctx)
