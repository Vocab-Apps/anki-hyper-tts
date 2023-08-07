import abc
import logging
import typing as t
from textwrap import indent

from typeapi import ClassTypeHint, type_repr

from databind.core.utils import exception_safe_str

if t.TYPE_CHECKING:
    from databind.core.context import Context

logger = logging.getLogger(__name__)


class Converter(abc.ABC):
    """Interface for converting a value from one representation to another."""

    def __repr__(self) -> str:
        return f"{type_repr(type(self))}()"

    def convert(self, ctx: "Context") -> t.Any:
        """Convert the value in *ctx* to another value.

        The default implementation will dispatch to #serialize() and #deserialize() depending on the direction
        given by the context. Because these methods raise #NotImplementedError, an instance of #Converter without
        custom logic will effectively be a no-op.

        Argument:
          ctx: The conversion context that contains the direction, value, datatype, settings, location and allows
            you to recursively continue the conversion process for sub values.

        Raises:
          NotImplementedError: If the converter does not support the conversion for the given context.
          NoMatchingConverter: If the converter is delegating to other converters, to point out that none
            of its delegates can convert the value.

        Returns:
          The new value.
        """

        if ctx.direction.is_serialize():
            return self.serialize(ctx)
        elif ctx.direction.is_deserialize():
            return self.deserialize(ctx)
        else:
            raise RuntimeError(f"unexpected direction: {ctx.direction!r}")

    def serialize(self, ctx: "Context") -> t.Any:
        raise NotImplementedError

    def deserialize(self, ctx: "Context") -> t.Any:
        raise NotImplementedError


class Module(Converter):
    """A module is a collection of #Converter#s."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.converters: t.List[Converter] = []

    def __repr__(self) -> str:
        return f"Module({self.name!r})"

    def register(self, converter: Converter, first: bool = False) -> None:
        assert isinstance(converter, Converter), converter
        if first:
            self.converters.insert(0, converter)
        else:
            self.converters.append(converter)

    def get_converters(self, ctx: "Context") -> t.Iterator[Converter]:
        for converter in self.converters:
            if isinstance(converter, Module):
                yield from converter.get_converters(ctx)
            else:
                yield converter

    def convert(self, ctx: "Context") -> t.Any:
        errors: t.List[t.Tuple[Converter, Exception]] = []
        for converter in self.get_converters(ctx):
            try:
                return converter.convert(ctx)
            except NotImplementedError:
                pass
            except ConversionError as exc:
                errors.append((converter, exc))
        if len(errors) == 1:
            raise errors[0][1]
        raise NoMatchingConverter(self, ctx, errors)


class ConversionError(Exception):
    """For any errors that occur during conversion."""

    def __init__(
        self,
        origin: Converter,
        context: "Context",
        message: str,
        errors: "t.Sequence[t.Tuple[Converter, Exception]] | None" = None,
    ) -> None:
        self.origin = origin
        self.context = context
        self.message = message
        self.errors = errors or []

    @exception_safe_str
    def __str__(self) -> str:
        import textwrap

        from databind.core.context import format_context_trace

        message = f'{self.message}\n\nTrace:\n{textwrap.indent(format_context_trace(self.context), "  ")}'
        if self.errors:
            message += "\n\nThe following errors have been reported by converters:"
            for converter, exc in self.errors:
                if str(exc):
                    message += f"\n\n  {converter}: {indent(str(exc), '    ').lstrip()}"
        return message

    @staticmethod
    def expected(
        origin: Converter,
        ctx: "Context",
        types: t.Union[type, t.Sequence[type]],
        got: t.Optional[type] = None,
    ) -> "ConversionError":
        if not isinstance(types, t.Sequence):
            types = (types,)
        expected = "|".join(type_repr(t) for t in types)
        got = type(ctx.value) if got is None else got
        return ConversionError(origin, ctx, f"expected {expected}, got {type_repr(got)} instead")


class NoMatchingConverter(ConversionError):
    """If no converter matched to convert the value and datatype in the context."""

    def __init__(self, origin: Converter, context: "Context", errors: "t.List[t.Tuple[Converter, Exception]]") -> None:
        super().__init__(
            origin,
            context,
            f"no {context.direction.name.lower()}r for `{context.datatype}` and payload of type "
            f"`{type_repr(type(context.value))}`",
            errors,
        )


class DelegateToClassmethodConverter(Converter):
    """
    This converter delegaes to the methods defined by name to perform serialization and deserialization of a type. This
    converter is usually used in conjunction with settings that override the converteer to be used in a specifc
    scenario (e.g. such as de/serializing JSON with the #databind.json.settings.JsonConverter setting).
    """

    def __init__(
        self,
        serialized_type: t.Union[t.Type[t.Any], t.Tuple[t.Type[t.Any], ...], None] = None,
        *,
        serialize: "str | None" = None,
        deserialize: "str | None" = None,
    ) -> None:
        self._serialized_type = serialized_type
        self._serialize = serialize
        self._deserialize = deserialize

    def serialize(self, ctx: "Context") -> t.Any:
        if self._serialize is None or not isinstance(ctx.datatype, ClassTypeHint):
            raise NotImplementedError
        if not isinstance(ctx.value, ctx.datatype.type):
            raise ConversionError.expected(self, ctx, ctx.datatype.type)
        method: t.Callable[[t.Any], t.Any] = getattr(ctx.datatype.type, self._serialize)
        return method(ctx.value)

    def deserialize(self, ctx: "Context") -> t.Any:
        if self._deserialize is None or not isinstance(ctx.datatype, ClassTypeHint):
            raise NotImplementedError
        if self._serialized_type is not None and not isinstance(ctx.value, self._serialized_type):
            raise ConversionError.expected(self, ctx, self._serialized_type)
        method: t.Callable[[t.Any], t.Any] = getattr(ctx.datatype.type, self._deserialize)
        return method(ctx.value)
