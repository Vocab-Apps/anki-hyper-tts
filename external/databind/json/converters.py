import base64
import datetime
import decimal
import enum
import typing as t

from typeapi import (
    AnnotatedTypeHint,
    ClassTypeHint,
    LiteralTypeHint,
    TupleTypeHint,
    TypeHint,
    UnionTypeHint,
    get_annotations,
    type_repr,
)

from databind.core import (
    Alias,
    Context,
    ConversionError,
    Converter,
    DateFormat,
    DeserializeAs,
    Direction,
    ExtraKeys,
    Field,
    Precision,
    Remainder,
    Schema,
    SerializeDefaults,
    Strict,
    Union,
    convert_to_schema,
    get_annotation_setting,
    get_fields_expanded,
)

T = t.TypeVar("T")


def _int_lossless(v: float) -> int:
    """Convert *v* to an integer only if the conversion is lossless, otherwise raise an error."""

    assert v % 1.0 == 0.0, f"expected int, got {v!r}"
    return int(v)


def _bool_from_str(s: str) -> bool:
    """Converts *s* to a boolean value based on common truthy keywords."""

    if s.lower() in ("yes", "true", "on", "enabled"):
        return True
    if s.lower() in ("no", "false", "off", "disabled"):
        return True
    raise ValueError(f"not a truthy keyword: {s!r}")


def _unwrap_annotated(hint: TypeHint) -> TypeHint:
    if isinstance(hint, AnnotatedTypeHint):
        return hint[0]
    return hint


class AnyConverter(Converter):
    """A converter for #typing.Any and #object typed values, which will return them unchanged in any case."""

    def convert(self, ctx: Context) -> t.Any:
        datatype = _unwrap_annotated(ctx.datatype)
        is_any_type = isinstance(datatype, ClassTypeHint) and datatype.type in (object, t.Any)
        if is_any_type:
            return ctx.value
        raise NotImplementedError


class CollectionConverter(Converter):
    _FORBIDDEN_COLLECTIONS = (str, bytes, bytearray, memoryview, t.Mapping)

    def __init__(self, json_collection_type: t.Type[t.Collection[t.Any]] = list) -> None:
        self.json_collection_type = json_collection_type

    def convert(self, ctx: Context) -> t.Any:
        datatype = _unwrap_annotated(ctx.datatype)
        if (
            not isinstance(datatype, ClassTypeHint)
            or not issubclass(datatype.type, t.Collection)
            or issubclass(datatype.type, self._FORBIDDEN_COLLECTIONS)
        ) and not isinstance(datatype, TupleTypeHint):
            raise NotImplementedError

        # NamedTuples with type information are a lot like data classes, so we delegate to the SchemaConverter.
        if (
            isinstance(datatype, ClassTypeHint)
            and issubclass(datatype.type, tuple)
            and getattr(datatype.type, "__annotations__", None)
        ):
            schema = Schema(
                fields={
                    name: Field(
                        # We need to evaluate the type hint to remove forward references. The source is needed to
                        # understand the context in which forward references must be evaluated.
                        datatype=TypeHint(type_, source=datatype.type).evaluate(),
                    )
                    for name, type_ in getattr(datatype.type, "__annotations__").items()
                },
                constructor=datatype.type,
                type=datatype.type,
            )
            if ctx.direction.is_serialize():
                return SchemaConverter().serialize_from_schema(ctx, schema)
            elif ctx.direction.is_deserialize():
                return SchemaConverter().deserialize_from_schema(ctx, schema)
            else:
                assert False, ctx.direction

        # TODO(@niklas.rosenstein): Should we support an object-based JSON representation for collections.namedtuple?

        if isinstance(datatype, TupleTypeHint) and not datatype.repeated:
            # Require that the length of the input data matches the tuple.
            item_types_iterator = iter(datatype)
            python_type: type = tuple

            def _length_check() -> None:
                if len(ctx.value) != len(datatype):
                    raise ConversionError(
                        self, ctx, f"expected a tuple of length {len(datatype)}, found {len(ctx.value)}"
                    )

        else:
            candidates = set()
            for current in datatype.recurse_bases():
                if issubclass(current.type, t.Collection) and len(current.args) == 1:
                    candidates.add(current.args[0])
            if len(candidates) == 0:
                raise ConversionError(self, ctx, f"could not find item type in {datatype}")
            elif len(candidates) > 1:
                raise ConversionError(self, ctx, f"found multiple item types in {datatype}: {candidates}")

            item_type = TypeHint(next(iter(candidates)))
            item_types_iterator = iter(lambda: item_type, None)
            python_type = datatype.type

            def _length_check() -> None:
                pass

        values: t.Iterable[t.Any] = (
            ctx.spawn(val, item_type, idx).convert()
            for idx, (val, item_type) in enumerate(zip(ctx.value, item_types_iterator))
        )

        if ctx.direction == Direction.SERIALIZE:
            if not isinstance(ctx.value, python_type):
                raise ConversionError.expected(self, ctx, python_type)
            _length_check()
            return self.json_collection_type(values)  # type: ignore[call-arg]

        else:
            if not isinstance(ctx.value, t.Collection) or isinstance(ctx.value, self._FORBIDDEN_COLLECTIONS):
                raise ConversionError.expected(self, ctx, t.Collection)
            _length_check()
            values = list(values)
            if python_type == list:
                return values
            elif hasattr(python_type, "_fields"):  # For collections.namedtuple
                return python_type(*values)

            try:
                return python_type(values)
            except TypeError:
                # We assume that the native list is an appropriate placeholder for whatever specific Collection type
                # was chosen in the value's datatype.
                return values


class DatetimeConverter(Converter):
    """A converter for #datetime.datetime, #datetime.date and #datetime.time that represents the serialized form as
    strings formatted using the #nr.date module. The converter respects the #DateFormat setting."""

    DEFAULT_DATE_FMT = DateFormat(".ISO_8601")
    DEFAULT_TIME_FMT = DEFAULT_DATE_FMT
    DEFAULT_DATETIME_FMT = DEFAULT_DATE_FMT

    def convert(self, ctx: Context) -> t.Any:
        datatype = _unwrap_annotated(ctx.datatype)
        if not isinstance(datatype, ClassTypeHint):
            raise NotImplementedError

        date_type = datatype.type
        if date_type not in (datetime.date, datetime.time, datetime.datetime):
            raise NotImplementedError

        datefmt = ctx.get_setting(DateFormat) or (
            self.DEFAULT_DATE_FMT
            if date_type == datetime.date
            else (
                self.DEFAULT_TIME_FMT
                if date_type == datetime.time
                else self.DEFAULT_DATETIME_FMT
                if date_type == datetime.datetime
                else None
            )
        )
        assert datefmt is not None

        if ctx.direction == Direction.DESERIALIZE:
            if isinstance(ctx.value, date_type):
                return ctx.value
            elif isinstance(ctx.value, str):
                try:
                    dt: t.Any = datefmt.parse(date_type, ctx.value)
                except ValueError as exc:
                    raise ConversionError(self, ctx, str(exc))
                assert isinstance(dt, date_type)
                return dt
            raise ConversionError.expected(self, ctx, date_type, type(ctx.value))

        else:
            if not isinstance(ctx.value, date_type):
                raise ConversionError.expected(self, ctx, date_type, type(ctx.value))
            return datefmt.format(ctx.value)  # type: ignore[type-var]


class DecimalConverter(Converter):
    """A converter for #decimal.Decimal values to and from JSON as strings."""

    def __init__(self, strict_by_default: bool = True) -> None:
        self.strict_by_default = strict_by_default

    def convert(self, ctx: Context) -> t.Any:
        datatype = _unwrap_annotated(ctx.datatype)
        if not isinstance(datatype, ClassTypeHint) or not issubclass(datatype.type, decimal.Decimal):
            raise NotImplementedError

        strict = ctx.get_setting(Strict) or Strict(self.strict_by_default)
        precision = ctx.get_setting(Precision)
        context = precision.to_decimal_context() if precision else None

        if ctx.direction == Direction.DESERIALIZE:
            if (not strict.enabled and isinstance(ctx.value, (int, float))) or isinstance(ctx.value, str):
                return decimal.Decimal(ctx.value, context)
            raise ConversionError.expected(self, ctx, str, type(ctx.value))

        else:
            if not isinstance(ctx.value, decimal.Decimal):
                raise ConversionError.expected(self, ctx, decimal.Decimal, type(ctx.value))
            return str(ctx.value)


class EnumConverter(Converter):
    """JSON converter for enum values.

    Converts #enum.IntEnum values to integers and #enum.Enum values to strings. Note that combined integer flags
    are not supported and cannot be serializ

    #Alias#es on the type annotation of an enum field are considered as aliases for the field name to be used
    in the value's serialized form as opposed to its value name defined in code.

    Example:

    ```py
    import enum, typing
    from databind.core.settings import Alias

    class Pet(enum.Enum):
      CAT = enum.auto()
      DOG = enum.auto()
      LION: typing.Annotated[int, Alias('KITTY')] = enum.auto()
    ```
    """

    def _discover_alias(self, enum_type: t.Type[enum.Enum], member_name: str) -> t.Optional[Alias]:
        # TODO (@NiklasRosenstein): Take into account annotations of the base classes?
        hint = TypeHint(get_annotations(enum_type).get(member_name))
        return get_annotation_setting(hint, Alias)

    def convert(self, ctx: Context) -> t.Any:
        datatype = _unwrap_annotated(ctx.datatype)
        if not isinstance(datatype, ClassTypeHint):
            raise NotImplementedError
        if not issubclass(datatype.type, enum.Enum):
            raise NotImplementedError

        value = ctx.value
        enum_type = datatype.type

        if ctx.direction == Direction.SERIALIZE:
            if type(value) is not enum_type:
                raise ConversionError.expected(self, ctx, enum_type, type(value))
            if issubclass(enum_type, enum.IntEnum):
                return value.value
            if issubclass(enum_type, enum.Enum):
                alias = self._discover_alias(enum_type, value.name)
                if alias and alias.aliases:
                    return alias.aliases[0]
                return value.name
            assert False, enum_type

        else:
            if issubclass(enum_type, enum.IntEnum):
                if not isinstance(value, int):
                    raise ConversionError.expected(self, ctx, int, type(value))
                try:
                    return enum_type(value)
                except ValueError as exc:
                    raise ConversionError(self, ctx, str(exc))
            if issubclass(enum_type, enum.Enum):
                if not isinstance(value, str):
                    raise ConversionError.expected(self, ctx, str, type(value))
                for enum_value in enum_type:
                    alias = self._discover_alias(enum_type, enum_value.name)
                    if alias and value in alias.aliases:
                        return enum_value
                try:
                    return enum_type[value]
                except KeyError:
                    raise ConversionError(self, ctx, f"{value!r} is not a member of enumeration {datatype}")
            assert False, enum_type


class MappingConverter(Converter):
    def __init__(self, json_mapping_type: t.Type[t.Mapping[str, t.Any]] = dict) -> None:
        self.json_mapping_type = json_mapping_type

    def convert(self, ctx: Context) -> t.Any:
        datatype = _unwrap_annotated(ctx.datatype)

        # Find the key and value types of the mapping.
        if not isinstance(datatype, ClassTypeHint) or not issubclass(datatype.type, t.Mapping):
            raise NotImplementedError
        candidates = set()
        for current in datatype.recurse_bases():
            if issubclass(current.type, t.Mapping) and len(current.args) == 2:
                candidates.add(current.args)
        if len(candidates) == 0:
            raise ConversionError(self, ctx, f"could not find key/value type in {datatype}")
        elif len(candidates) > 1:
            raise ConversionError(self, ctx, f"found multiple key/value types in {datatype}: {candidates}")

        key_type, value_type = next(iter(candidates))

        if not isinstance(ctx.value, t.Mapping):
            raise ConversionError.expected(self, ctx, t.Mapping)

        result = {}
        for key, value in ctx.value.items():
            value = ctx.spawn(value, value_type, key).convert()
            key = ctx.spawn(key, key_type, f"Key({key!r})").convert()
            result[key] = value

        if ctx.direction == Direction.DESERIALIZE and datatype.type != dict:
            # We assume that the runtime type is constructible from a plain dictionary.
            try:
                return datatype.type(result)  # type: ignore[call-arg]
            except TypeError:
                # We expect this exception to occur for example if the annotated type is an abstract class like
                # t.Mapping; in which case we just assume that "dict' is a fine type to return.
                return result
        elif ctx.direction == Direction.SERIALIZE and self.json_mapping_type != dict:
            # Same for the JSON output type.
            return self.json_mapping_type(result)  # type: ignore[call-arg]

        return result


class OptionalConverter(Converter):
    def convert(self, ctx: Context) -> t.Any:
        datatype = _unwrap_annotated(ctx.datatype)
        if not isinstance(datatype, UnionTypeHint) or not datatype.has_none_type():
            raise NotImplementedError
        if ctx.value is None:
            return None
        return ctx.spawn(ctx.value, datatype.without_none_type(), None).convert()


class PlainDatatypeConverter(Converter):
    """A converter for the plain datatypes #bool, #bytes, #int, #str, #float and #null.

    Arguments:
      direction (Direction): The direction in which to convert (serialize or deserialize).
      strict_by_default (bool): Whether to use strict type conversion on values by default if no other
        information on strictness is given. This defaults to `True`. With strict conversion enabled,
        loss-less type conversions are disabled (such as casting a string to an integer). Note that
        serialization is _always_ strict, only the deserialization is controlled with this option or
        the #Strict setting.
    """

    # Map for (source_type, target_type)
    _strict_adapters: t.Dict[t.Tuple[type, type], t.Callable[[t.Any], t.Any]] = {
        (bytes, bytes): lambda d: base64.b64encode(d).decode("ascii"),
        (str, bytes): base64.b64decode,
        (str, str): str,
        (int, int): int,
        (float, float): float,
        (int, float): float,
        (float, int): _int_lossless,
        (bool, bool): bool,
        (type(None), type(None)): lambda x: x,
    }

    # Used only during deserialization if the #fieldinfo.strict is disabled.
    _nonstrict_adapters = _strict_adapters.copy()
    _nonstrict_adapters.update(
        {
            (str, int): int,
            (str, float): float,
            (str, bool): _bool_from_str,
            (int, str): str,
            (float, str): str,
            (bool, str): str,
            (type(None), type(None)): lambda x: x,
        }
    )

    def __init__(self, strict_by_default: bool = True) -> None:
        self.strict_by_default = strict_by_default

    def convert(self, ctx: Context) -> t.Any:
        datatype = _unwrap_annotated(ctx.datatype)
        if not isinstance(datatype, ClassTypeHint):
            raise NotImplementedError
        if datatype.type not in {k[0] for k in self._strict_adapters}:
            raise NotImplementedError

        source_type = type(ctx.value)
        target_type = datatype.type
        strict = (
            (ctx.get_setting(Strict) or Strict(self.strict_by_default))
            if ctx.direction == Direction.DESERIALIZE
            else Strict(True)
        )
        adapters = self._strict_adapters if strict.enabled else self._nonstrict_adapters
        adapter = adapters.get((source_type, target_type))
        if adapter is None:
            raise ConversionError.expected(self, ctx, target_type, source_type)

        try:
            return adapter(ctx.value)
        except ValueError as exc:
            raise ConversionError(self, ctx, str(exc)) from exc


class SchemaConverter(Converter):
    """Converter for type hints that can be adapter to a #databind.core.schema.Schema object.

    This converter respects the following settings:

    * #Alias
    * #SerializeDefaults
    """

    def __init__(
        self,
        json_mapping_type: t.Type[t.MutableMapping[str, t.Any]] = dict,
        convert_to_schema: t.Callable[[TypeHint], Schema] = convert_to_schema,
        serialize_defaults: bool = True,
    ) -> None:
        self.json_mapping_type = json_mapping_type
        self.convert_to_schema = convert_to_schema
        self.serialize_defaults = serialize_defaults

    @staticmethod
    def _get_alias_setting(ctx: Context, field_name: str) -> Alias:
        return ctx.get_setting(Alias) or Alias(field_name)

    def _get_schema(self, ctx: Context) -> Schema:
        deserialize_as = ctx.get_setting(DeserializeAs)
        if deserialize_as is not None:
            datatype = TypeHint(deserialize_as.type)
        else:
            datatype = _unwrap_annotated(ctx.datatype)

        try:
            return self.convert_to_schema(datatype)
        except ValueError as exc:
            raise NotImplementedError(str(exc))

    def serialize_from_schema(self, ctx: Context, schema: Schema) -> t.MutableMapping[str, t.Any]:
        try:
            is_instance = isinstance(ctx.value, schema.type)
        except TypeError:
            # The type may not support isinstance() checks (e.g. typing.TypedDict).
            pass
        else:
            if not is_instance:
                raise ConversionError.expected(self, ctx, schema.type)

        serialize_defaults = (ctx.get_setting(SerializeDefaults) or SerializeDefaults(self.serialize_defaults)).enabled
        result = self.json_mapping_type()

        def _get_field_value(field_name: str, field: Field) -> t.Any:
            if isinstance(ctx.value, t.Mapping):
                return ctx.value[field_name]  # TODO (@NiklasRosenstein): Respect non-required fields
            else:
                return getattr(ctx.value, field_name)

        remainder_field: t.Optional[t.Tuple[str, Field]] = None
        remainder_values: t.Optional[t.Mapping[str, t.Any]] = None

        for field_name, field in schema.fields.items():
            field_ctx = ctx.spawn(_get_field_value(field_name, field), field.datatype, field_name)
            remainder = field_ctx.get_setting(Remainder)
            if remainder and remainder.enabled:
                if remainder_field is not None:
                    raise ConversionError(
                        self, ctx, f"found at least two remainder fields ({remainder_field[0]!r}, {field_name!r})"
                    )
                # We look at the remainder field later.
                remainder_field = field_name, field
                assert not field.flattened, "remainder field cannot be flattened"
            value = field_ctx.convert()
            if field.flattened:
                if not isinstance(value, t.Mapping):
                    raise ConversionError(
                        self,
                        field_ctx,
                        f"field {field_name!r} is flattened but its serialized form is not "
                        f"a mapping (got {type(value).__name__!r})",
                    )
                assert result.keys().isdisjoint(value.keys()), result.keys() & value.keys()
                result.update(value)
            else:
                if serialize_defaults or not field.has_default() or field_ctx.value != field.get_default():
                    alias = self._get_alias_setting(field_ctx, field_name).aliases[0]
                    if remainder and remainder.enabled:
                        if not isinstance(value, t.Mapping):
                            raise ConversionError(
                                self,
                                ctx,
                                f"cannot expand remainder field {field_name!r} of type {type(value).__name__}",
                            )
                        remainder_values = value
                    else:
                        result[alias] = value

        if remainder_field:
            assert remainder_values is not None
            duplicate_keys = result.keys() & remainder_values.keys()
            if duplicate_keys:
                raise ConversionError(
                    self, ctx, f"keys in remainder field collide with other fields in the schema: {duplicate_keys}"
                )
            result.update(remainder_values)

        return result

    def deserialize_from_schema(self, ctx: Context, schema: Schema) -> t.Any:
        if not isinstance(ctx.value, t.Mapping):
            raise ConversionError.expected(self, ctx, t.Mapping)

        source = ctx.value
        used_keys = set()
        remainder_field: t.Optional[t.Tuple[str, Field]] = None

        def _extract_field(
            result: t.Dict[str, t.Any], field_name: str, field: Field, keep_aliased: bool
        ) -> t.Dict[str, t.Any]:
            nonlocal remainder_field

            field_ctx = ctx.spawn(None, field.datatype, field_name)
            remainder = field_ctx.get_setting(Remainder)
            if remainder and remainder.enabled:
                if remainder_field is not None:
                    raise ConversionError(
                        self, ctx, f"encountered at least two remainder fields ({remainder_field[0]!r}, {field_name!r})"
                    )
                remainder_field = (field_name, field)
                return result

            aliases = self._get_alias_setting(field_ctx, field_name).aliases
            for alias in aliases:
                if alias in source:
                    result[alias if keep_aliased else field_name] = source[alias]
                    used_keys.add(alias)
                    break
            else:
                if field.required:
                    other_aliases = f' (or {", ".join(map(repr, aliases[1:]))})' if len(aliases) > 1 else ""
                    raise ConversionError(self, ctx, f"missing required field: {aliases[0]!r}{other_aliases}")
            return result

        def _extract_fields(fields: t.Dict[str, Field]) -> t.Dict[str, t.Any]:
            result: t.Dict[str, t.Any] = {}
            for field_name, field in fields.items():
                _extract_field(result, field_name, field, True)
            return result

        result = {}
        expanded = get_fields_expanded(schema)
        for field_name, field in schema.fields.items():
            if field.flattened:
                assert field_name in expanded, field_name
                value = ctx.spawn(_extract_fields(expanded[field_name]), field.datatype, field_name).convert()
            else:
                container = _extract_field({}, field_name, field, False)
                if not container:
                    assert not field.required or (remainder_field and remainder_field[0] == field_name)
                    if field.has_default():
                        result[field_name] = field.get_default()
                    continue
                value = ctx.spawn(container[field_name], field.datatype, field_name).convert()
            result[field_name] = value

        # TODO(@NiklasRosenstein): Support deserializing as a type different than what is defined in the schema.

        unused_keys = source.keys() - used_keys
        if remainder_field:
            remainders = {k: ctx.value[k] for k in unused_keys}
            result[remainder_field[0]] = ctx.spawn(
                remainders, remainder_field[1].datatype, remainder_field[0]
            ).convert()
        elif unused_keys:
            extra_keys = ctx.get_setting(ExtraKeys) or ExtraKeys(False)
            extra_keys.inform(self, ctx, unused_keys)

        return schema.constructor(**result)

    def deserialize(self, ctx: Context) -> t.Any:
        schema = self._get_schema(ctx)
        return self.deserialize_from_schema(ctx, schema)

    def serialize(self, ctx: Context) -> t.MutableMapping[str, t.Any]:
        schema = self._get_schema(ctx)
        return self.serialize_from_schema(ctx, schema)


class StringifyConverter(Converter):
    """A useful helper converter that matches on a given type or its subclasses and converts them to a string for
    serialization and deserializes them from a string using the type's constructor."""

    def __init__(
        self,
        type_: t.Type[T],
        parser: t.Optional[t.Callable[[str], T]] = None,
        formatter: t.Callable[[T], str] = str,
        name: t.Optional[str] = None,
    ) -> None:
        assert isinstance(type_, type), type_
        self.type_ = type_
        self.parser: t.Callable[[str], T] = parser or type_
        self.formatter = formatter
        self.name = name

    def __repr__(self) -> str:
        if self.name is not None:
            return f"StringifyConverter(name={self.name!r})"
        else:
            return (
                f"StringifyConverter(type={type_repr(self.type_)}, parser={self.parser!r}, "
                f"formatter={self.formatter!r})"
            )

    def convert(self, ctx: Context) -> t.Any:
        datatype = _unwrap_annotated(ctx.datatype)
        if not isinstance(datatype, ClassTypeHint) or not issubclass(datatype.type, self.type_):
            raise NotImplementedError

        if ctx.direction == Direction.DESERIALIZE:
            if not isinstance(ctx.value, str):
                raise ConversionError.expected(self, ctx, str)
            try:
                return self.parser(ctx.value)
            except (TypeError, ValueError) as exc:
                raise ConversionError(self, ctx, str(exc))

        else:
            if not isinstance(ctx.value, datatype.type):
                raise ConversionError.expected(self, ctx, datatype.type)
            return self.formatter(ctx.value)


class UnionConverter(Converter):
    """Converter for union types. The following kinds of union types are supported:

    * A #typing.Union (represented as #UnionTypeHint) instance, in which case the members are deserialized in the
      the #Union.NESTED mode, using the class name as the discriminator keys.

        ```py
        AOrB = A | B   # ex.: {"type": "A", "A": {...}}
        ```

    * A #typing.Annotated annotated with the #Union setting (represented as #AnnotatedTypeHint)

        ```py
        from databind.core.settings import Union
        AOrB = typing.Annotated[A | B, Union({'a': A, 'b': B}, Union.KEYED)]  # ex.: {"a": {...}}
        ```

    * A class that is decorated with the #Union setting

        ```py
        import dataclasses
        from databind.core.settings import Union

        @Union(style=Union.FLAT)
        class Base(abc.ABC):
          pass

        @Union.register(Base, 'a')
        @dataclasses.dataclass
        class A(Base):
          pass

        # ...
        # ex.: {"type": "a", ...}
        ```

    !!! note

        Note that the union members should be concrete types, not generic aliases, because the converter cannot check
        if an object is an instance of an alias. This is an implementation detail of the
        #databind.core.union.UnionMembers implementations.

    More Examples:

    ```py
    import abc
    import typing
    from databind.core.settings import Union

    AOrB = typing.Annotated[
      typing.Union[A, B],
      Union({'A': A, 'B': B}, Union.NESTED, 'uses', 'with')
    ]

    @Union('!my.package.plugins')
    class Plugin(abc.ABC):
      @abc.abstractmethod
      def activate(self) -> None: ...
    ```
    """

    def _get_deserialize_member_name(
        self, ctx: Context, value: t.Mapping[str, t.Any], style: str, discriminator_key: str
    ) -> str:
        """Identify the name of the union member of the given serialized *value* and return it. How that name is
        determined depends on the *style*."""

        self._check_style_compatibility(ctx, style, value)

        # TODO (@NiklasRosenstein): Support Union.BEST_MATCH
        if style in (Union.NESTED, Union.FLAT):
            if discriminator_key not in value:
                raise ConversionError(self, ctx, f"missing discriminator key {discriminator_key!r} in mapping")
            member_name = value[discriminator_key]
            if not isinstance(member_name, str):
                raise ConversionError.expected(self, ctx.spawn(member_name, str, discriminator_key), str)
        elif style == Union.KEYED:
            if len(value) != 1:
                raise ConversionError(
                    self, ctx, f"expected exactly one key to act as the discriminator, got {len(value)} key(s)"
                )
            member_name = next(iter(value))
            assert isinstance(member_name, str)
        else:
            raise ConversionError(self, ctx, f"unsupported Union.style: {style!r}")

        assert isinstance(member_name, str), (member_name, value)
        return member_name

    def _check_style_compatibility(self, ctx: Context, style: str, value: t.Any) -> None:
        if not isinstance(value, t.MutableMapping) and style in (Union.FLAT,):
            raise ConversionError(self, ctx, f"The Union.{style.upper()} style is not supported for plain member types")

    def convert(self, ctx: Context) -> t.Any:
        datatype = ctx.datatype
        union: t.Optional[Union]
        if isinstance(datatype, UnionTypeHint):
            if datatype.has_none_type():
                raise NotImplementedError("unable to handle Union type with None in it")
            if not all(isinstance(a, ClassTypeHint) for a in datatype):
                raise NotImplementedError(f"members of plain Union must be concrete types: {datatype}")
            members = {t.cast(ClassTypeHint, a).type.__name__: a for a in datatype}
            if len(members) != len(datatype):
                raise NotImplementedError(f"members of plain Union cannot have overlapping type names: {datatype}")
            union = Union(members, Union.BEST_MATCH)
        elif isinstance(datatype, (AnnotatedTypeHint, ClassTypeHint)):
            union = ctx.get_setting(Union)
            if union is None:
                raise NotImplementedError
        else:
            raise NotImplementedError

        style = union.style
        if style == Union.BEST_MATCH:
            errors = []
            for member_name in union.members.get_type_ids():
                member_type = union.members.get_type_by_id(member_name)
                try:
                    return ctx.spawn(ctx.value, member_type, None).convert()
                except ConversionError as exc:
                    errors.append((exc.origin, exc))
            raise ConversionError(
                self,
                ctx,
                f"unable to {ctx.direction.name.lower()} any union member",
                errors,
            )

        discriminator_key = union.discriminator_key
        is_deserialize = ctx.direction == Direction.DESERIALIZE

        if is_deserialize:
            # Identify the member type to deserialize to.
            if not isinstance(ctx.value, t.Mapping):
                raise ConversionError.expected(self, ctx, t.Mapping)
            member_name = self._get_deserialize_member_name(ctx, ctx.value, style, discriminator_key)
            member_type = union.members.get_type_by_id(member_name)

        else:
            # Identify the member type based on the Python value type.
            member_name = union.members.get_type_id(type(ctx.value))
            member_type = union.members.get_type_by_id(member_name)

        nesting_key = union.nesting_key or member_name
        type_hint = TypeHint(member_type) if not isinstance(member_type, TypeHint) else member_type

        if is_deserialize:
            # Forward deserialization of the value using the newly identified type hint.
            # TODO (@NiklasRosenstein): Support Union.BEST_MATCH.
            if style == Union.NESTED:
                if nesting_key not in ctx.value:
                    raise ConversionError(self, ctx, f"missing nesting key {nesting_key!r} in mapping")
                child_context = ctx.spawn(ctx.value[nesting_key], type_hint, nesting_key)
            elif style == Union.FLAT:
                child_context = ctx.spawn(dict(ctx.value), type_hint, None)
                # Don't pass down the discriminator key.
                t.cast(t.Dict[str, t.Any], child_context.value).pop(discriminator_key)
            elif style == Union.KEYED:
                child_context = ctx.spawn(ctx.value[member_name], type_hint, member_name)
            else:
                raise ConversionError(self, ctx, f"unsupported union style: {style!r}")

        else:
            child_context = ctx.spawn(ctx.value, type_hint, None)

        result = child_context.convert()

        if is_deserialize:
            return result

        else:
            self._check_style_compatibility(ctx, style, result)
            # Bring the serialized value into shape.
            if style == Union.NESTED:
                result = {discriminator_key: member_name, member_name: result}
            elif style == Union.FLAT:
                assert isinstance(result, t.MutableMapping), type(result)
                result[discriminator_key] = member_name
            elif style == Union.KEYED:
                result = {member_name: result}
            elif style == Union.BEST_MATCH:
                pass
            else:
                raise ConversionError(self, ctx, f"unsupported union style: {style!r}")

        return result


class LiteralConverter(Converter):
    """A converter for #typing.Literal type hints. A literal value in the definition must simply match the literal
    value in the context being serialized/deserialized, otherwise a #ConversionError is raised. Currently, literal
    values must be of a plain data type that natively maps to a JSON type, like a boolean, integer, float, string
    or #None."""

    def convert(self, ctx: Context) -> t.Any:
        if not isinstance(ctx.datatype, LiteralTypeHint):
            raise NotImplementedError

        if ctx.value not in ctx.datatype.values:
            raise ConversionError(
                self,
                ctx,
                f"literal value mismatch: got {ctx.value!r}, expected {'|'.join(map(repr, ctx.datatype.values))}",
            )

        return ctx.value
