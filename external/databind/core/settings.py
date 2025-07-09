import abc
import dataclasses
import datetime
import decimal
import enum
import typing as t

from nr.date import date_format, datetime_format, format_set, time_format
from typeapi import AnnotatedTypeHint, ClassTypeHint, TypeHint

from databind.core.utils import T, check_instance_of, check_not_none, check_subclass_of

if t.TYPE_CHECKING:
    from databind.core.context import Context
    from databind.core.converter import Converter
    from databind.core.union import EntrypointUnionMembers, ImportUnionMembers, StaticUnionMembers, UnionMembers

T_Setting = t.TypeVar("T_Setting", bound="Setting")
T_ClassDecoratorSetting = t.TypeVar("T_ClassDecoratorSetting", bound="ClassDecoratorSetting")


class SettingsProvider(abc.ABC):
    """Interface for providing settings."""

    def get_setting(self, context: "Context", setting_type: "t.Type[T_Setting]") -> "T_Setting | None":
        ...


class Settings(SettingsProvider):
    """This class is used as a container for other objects that serve as a provider of settings that may taken into
    account during data conversion. Objects that provide settings are instances of #Setting subclasses, such as
    #FieldAlias or #DateFormat.

    Depending on the type of setting, they may be taken into account if present on a field of a dataclass, or globally
    from an instance of the #Settings class that is passed to the #ObjectMapper, or both. Which settings are recognized
    and considered depends also on the implementation of the converter(s) being used.

    The #Settings class provides capabilities to supply global settings, as well as supplying settings conditionally
    based on the type that is being looked at by the #ObjectMapper at the given point in time.

    Example:

    ```py
    from databind.core.settings import DateFormat, Priority, Settings, Strict
    settings = Settings()
    settings.add_global(DateFormat('.ISO_8601', priority=Priority.HIGH))
    settings.add_local(int, Strict(false))
    ```
    """

    def __init__(
        self, parent: t.Optional[SettingsProvider] = None, global_settings: t.Optional[t.List["Setting"]] = None
    ) -> None:
        self.parent = parent
        self.global_settings: t.List[Setting] = list(global_settings) if global_settings else []
        self.local_settings: t.Dict[type, t.List[Setting]] = {}
        self.providers: t.List[t.Callable[[Context], t.List[Setting]]] = []

    def add_global(self, setting: "Setting") -> None:
        """Add a global setting."""

        self.global_settings.append(setting)

    def add_local(self, type_: type, setting: "Setting") -> None:
        """Add a setting locally for a particular Python type. If that Python type is encountered, the settings are
        combined with any other settings that are found for the type."""

        self.local_settings.setdefault(type_, []).append(setting)

    def add_conditional(self, predicate: t.Callable[["Context"], bool], setting: "Setting") -> None:
        """Adds a setting conditional on the given *predicate*."""

        def _provider(context: Context) -> t.List[Setting]:
            if predicate(context):
                return [setting]
            return []

        self.providers.append(_provider)

    def add_provider(self, provider: t.Callable[["Context"], t.List["Setting"]]) -> None:
        """Add a provider callback that is invoked for every conversion context to provide additional settings that
        the subsequent converter should have access to."""

        self.providers.append(provider)

    def copy(self) -> "Settings":
        new = type(self)(self.parent, self.global_settings)
        new.local_settings = {k: list(v) for k, v in self.local_settings.items()}
        new.providers = list(self.providers)
        return new

    # SettingsProvider

    def get_setting(self, context: "Context", setting_type: t.Type[T_Setting]) -> "T_Setting | None":
        """Resolves the highest priority instance of the given setting type relevant to the current context. The places
        that the setting is looked for are, in order:

        1. If the context's datatype is #AnnotatedTypeHint, look for it in the #AnnotatedTypeHint.metadata. Otherwise,
           use the wrapped type in the following steps.
        2. If the datatype is a #ClassTypeHint, look for it as a class setting, then subsequently in the settings added
           with #add_local().
        3. Check the setting providers added with #add_provider() or #add_conditional().
        4. Look for it in the global settings.
        5. Delegate to the #parent settings provider (if any).

        If multiple settings are find using any of these steps, the setting with the highest priority among the
        settings is returned. If multiple settings have the same priority, the setting found first via the above order
        is returned.
        """

        from nr.stream import Stream

        def _all_settings() -> t.Iterator[t.Any]:
            datatype = context.datatype
            if isinstance(datatype, AnnotatedTypeHint):
                yield from (s for s in datatype.metadata if isinstance(s, setting_type))
                datatype = datatype[0]
            if isinstance(datatype, ClassTypeHint):
                yield from get_class_settings(datatype.type, setting_type)  # type: ignore[type-var]
                yield from self.local_settings.get(datatype.type, [])
            for provider in self.providers:
                yield from provider(context)
            yield from self.global_settings
            if self.parent:
                setting = self.parent.get_setting(context, setting_type)
                if setting is not None:
                    yield setting

        return get_highest_setting(Stream(_all_settings()).of_type(setting_type))


class Priority(enum.IntEnum):
    """The priority for settings determines their order in the presence of multiple conflicting settings. Settings
    should default to using the #NORMAL priority. The other priorities are used to either prevent overriding a field
    setting globally or to enforce overriding of local field settings globally using #Settings."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    ULTIMATE = 3


class Setting:
    """Base class for types of which instances represent a setting to be taken into account during data conversion.
    Every setting has a priority that is used to construct and order or to determine the single setting to use in
    the presence of multiple instances of the same setting type being present.

    Settings are usually attached to dataclass fields using #typing.Annotated, or added to a #Settings object for
    applying the setting globally, but some subclasses may support being used as decorators to attach the setting
    to a type object. Such settings would registers themselves under the `__databind_settings__` attribute (created
    if it does not exist) such that it can be picked up when introspected by a converter. Such #Setting subclasses
    should inherit from #DecoratorSetting instead."""

    priority: Priority = Priority.NORMAL

    def __init__(self) -> None:
        if type(self) is Setting:
            raise TypeError("Setting cannot be directly instantiated")


class ClassDecoratorSetting(Setting):
    bound_to: t.Optional[type] = None

    def __init__(self) -> None:
        if type(self) is ClassDecoratorSetting:
            raise TypeError("ClassDecoratorSetting cannot be directly instantiated")
        super().__init__()

    def __call__(self, type_: t.Type[T]) -> t.Type[T]:
        """Decorate the class *type_* with this setting, adding the setting to its `__databind_settings__` list
        (which is created if it does not exist) and sets #bound_to. The same setting instance cannot decorate multiple
        types."""

        assert isinstance(type_, type), type_
        if self.bound_to is not None:
            raise RuntimeError("cannot decorate multiple types with the same setting instance")

        self.bound_to = type_
        settings = getattr(type_, "__databind_settings__", None)
        if settings is None:
            settings = []
            setattr(type_, "__databind_settings__", settings)
        settings.append(self)

        return type_


def get_highest_setting(settings: t.Iterable[T_Setting]) -> "T_Setting | None":
    """Return the first, highest setting of *settings*."""

    try:
        return max(settings, key=lambda s: s.priority)
    except ValueError:
        return None


def get_class_settings(
    type_: type, setting_type: t.Type[T_ClassDecoratorSetting]
) -> t.Iterable[T_ClassDecoratorSetting]:
    """Returns all matching settings on *type_*."""

    for item in vars(type_).get("__databind_settings__", []):
        if isinstance(item, setting_type):
            yield item


def get_class_setting(type_: type, setting_type: t.Type[T_ClassDecoratorSetting]) -> "T_ClassDecoratorSetting | None":
    """Returns the first instance of the given *setting_type* on *type_*."""

    return get_highest_setting(get_class_settings(type_, setting_type))


def get_annotation_setting(type_: TypeHint, setting_type: t.Type[T_Setting]) -> "T_Setting | None":
    """Returns the first setting of the given *setting_type* from the given type hint from inspecting the metadata
    of the #AnnotatedTypeHint. Returns `None` if no such setting exists or if *type_* is not an #AnnotatedTypeHint
    instance."""

    if isinstance(type_, AnnotatedTypeHint):
        return get_highest_setting(s for s in type_.metadata if isinstance(s, setting_type))
    return None


@dataclasses.dataclass(frozen=True)
class BooleanSetting(Setting):
    """Base class for boolean settings."""

    enabled: bool = True
    priority: Priority = Priority.NORMAL

    def __post_init__(self) -> None:
        if type(self) is BooleanSetting:
            raise TypeError("BooleanSetting cannot be directly instantiated")


class Alias(Setting):
    """The #Alias setting is used to attach one or more alternative names to a dataclass field that should be used
    instead of the field's name in the code.

    Example:

    ```py
    import typing
    from dataclasses import dataclass
    from databind.core.settings import Alias

    @dataclass
    class MyClass:
      my_field: typing.Annotated[int, Alias('foobar', 'spam')]
    ```

    When deserializing a payload, converters should now use `foobar` if it exists, or fall back to `spam` when looking
    up the value for the field in the payload as opposed to `my_field`. When serializing, converters should use `foobar`
    as the name in the generated payload (always the first alias).
    """

    #: A tuple of the aliases provided to the constructor.
    aliases: t.Tuple[str, ...]
    priority: Priority = Priority.NORMAL

    def __init__(self, alias: str, *additional_aliases: str, priority: Priority = Priority.NORMAL) -> None:
        self.aliases = (alias,) + additional_aliases
        self.priority = priority

    def __repr__(self) -> str:
        return f'Alias({", ".join(map(repr, self.aliases))}, priority={self.priority!r})'


class Required(BooleanSetting):
    """Indicates whether a field is required during deserialization, even if it's type specifies that it is an
    optional field.

    Example:

    ```py
    import typing
    from dataclasses import dataclass
    from databind.core.settings import Required

    @dataclass
    class MyClass:
      my_field: typing.Annotated[typing.Optional[int], Required()]
    ```
    """


class Flattened(BooleanSetting):
    """Indicates whether a field should be "flattened" by virtually expanding it's sub fields into the parent
    datastructure's serialized form.

    Example:

    ```py
    import typing
    from dataclasses import dataclass
    from databind.core.settings import Flattened

    @dataclass
    class Inner:
      a: int
      b: str

    @dataclass
    class Outter:
      inner: typing.Annotated[Inner, Flattened()]
      c: str
    ```

    The `Outter` class in the example above may be deserialized, for example, from a JSON payload of the form
    `{"a": 0, "b": "", "c": ""}` as opposed to `{"inner": {"a": 0, "b": ""}, "c": ""}` due to the `Outter.inner`
    field's sub fields being expanded into `Outter`.
    """


class Strict(BooleanSetting):
    """Enable strict conversion of the field during conversion (this should be the default for converters unless
    some maybe available option to affect the strictness in a converter is changed). This setting should particularly
    affect only loss-less type conversions (such as `int` to `string` and the reverse being allowed when strict
    handling is disabled)."""


class SerializeDefaults(BooleanSetting):
    """Control whether default values are to be encoded in the serialized form of a structure. The default behaviour
    is up to the serializer implementation, though we consider it good practices to include values that match the
    default value of a field by default. However, using the setting defaults to #enabled having a value of `True` due
    to how the name of the setting appears assertive of the fact that the instance indicates the setting is enabled."""


@dataclasses.dataclass(frozen=True)
class DeserializeAs(Setting):
    """Indicates that a field should be deserialized as the given type instead of the type of the field. This is
    typically used when a field should be typed as an abstract class or interface, but during deserialization of the
    field, a concrete type should be used instead.

    Example:

    ```py
    import typing
    from dataclasses import dataclass
    from databind.core.settings import DeserializeAs

    @dataclass
    class A:
        pass

    @dataclass
    class B(A):
        pass

    @dataclass
    class MyClass:
      my_field: typing.Annotated[A, DeserializeAs(B)]
    ```

    Here, although `MyClass.my_field` is annotated as `A`, when a payload is deserialized into an instance of
    `MyClass`, the value for `my_field` will be deserialized as an instance of `B` instead of `A`.
    """

    type: t.Type[t.Any]
    priority: Priority = Priority.NORMAL


@dataclasses.dataclass(frozen=True)
class Precision(Setting):
    """A setting to describe the precision for #decimal.Decimal fields."""

    prec: t.Optional[int] = None
    rounding: t.Optional[str] = None
    Emin: t.Optional[int] = None
    Emax: t.Optional[int] = None
    capitals: t.Optional[bool] = None
    clamp: t.Optional[bool] = None
    priority: Priority = Priority.NORMAL

    def to_decimal_context(self) -> decimal.Context:
        return decimal.Context(
            prec=self.prec,
            rounding=self.rounding,
            Emin=self.Emin,
            Emax=self.Emax,
            capitals=self.capitals,
            clamp=self.clamp,
        )


@dataclasses.dataclass
class Union(ClassDecoratorSetting):
    """A setting that decorates a class or can be attached to the #typing.Annotated metadata of a #typing.Union
    type hint to specify that the type should be regarded as a union of more than one types. Which concrete type
    is to be used at the point of deserialization is usually clarified through a discriminator key. Unions may be
    of various styles that dictate how the discriminator key and the remaining fields are to be stored or read
    from.

    For serialiazation, the type of the Python value should inform the converter about which member of the union
    is being used. If the a union definition has multiple type IDs mapping to the same Python type, the behaviour
    is entirely up to the converter (an adequate resolution may be to pick the first matching type ID and ignore
    the remaining matches).

    !!! note

        The the examples for the different styles below, `"type"` is a stand-in for the value of the #discriminator_key
        and `...` serves as a stand-in for the remaining fields of the type that is represented by the discriminator.
    """

    #: The nested style in JSON equivalent is best described as `{"type": "<typeid>", "<typeid>": { ... }}`.
    NESTED: t.ClassVar = "nested"

    #: The flat style in JSON equivalent is best described as `{"type": "<typeid>", ... }`.
    FLAT: t.ClassVar = "flat"

    #: The keyed style in JSON equivalent is best described as `{"<typeid>": { ... }}`.
    KEYED: t.ClassVar = "keyed"

    #: The "best match" style attempts to deserialize the payload in an implementation-defined order and return
    #: the first or best succeeding result. No discriminator key is used.
    BEST_MATCH: t.ClassVar = "best_match"

    #: The subtypes of the union as an implementation of the #UnionMembers interface. When constructing the #Union
    #: setting, a dictionary may be passed in place of a #UnionMembers implementation, or a list of #UnionMembers
    #: to chain them together. Te constructor will also accept a string that is either `"<import>"`, which will
    #: be converted to an #ImportUnionMembers handler, or a string formatted as `"!<entrypoint>"`, which will be
    #: converted to an #EntrypointUnionMembers handler.
    members: "UnionMembers"

    #: The style of the union. This should be one of #NESTED, #FLAT, #KEYED or #BEST_MATCH. The default is #NESTED.
    style: str = NESTED

    #: The discriminator key to use, if valid for the #style. Defaults to `"type"`.
    discriminator_key: str = "type"

    #: The key to use when looking up the fields for the member type. Only used with the #NESTED style. If not set,
    #: the union member's type ID is used as the key.
    nesting_key: t.Optional[str] = None

    def __init__(
        self,
        members: t.Union[
            "UnionMembers",
            "StaticUnionMembers._MembersMappingType",
            "t.List[UnionMembers | str | StaticUnionMembers._MembersMappingType]",
            str,
            None,
        ] = None,
        style: str = NESTED,
        discriminator_key: str = "type",
        nesting_key: t.Optional[str] = None,
    ) -> None:
        def _convert_handler(handler: "UnionMembers | StaticUnionMembers._MembersMappingType | str") -> "UnionMembers":
            if isinstance(handler, t.Mapping) or handler is None:
                from databind.core.union import StaticUnionMembers

                return StaticUnionMembers(dict(handler) or {})
            elif isinstance(handler, str):
                if handler == "<import>":
                    return Union.import_()
                elif handler.startswith("!"):
                    return Union.entrypoint(handler[1:])
                raise ValueError(f"invalid union members string specified: {handler!r}")
            return handler

        if isinstance(members, list):
            from databind.core.union import ChainUnionMembers

            members = ChainUnionMembers(*(_convert_handler(x) for x in members))
        elif members is None:
            members = _convert_handler({})
        else:
            members = _convert_handler(members)

        self.members = members
        self.style = style
        self.discriminator_key = discriminator_key
        self.nesting_key = nesting_key

    def __hash__(self) -> int:
        return id(self)  # Needs to be hashable for Annotated[...] in Python 3.6

    @staticmethod
    def register(extends: type, name: t.Optional[str] = None) -> t.Callable[[t.Type[T]], t.Type[T]]:
        """A convenience method to use as a decorator for classes that should be registered as members of a #Union
        setting that is attached to the type *extends*. The #Union setting on *extends* must have a #StaticUnionMembers
        #members object. The decorated class must also be a subclass of *extends*.

        Example:

        ```py
        import abc
        import dataclasses
        from databind.core.settings import Union

        @Union()
        class MyInterface(abc.ABC):
          # ...
          pass

        @dataclasses.dataclass
        @Union.register(MyInterface, 'some')
        class SomeImplementation(MyInterface):
          # ...
          pass
        ```
        """

        from databind.core.union import StaticUnionMembers

        check_instance_of(extends, type)
        inst = check_not_none(
            get_class_setting(extends, Union), lambda: f"{extends.__name__} is not annotated with @union"
        )

        members = check_instance_of(inst.members, StaticUnionMembers)

        def _decorator(subtype: t.Type[T]) -> t.Type[T]:
            check_instance_of(subtype, type)
            check_subclass_of(subtype, extends)
            return members.register(name)(subtype)

        return _decorator

    @staticmethod
    def entrypoint(group: str) -> "EntrypointUnionMembers":
        from databind.core.union import EntrypointUnionMembers

        return EntrypointUnionMembers(group)

    @staticmethod
    def import_() -> "ImportUnionMembers":
        from databind.core.union import ImportUnionMembers

        return ImportUnionMembers()


@dataclasses.dataclass(init=False, unsafe_hash=True)
class DateFormat(Setting):
    """The #DateFormat setting is used to describe the date format to use for #datetime.datetime, #datetime.date
    and #datetime.time values when formatting them as a string, i.e. usually when the date/time is serialized, and
    when parsing them.

    The #nr.date module provides types to describe the format of a date, time and datetime (see #date_format,
    #time_format and #datetime_format), as well as an entire suite of formats for all types of date/time values.

    Arguments:
      formats: One or more datetime formats to use when parsing. The first of the formats is used for formatting.
        Each element must be one of the following:

        * A formatter (like #date_format, #time_format or #datetime_format),
        * a #format_set,
        * a string that is a date/time format, or
        * a string starting with a period (`.`) that names a builtin format set (like `.ISO_8601`)

        Attempting to use #parse() or #format() for a date/time value type for which the #DateFormat does not
        provide an applicable format results in a #ValueError.
    """

    Dtype = t.Union[datetime.date, datetime.time, datetime.datetime]
    Formatter = t.Union["date_format", "time_format", "datetime_format", "format_set"]
    T_Input = t.Union[str, Formatter]
    T_Dtype = t.TypeVar("T_Dtype", bound=Dtype)

    formats: t.Sequence[T_Input]

    def __init__(self, *formats: T_Input) -> None:
        if not formats:
            raise ValueError("need at least one date format")
        self.formats = formats

    @staticmethod
    def __get_builtin_format(fmt: str) -> Formatter:
        if fmt == ".ISO_8601":
            from nr.date.format_sets import ISO_8601

            return ISO_8601
        if fmt == ".JAVA_OFFSET_DATETIME":
            from nr.date.format_sets import JAVA_OFFSET_DATETIME

            return JAVA_OFFSET_DATETIME
        raise ValueError(f"{fmt!r} is not a built-in date/time format set")

    def __iter_formats(self, type_: t.Type[Formatter]) -> t.Iterable[Formatter]:
        for fmt in self.formats:
            if isinstance(fmt, str):
                if fmt.startswith("."):
                    yield self.__get_builtin_format(fmt)
                else:
                    yield type_.compile(fmt)  # type: ignore
            elif type(fmt) is type_:
                yield fmt
            elif isinstance(fmt, format_set):
                yield from getattr(fmt, type_.__name__ + "s")
            # else:
            #  raise RuntimeError(f'bad date format type: {type(fmt).__name__}')

    def parse(self, type_: t.Type[T_Dtype], value: str) -> T_Dtype:
        """Parse a date/time value from a string.

        Arguments:
          type_: The type to parse the value into, i.e. #datetime.date, #datetime.time or #datetime.datetime.
          value: The string to parse.
        Raises:
          ValueError: If no date format is sufficient to parse *value* into the given *type_*.
        Returns:
          The parsed date/time value.
        """

        from nr.date import date_format, datetime_format, time_format

        format_t: t.Type[DateFormat.Formatter]
        format_t, method_name = {  # type: ignore
            datetime.date: (date_format, "parse_date"),
            datetime.time: (time_format, "parse_time"),
            datetime.datetime: (datetime_format, "parse_datetime"),
        }[type_]
        for fmt in self.__iter_formats(format_t):
            try:
                return t.cast(DateFormat.T_Dtype, getattr(fmt, method_name)(value))
            except ValueError:
                pass
        raise self._formulate_parse_error(list(self.__iter_formats(format_t)), value)

    def format(self, dt: T_Dtype) -> str:
        """Format a date/time value to a string.

        Arguments:
          dt: The date/time value to format (i.e. an instance of #datetime.date, #datetime.time or
            #datetime.datetime).
        Raises:
          ValueError: If no date format to format the type of *value* is available.
        Returns:
          The formatted date/time value.
        """

        from nr.date import date_format, datetime_format, time_format

        format_t: t.Type[DateFormat.Formatter]
        format_t, method_name = {  # type: ignore
            datetime.date: (date_format, "format_date"),
            datetime.time: (time_format, "format_time"),
            datetime.datetime: (datetime_format, "format_datetime"),
        }[type(dt)]
        for fmt in self.__iter_formats(format_t):
            try:
                return t.cast(str, getattr(fmt, method_name)(dt))
            except ValueError:
                pass
        raise self._formulate_parse_error(list(self.__iter_formats(format_t)), dt)

    @staticmethod
    def _formulate_parse_error(formats: t.Sequence[Formatter], s: t.Any) -> ValueError:
        return ValueError(
            f'"{s}" does not match date formats ({len(formats)}):'
            + "".join(f"\n  | {str(x) if isinstance(x, format_set) else x.format_str}" for x in formats)
        )


class ExtraKeys(ClassDecoratorSetting):
    """If discovered while deserializing a #databind.core.schema.Schema, it's callback is used to inform when extras
    keys are encountered. If the setting is not available, or if the arg is set to `False` (the default), it will
    cause an error.

    The setting may also be supplied at an individual schema level.

    Can be used as a decorator for a class to indicate that extra keys on the schema informed by the class are allowed,
    as a global setting or as an annotation on a schema field.

    !!! note

        Only the first, highest priority annotation is used; thus if you pass a callback for *arg* it may not be called
        if the #ExtraKeys setting you pass it to is overruled by another.
    """

    def __init__(
        self,
        allow: bool = True,
        recorder: "t.Callable[[Context, t.Set[str]], t.Any] | None" = None,
        priority: Priority = Priority.NORMAL,
    ) -> None:
        self.allow = allow
        self.recorder = recorder
        self.priority = priority

    def inform(self, origin: "Converter", ctx: "Context", extra_keys: "t.Set[str]") -> None:
        from databind.core.converter import ConversionError

        if self.allow is False:
            raise ConversionError(origin, ctx, f"encountered extra keys: {extra_keys}")
        elif self.recorder is not None:
            self.recorder(ctx, extra_keys)


class Remainder(BooleanSetting):
    """This setting can be used to indicate on a field of a schema that is of a mapping type that it consumes any
    extra keys that are not otherwise understood by the schema. Note that there can only be a maximum of 1 remainder
    field in the same schema."""
