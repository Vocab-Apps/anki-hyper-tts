import dataclasses
import sys
import typing as t

from typeapi import (
    AnnotatedTypeHint,
    ClassTypeHint,
    TypedDictProtocol,
    TypeHint,
    UnionTypeHint,
    get_annotations,
    is_typed_dict,
    type_repr,
)

from databind.core.utils import NotSet

if sys.version_info[:2] <= (3, 8):
    GenericAlias = t.Any
else:
    from types import GenericAlias

if t.TYPE_CHECKING:
    Constructor = t.Callable[..., t.Any]


__all__ = [
    "Field",
    "Schema",
    "convert_to_schema",
    "convert_dataclass_to_schema",
    "convert_typed_dict_to_schema",
    "get_fields_expanded",
]


@dataclasses.dataclass
class Field:
    """Describes a field in a schema."""

    #: The datatype of the field.
    datatype: TypeHint

    #: Whether the field is required to be present, if this is `False` and the field does not have a #default or
    #: #default_factorty, the field value will not be passed to the schema constructor. Even if a #default or
    #: #default_factory is present, if he field is required it must be present in the payload being deserialized.
    required: bool = True

    #: The default value for the field, if any.
    default: t.Union[NotSet, t.Any] = NotSet.Value

    #: The default value factory for the field, if any.
    default_factory: t.Union[NotSet, t.Any] = NotSet.Value

    #: Indicates whether the field is to be treated "flat". If the #datatype is a structured type that has fields of its
    #: own, those fields should be treated as if expanded into the same level as this field.
    flattened: bool = False

    def has_default(self) -> bool:
        return self.default is not NotSet.Value or self.default_factory is not NotSet.Value

    def get_default(self) -> t.Any:
        if self.default is not NotSet.Value:
            return self.default
        elif self.default_factory is not NotSet.Value:
            return self.default_factory()
        else:
            raise RuntimeError("Field does not have a default value")

    @property
    def aliases(self) -> t.Tuple[str, ...]:
        """For convience, the aliases described in the #datatype#'s annotations are listed here. Do note however, that
        during the conversion process, the #Alias setting should still be looked up through #Context.get_setting()
        and this field should be ignored. It serves only a introspective purpose. Returns an empty tuple if no alias
        setting is present in the type hint."""

        from databind.core.settings import Alias, get_annotation_setting

        alias = get_annotation_setting(self.datatype, Alias)
        return alias.aliases if alias else ()


@dataclasses.dataclass
class Schema:
    """A #Schema describes a set of fields with a name and datatype."""

    #: A dictionary that maps the field descriptions in the schema. The key is the name of the field in code. Given an
    #: instance of an object that complies to a given #Schema, this is the name by which the value of the field should
    #: be read using attribute lookup.
    fields: t.Dict[str, Field]

    #: A function that constructs an instance of a Python object that this schema represents given a dictionary as
    #: keyword arguments of the deserialized field values. Fields that are not present in the source payload and a that
    #: do not have a default value will not be present in the passed dictionary.
    constructor: "Constructor"

    #: The underlying native Python type associated with the schema.
    type: type

    #: Annotation metadata that goes with the schema, possibly derived from a #AnnotatedTypeHint hint or the underlying
    #: Python type object.
    annotations: t.List[t.Any] = dataclasses.field(default_factory=list)


def convert_to_schema(hint: TypeHint) -> Schema:
    """Convert the given type hint to a #Schema.

    The function delegates to #convert_dataclass_to_schema() or #convert_typed_dict_to_schema().

    Arguments:
      hint: The type hint to convert. If it is a #AnnotatedTypeHint hint, it will be unwrapped.
    Raises:
      ValueError: If the type hint is not supported.
    """

    assert isinstance(hint, TypeHint), hint
    original_hint = hint

    annotations = []
    if isinstance(hint, AnnotatedTypeHint):
        annotations = list(hint.metadata)
        hint = hint[0]

    if isinstance(hint, ClassTypeHint) and dataclasses.is_dataclass(hint.type):
        schema = convert_dataclass_to_schema(hint)
    elif isinstance(hint, ClassTypeHint) and is_typed_dict(hint.type):
        # TODO(@NiklasRosenstein): Pass in the original TypeHint which will contain information about
        #   TypeVar parametrization that is lost when we just pass the generic type.
        schema = convert_typed_dict_to_schema(hint.type)
    else:
        raise ValueError(f"cannot be converted to a schema (not a dataclass or TypedDict): {type_repr(original_hint)}")

    schema.annotations.extend(annotations)
    return schema


def convert_dataclass_to_schema(dataclass_type: t.Union[type, GenericAlias, ClassTypeHint]) -> Schema:
    """Converts a Python class that is decorated with #dataclasses.dataclass() to a Schema.

    The function will respect the #Required setting if it is present in a field's datatype if,
    and only if, the setting occurs in the root type hint, which must be a #typing.Annotated hint.

    Arguments:
      dataclass_type: A Python type that is a dataclass, or a generic alias of a dataclass.
    Returns:
      A schema that represents the dataclass. If a generic alias was passed, fields of which the type hint contained
      type parameters will have their type parameters substituted with the respective arguments present in the alias.

    Example:

    ```py
    import dataclasses
    from typing import Generic, TypeVar
    from typeapi import TypeHint
    from databind.core.schema import convert_dataclass_to_schema, Field, Schema
    T = TypeVar('T')
    @dataclasses.dataclass
    class A(Generic[T]):
      a: T
    assert convert_dataclass_to_schema(A[int]) == Schema({'a': Field(TypeHint(int))}, A)
    ```
    """

    from dataclasses import MISSING

    hint: ClassTypeHint
    if isinstance(dataclass_type, ClassTypeHint):
        hint = dataclass_type
    else:
        hint = TypeHint(dataclass_type)  # type: ignore[assignment]
        assert isinstance(hint, ClassTypeHint), hint

    dataclass_type = hint.type
    assert isinstance(dataclass_type, type), repr(dataclass_type)
    assert dataclasses.is_dataclass(
        dataclass_type
    ), f"expected a @dataclass type, but {type_repr(dataclass_type)} is not such a type"

    # Figure out which field is defined on which dataclass in the class hierarchy.
    # This is important because we need to use the correct context when evaluating
    # forward references in field annotations; we can't just use the target
    # dataclass if it was defined in a different module.
    field_origin: t.Dict[str, type] = {}
    base_queue = [hint.type]
    while base_queue:
        base_type = base_queue.pop(0)
        if dataclasses.is_dataclass(base_type):
            annotations = get_annotations(base_type)
            for field in dataclasses.fields(base_type):
                if field.name in annotations and field.name not in field_origin:
                    field_origin[field.name] = base_type
        base_queue += base_type.__bases__

    # Retrieve the context in which type hints from each field origin type need to be
    # evaluated.
    eval_context_by_type: t.Dict[type, t.Mapping[str, t.Any]] = {
        type_: vars(sys.modules[type_.__module__]) for type_ in set(field_origin.values())
    }

    # Collect the members from the dataclass and its base classes.
    queue = [hint]
    fields: t.Dict[str, Field] = {}
    while queue:
        hint = queue.pop(0)
        parameter_map = hint.get_parameter_map()

        if hint.type in eval_context_by_type:
            # Make sure forward references are resolved.
            hint = hint.evaluate(eval_context_by_type[hint.type])  # type: ignore[assignment]
            assert isinstance(hint, ClassTypeHint)

            for field in dataclasses.fields(hint.type):
                if not field.init:
                    # If we cannot initialize the field in the constructor, we should also
                    # exclude it from the definition of the type for de-/serializing.
                    continue
                if field.name in fields:
                    # Subclasses override their parent's fields.
                    continue
                if field_origin[field.name] != hint.type:
                    # If this field does not belong to the current type
                    continue

                field_hint = TypeHint(field.type, field_origin[field.name]).evaluate().parameterize(parameter_map)

                # NOTE(NiklasRosenstein): In Python 3.6, Mypy complains about "Callable does not accept self argument",
                #       but we also cannot ignore it because of warn_unused_ignores.
                _field_default_factory = getattr(field, "default_factory")

                default = NotSet.Value if field.default == MISSING else field.default
                default_factory = NotSet.Value if _field_default_factory == MISSING else _field_default_factory
                has_default = default != NotSet.Value or default_factory != NotSet.Value
                required = _is_required(field_hint, not has_default)

                fields[field.name] = Field(
                    datatype=field_hint,
                    required=required,
                    default=None if not required and not has_default else default,
                    default_factory=default_factory,
                    flattened=_is_flat(field_hint, False),
                )
        else:
            # This could mean that a base class is a dataclass but all of its members
            # are overwritten by other fields.
            pass

        # Continue with the base classes.
        for base in hint.bases or hint.type.__bases__:
            base_hint = TypeHint(base, source=hint.type).evaluate().parameterize(parameter_map)
            assert isinstance(base_hint, ClassTypeHint), f"nani? {base_hint}"
            if dataclasses.is_dataclass(base_hint.type):
                queue.append(base_hint)

    return Schema(fields, t.cast("Constructor", dataclass_type), dataclass_type)


def convert_typed_dict_to_schema(typed_dict: t.Union[TypedDictProtocol, t.Type[t.Any], TypeHint]) -> Schema:
    """Converts the definition of a #typing.TypedDict to a #Schema.

    !!! note

        This function will take into account default values assigned on the class-level of the typed dict (which is
        usually only relevant if the class-style declaration method was used, but default values can be assigned to
        the function-style declared type as well). Fields that have default values are considered not-required even
        if the declaration specifies them as required.

        Be aware that right-hand side values on #typing.TypedDict classes are not allowed by Mypy.

        Also note that #typing.TypedDict cannot be mixed with #typing.Generic, so keys with a generic type in the
        typed dict are not possible (state: 2022-03-17, Python 3.10.2).

    !!! todo

        Support understanding #typing.Required and #typing.NotRequired.

    Example:

    ```py
    from databind.core.schema import convert_typed_dict_to_schema, Schema, Field
    from typing import TypedDict
    from typeapi import TypeHint
    class Movie(typing.TypedDict):
      name: str
      year: int = 0
    assert convert_typed_dict_to_schema(Movie) == Schema({
      'name': Field(TypeHint(str)),
      'year': Field(TypeHint(int), False, 0),
    }, Movie)
    ```
    """

    if isinstance(typed_dict, TypeHint):
        if not isinstance(typed_dict, ClassTypeHint):
            raise TypeError(f"expected ClassTypeHint, got {typed_dict}")
        typed_dict = typed_dict.type

    assert is_typed_dict(typed_dict), typed_dict

    eval_context = vars(sys.modules[typed_dict.__module__])

    annotations = get_annotations(t.cast(type, typed_dict))
    fields: t.Dict[str, Field] = {}
    for key in typed_dict.__required_keys__ | typed_dict.__optional_keys__:
        field_hint = TypeHint(annotations[key]).evaluate(eval_context)

        has_default = hasattr(typed_dict, key)
        required = _is_required(field_hint, not has_default)
        fields[key] = Field(
            datatype=field_hint,
            required=required and typed_dict.__total__,
            default=getattr(typed_dict, key) if has_default else None if not required else NotSet.Value,
            flattened=_is_flat(field_hint, False),
        )

    return Schema(fields, t.cast("Constructor", typed_dict), t.cast(type, typed_dict))


def _is_required(datatype: TypeHint, default: bool) -> bool:
    """If *datatype* is a #AnnotatedTypeHint instance, it will look for a #Required settings instance and returns
    that instances #Required.enabled value. Otherwise, it returns *default*."""
    from databind.core.settings import Required, get_annotation_setting

    required = get_annotation_setting(datatype, Required)
    if required:
        return required.enabled

    if isinstance(datatype, AnnotatedTypeHint):
        datatype = datatype[0]

    if isinstance(datatype, UnionTypeHint) and datatype.has_none_type():
        return False

    return default


def _is_flat(datatype: TypeHint, default: bool) -> bool:
    from databind.core.settings import Flattened, get_annotation_setting

    return (get_annotation_setting(datatype, Flattened) or Flattened(default)).enabled


def get_fields_expanded(
    schema: Schema,
    convert_to_schema: t.Callable[[TypeHint], Schema] = convert_to_schema,
) -> t.Dict[str, t.Dict[str, Field]]:
    """Returns a dictionary that contains an entry for each flattened field in the schema, mapping to another
    dictionary that contains _all_ fields expanded from the flattened field's sub-schema.

    Given a schema like the following example, this function returns something akin to the below.

    === "Schema"

        ```
        Schema1:
          a: int
          b: Schema2, flattened=True

        Schema2:
          c: str
          d: Schema3, flattened=True

        Schema3:
          e: int
        ```

    === "Result"

        ```py
        {
          "b": {
            "c": Field(str),
            "e": Field(int)
          }
        }

    Arguments:
      schema: The schema to compile the expanded fields for.
      convert_to_schema: A function that accepts a #TypeHint and converts it to a schema.
        Defaults to the #convert_to_schema() function.

    !!! note

        The top-level dictionary returned by this function contains _only_ those fields that are
        flattened and should be "composed" of other fields.
    ```
    """

    result = {}
    for field_name, field in schema.fields.items():
        if field.flattened:
            field_schema = convert_to_schema(field.datatype)
            result[field_name] = {
                **{k: v for k, v in field_schema.fields.items() if not v.flattened},
                **{k: v for sf in get_fields_expanded(field_schema).values() for k, v in sf.items()},
            }
            for sub_field_name in result[field_name]:
                if sub_field_name in schema.fields and sub_field_name != field_name:
                    raise RuntimeError(f"field {sub_field_name!r} occurs multiple times")
    return result
