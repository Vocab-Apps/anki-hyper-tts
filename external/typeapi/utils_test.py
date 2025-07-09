# type: ignore

import collections.abc
import sys
import typing as t
from typing import Any, Dict, Generic, List, Mapping, MutableMapping, Optional, TypeVar, Union

import pytest
import typing_extensions

from typeapi.utils import (
    IS_PYTHON_AT_LEAST_3_7,
    IS_PYTHON_AT_LEAST_3_9,
    ForwardRef,
    get_annotations,
    get_subscriptable_type_hint_from_origin,
    get_type_hint_args,
    get_type_hint_origin_or_none,
    get_type_hint_original_bases,
    get_type_hint_parameters,
)

T = TypeVar("T")
U = TypeVar("U")


def test__typing_List__introspection():
    # Origin:

    if sys.version_info[:2] <= (3, 6):
        from typing import MutableSequence
        from typing import T as _T

        assert List.__origin__ is None
        assert List[int].__origin__ is List
        assert List.__orig_bases__ == (list, MutableSequence[_T])
        assert List[int].__orig_bases__ == (list, MutableSequence[_T])
    else:
        assert List.__origin__ is list
        assert List[int].__origin__ is list
        assert not hasattr(List, "__orig_bases__")
        assert not hasattr(List[int], "__orig_bases__")

    assert get_type_hint_origin_or_none(List) is list
    assert get_type_hint_origin_or_none(List[int]) is list

    # NOTE(NiklasRosenstein): We currently have a different behaviour for special generics
    #   between Python 3.6 and other versions in that Python 3.6 actually returns original.
    if sys.version_info[:2] <= (3, 6):
        assert get_type_hint_original_bases(List) == (list, MutableSequence[_T])
    else:
        assert get_type_hint_original_bases(List) == ()
    assert get_type_hint_original_bases(List[int]) == ()

    # Generic-form parameters:

    if sys.version_info[:2] <= (3, 6):
        assert List.__args__ is None
        assert str(List.__parameters__) == "(~T,)"

    elif (3, 7) <= sys.version_info[:2] <= (3, 8):
        assert str(List.__args__) == "(~T,)"
        assert str(List.__parameters__) == "(~T,)"

    else:
        assert not hasattr(List, "__args__")
        assert not hasattr(List, "__parameters__")
        assert List._nparams == 1

    assert get_type_hint_args(List) == ()
    assert str(get_type_hint_parameters(List)) == "(~T,)"

    # Parametrized generic:

    assert List[T].__args__ == (T,)
    assert List[T].__parameters__ == (T,)
    assert get_type_hint_args(List[T]) == (T,)
    assert get_type_hint_parameters(List[T]) == (T,)

    # Fully specialized:

    assert List[int].__args__ == (int,)
    assert List[int].__parameters__ == ()
    assert get_type_hint_args(List[int]) == (int,)
    assert get_type_hint_parameters(List[int]) == ()


def test__typing_Collection__origin():
    assert get_type_hint_origin_or_none(t.Collection) is collections.abc.Collection
    assert get_type_hint_origin_or_none(t.Collection[int]) is collections.abc.Collection


@pytest.mark.parametrize(
    argnames=["hint", "origin_type", "mutable"],
    argvalues=[
        (Dict, dict, True),
        (MutableMapping, collections.abc.MutableMapping, True),
        (Mapping, collections.abc.Mapping, False),
    ],
)
def test__mapping_types__introspection(hint: object, origin_type: type, mutable: bool):
    # Origin:

    if sys.version_info[:2] <= (3, 6):
        assert hint.__origin__ is None
        assert hint[int, str].__origin__ is hint
    else:
        assert hint.__origin__ is origin_type
        assert hint[int, str].__origin__ is origin_type

    assert get_type_hint_origin_or_none(hint) is origin_type
    assert get_type_hint_origin_or_none(hint[int, str]) is origin_type

    # Generic-form parameters:

    value_type = "~VT" if mutable else "+VT_co"

    if sys.version_info[:2] <= (3, 6):
        assert hint.__args__ is None
        assert str(hint.__parameters__) == "(~KT, %s)" % value_type

    elif (3, 7) <= sys.version_info[:2] <= (3, 8):
        assert str(hint.__args__) == "(~KT, %s)" % value_type
        assert str(hint.__parameters__) == "(~KT, %s)" % value_type

    else:
        assert not hasattr(hint, "__args__")
        assert not hasattr(hint, "__parameters__")
        assert hint._nparams == 2

    assert get_type_hint_args(hint) == ()
    assert str(get_type_hint_parameters(hint)) == "(~KT, %s)" % value_type

    # Parametrized generic:

    assert hint[T, U].__args__ == (T, U)
    assert hint[T, U].__parameters__ == (T, U)
    assert get_type_hint_args(hint[T, U]) == (T, U)
    assert get_type_hint_parameters(hint[T, U]) == (T, U)

    # Fully specialized:

    assert hint[int, str].__args__ == (int, str)
    assert hint[int, str].__parameters__ == ()
    assert get_type_hint_args(hint[int, str]) == (int, str)
    assert get_type_hint_parameters(hint[int, str]) == ()

    assert hint[T, str].__args__ == (T, str)
    assert hint[T, str].__parameters__ == (T,)
    assert get_type_hint_args(hint[T, str]) == (T, str)
    assert get_type_hint_parameters(hint[T, str]) == (T,)

    assert hint[int, T].__args__ == (int, T)
    assert hint[int, T].__parameters__ == (T,)
    assert get_type_hint_args(hint[int, T]) == (int, T)
    assert get_type_hint_parameters(hint[int, T]) == (T,)


def test__typing_Generic__introspection():
    class MyGeneric(Generic[T, U]):
        pass

    # Origin:

    assert MyGeneric.__orig_bases__ == (Generic[T, U],)
    if sys.version_info[:2] <= (3, 6):
        assert MyGeneric.__origin__ is None
        assert MyGeneric[int, str].__origin__ is MyGeneric
        assert MyGeneric[int, str].__orig_bases__ == (Generic[T, U],)
    else:
        assert not hasattr(MyGeneric, "__origin__")
        assert MyGeneric[int, str].__origin__ is MyGeneric
        assert not hasattr(MyGeneric[int, str], "__orig_bases__")

    assert get_type_hint_origin_or_none(MyGeneric) is None
    assert get_type_hint_origin_or_none(MyGeneric[int, str]) is MyGeneric
    assert get_type_hint_original_bases(MyGeneric) == (Generic[T, U],)
    assert get_type_hint_original_bases(MyGeneric[int, str]) == ()

    # Generic-form parameters:

    if sys.version_info[:2] <= (3, 6):
        assert MyGeneric.__args__ is None
        assert str(MyGeneric.__parameters__) == "(~T, ~U)"

    elif (3, 7) <= sys.version_info[:2] <= (3, 8):
        assert not hasattr(MyGeneric, "__args__")
        assert str(MyGeneric.__parameters__) == "(~T, ~U)"

    else:
        assert not hasattr(MyGeneric, "__args__")
        assert hasattr(MyGeneric, "__parameters__")
        assert not hasattr(MyGeneric, "_nparams")

    assert get_type_hint_args(MyGeneric) == ()
    assert get_type_hint_parameters(MyGeneric) == (T, U)

    # Parametrized generic:

    assert MyGeneric[T, U].__args__ == (T, U)
    assert MyGeneric[T, U].__parameters__ == (T, U)
    assert get_type_hint_args(MyGeneric[T, U]) == (T, U)
    assert get_type_hint_parameters(MyGeneric[T, U]) == (T, U)

    # Fully specialized:

    assert MyGeneric[int, str].__args__ == (int, str)
    assert MyGeneric[int, str].__parameters__ == ()
    assert get_type_hint_args(MyGeneric[int, str]) == (int, str)
    assert get_type_hint_parameters(MyGeneric[int, str]) == ()

    assert MyGeneric[T, str].__args__ == (T, str)
    assert MyGeneric[T, str].__parameters__ == (T,)
    assert get_type_hint_args(MyGeneric[T, str]) == (T, str)
    assert get_type_hint_parameters(MyGeneric[T, str]) == (T,)

    assert MyGeneric[int, T].__args__ == (int, T)
    assert MyGeneric[int, T].__parameters__ == (T,)
    assert get_type_hint_args(MyGeneric[int, T]) == (int, T)
    assert get_type_hint_parameters(MyGeneric[int, T]) == (T,)


def test__typing_Generic__class_hierarchy():
    class MyGeneric(Generic[T]):
        pass

    class AnotherGeneric(Generic[T]):
        pass

    class SubGeneric(MyGeneric[T], AnotherGeneric[int], int):
        pass

    assert get_type_hint_origin_or_none(SubGeneric) is None
    assert get_type_hint_origin_or_none(SubGeneric[int]) is SubGeneric
    assert get_type_hint_original_bases(SubGeneric) == (MyGeneric[T], AnotherGeneric[int], int)
    assert get_type_hint_original_bases(SubGeneric[int]) == ()


@pytest.mark.parametrize(
    argnames=["Annotated"],
    argvalues=[(typing_extensions.Annotated,)] + ([(t.Annotated,)] if hasattr(t, "Annotated") else []),
)
def test__typing_Annotated__introspection(Annotated):
    # Origin:

    if sys.version_info[:2] <= (3, 6):
        assert Annotated.__origin__ is None
        assert Annotated[int, 42].__origin__ is Annotated  # Ouch..
    else:
        assert not hasattr(Annotated, "__origin__")
        assert Annotated[int, 42].__origin__ is int

    assert get_type_hint_origin_or_none(Annotated) is None
    assert get_type_hint_origin_or_none(Annotated[int, 42]) is Annotated

    # Args and parameters:

    if sys.version_info[:2] <= (3, 6):
        assert Annotated.__args__ is None
        assert Annotated.__parameters__ == ()

        with pytest.raises(TypeError) as exc:
            assert Annotated.__metadata__ == ()
        assert (
            str(exc.value)
            == "Annotated[...] should be instantiated with at least two arguments (a type and an annotation)."
        )  # noqa: E501
    else:
        assert not hasattr(Annotated, "__args__")
        assert not hasattr(Annotated, "__parameters__")
        assert not hasattr(Annotated, "__metadata__")

    assert get_type_hint_args(Annotated) == ()
    assert get_type_hint_parameters(Annotated) == ()

    if sys.version_info[:2] <= (3, 6):
        assert Annotated[int, 42].__args__ == (int, (42,))
        assert Annotated[int, 42].__parameters__ == ()
        assert Annotated[int, 42].__metadata__ == (42,)
    else:
        assert Annotated[int, 42].__args__ == (int,)
        assert Annotated[int, 42].__parameters__ == ()
        assert Annotated[int, 42].__metadata__ == (42,)

    assert get_type_hint_args(Annotated[int, 42]) == (int, 42)
    assert get_type_hint_parameters(Annotated[int, 42]) == ()


def test__typing_Union__introspection():
    # Origin:

    if sys.version_info[:2] <= (3, 6):
        assert Union.__origin__ is None
        assert Union[int, str].__origin__ is Union
    else:
        assert not hasattr(Union, "__origin__")
        assert Union[int, str].__origin__ is Union

    assert get_type_hint_origin_or_none(Union) is None
    assert get_type_hint_origin_or_none(Union[int, str]) is Union

    # Args and parameters:

    if sys.version_info[:2] <= (3, 6):
        assert Union.__args__ is None
        assert Union.__parameters__ is None
    else:
        assert not hasattr(Union, "__args__")
        assert not hasattr(Union, "__parameters__")
    assert get_type_hint_args(Union) == ()
    assert get_type_hint_parameters(Union) == ()

    assert Union[int, str].__args__ == (int, str)
    assert Union[int, str].__parameters__ == ()
    assert get_type_hint_args(Union[int, str]) == (int, str)
    assert get_type_hint_parameters(Union[int, str]) == ()

    assert Union[int, T].__args__ == (int, T)
    assert Union[int, T].__parameters__ == (T,)
    assert get_type_hint_args(Union[int, T]) == (int, T)
    assert get_type_hint_parameters(Union[int, T]) == (T,)


@pytest.mark.parametrize(
    argnames=["Literal"], argvalues=[(typing_extensions.Literal,)] + ([(t.Literal,)] if hasattr(t, "Literal") else [])
)
def test__typing_Literal__introspection(Literal):
    # Origin:

    if sys.version_info[:2] <= (3, 6):
        assert not hasattr(Literal, "__origin__")
        assert not hasattr(Literal[42, "foo"], "__origin__")
    else:
        assert not hasattr(Literal, "__origin__")
        assert Literal[42, "foo"].__origin__ is Literal

    assert get_type_hint_origin_or_none(Literal) is None
    assert get_type_hint_origin_or_none(Literal[42, "foo"]) is Literal

    # Args and parameters:

    assert not hasattr(Literal, "__args__")
    assert not hasattr(Literal, "__parameters__")
    if sys.version_info[:2] <= (3, 6):
        assert Literal.__values__ is None
    else:
        assert not hasattr(Literal, "__values__")
    assert get_type_hint_args(Literal) == ()
    assert get_type_hint_parameters(Literal) == ()

    if sys.version_info[:2] <= (3, 6):
        assert not hasattr(Literal[42, "foo"], "__args__")
        assert not hasattr(Literal[42, "foo"], "__parameters__")
        assert Literal[42, "foo"].__values__ == (42, "foo")
    else:
        assert Literal[42, "foo"].__args__ == (42, "foo")
        assert Literal[42, "foo"].__parameters__ == ()
        assert not hasattr(Literal[42, "foo"], "__values__")
    assert get_type_hint_args(Literal[42, "foo"]) == (42, "foo")
    assert get_type_hint_parameters(Literal[42, "foo"]) == ()


def test__typing_Any__introspection():
    # Origin:

    assert not hasattr(Any, "__origin__")
    assert get_type_hint_origin_or_none(Any) is object

    # Args and parameters:

    assert not hasattr(Any, "__args__")
    assert not hasattr(Any, "__parameters__")
    assert get_type_hint_args(Any) == ()
    assert get_type_hint_parameters(Any) == ()


def test__TypeVar__introspection():
    # Origin:

    assert not hasattr(T, "__origin__")
    assert get_type_hint_origin_or_none(T) is None

    # Args and parameters:

    assert not hasattr(T, "__args__")
    assert not hasattr(T, "__parameters__")
    assert get_type_hint_args(T) == ()
    assert get_type_hint_parameters(T) == ()


def test__int__introspection():
    assert get_type_hint_origin_or_none(int) is None
    assert get_type_hint_args(int) == ()
    assert get_type_hint_parameters(int) == ()


def test__ForwardRef__introspection_in_other_type():
    # NOTE(NiklasRosenstein): We use string equality because in Python <=3.7.6, ForwardRef does not
    #       implement equality correctly.
    assert str(List["int"].__args__) == str((ForwardRef("int"),))
    assert List["int"].__parameters__ == ()
    assert str(get_type_hint_args(List["int"])) == str((ForwardRef("int"),))
    assert get_type_hint_parameters(List["int"]) == ()


def test__ForwardRef__introspection():
    assert ForwardRef("int").__forward_arg__ == "int"
    get_type_hint_origin_or_none(ForwardRef("int")) is None
    get_type_hint_args(ForwardRef("int")) == ()
    get_type_hint_parameters(ForwardRef("int")) == ()

    get_type_hint_origin_or_none("int") is None
    get_type_hint_args("int") == ()
    get_type_hint_parameters("int") == ()


def test__get_subscriptable_type_hint_from_origin():
    assert get_subscriptable_type_hint_from_origin(List) is List
    assert get_subscriptable_type_hint_from_origin(list) is List
    assert get_subscriptable_type_hint_from_origin(Dict) is Dict
    assert get_subscriptable_type_hint_from_origin(dict) is Dict
    assert get_subscriptable_type_hint_from_origin(Mapping) is Mapping
    assert get_subscriptable_type_hint_from_origin(collections.abc.Mapping) is Mapping
    assert get_subscriptable_type_hint_from_origin(T) is T
    assert get_subscriptable_type_hint_from_origin(int) is int


def test__get_annotations__does_not_evaluate_strings() -> None:
    class A:
        a: "str | None"

    assert get_annotations(A, eval_str=False) == {"a": "str | None"}


def test__get_annotations__includes_bases() -> None:
    class A:
        a: "str | None"
        b: int

    class B(A):
        b: "str"
        c: Optional[int]

    assert get_annotations(B, include_bases=True, eval_str=False) == {"a": "str | None", "b": "str", "c": Optional[int]}


def test__get_annotations__can_evaluate_future_type_hints() -> None:
    class A:
        a: "str | None"

    annotations = get_annotations(A)
    assert annotations == {"a": Optional[str]}

    # NOTE(@NiklasRosenstein): Even though `str | None` is of type `types.UnionType` in Python 3.10+,
    #   our fake evaluation will still return legacy type hints.
    if IS_PYTHON_AT_LEAST_3_9:
        from typing import _UnionGenericAlias  # type: ignore

        assert type(annotations["a"]) is _UnionGenericAlias

    elif IS_PYTHON_AT_LEAST_3_7:
        from typing import _GenericAlias  # type: ignore

        assert type(annotations["a"]) is _GenericAlias

    else:
        assert str(type(annotations["a"])) == "typing.Union"


def test__get_annotations__evaluate_forward_references_on_class_level() -> None:
    class A:
        class B:
            pass

        a: "str"
        b: "B"

    annotations = get_annotations(A)
    assert annotations == {"a": str, "b": A.B}
