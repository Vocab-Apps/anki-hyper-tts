from typing import Any, ClassVar, Dict, Generic, List, NewType, Optional, Sequence, Tuple, TypeVar, Union

from pytest import mark
from typing_extensions import Annotated, Literal, TypeAlias

from typeapi.typehint import (
    AnnotatedTypeHint,
    ClassTypeHint,
    ClassVarTypeHint,
    ForwardRefTypeHint,
    LiteralTypeHint,
    TupleTypeHint,
    TypeAliasTypeHint,
    TypeHint,
    TypeVarTypeHint,
    UnionTypeHint,
)
from typeapi.utils import IS_PYTHON_AT_LEAST_3_10, ForwardRef

T = TypeVar("T")
U = TypeVar("U")


def test__TypeHint__any() -> None:
    hint = TypeHint(Any)
    assert isinstance(hint, ClassTypeHint)
    assert hint.hint == Any
    assert hint.origin is object
    assert hint.type is object
    assert hint.args == ()
    assert hint.parameters == ()
    assert len(hint) == 0


def test__TypeHint__int() -> None:
    hint = TypeHint(int)
    assert isinstance(hint, ClassTypeHint)
    assert hint.hint is int
    assert hint.origin is None
    assert hint.type is int
    assert hint.args == ()
    assert hint.parameters == ()
    assert len(hint) == 0


def test__TypeHint__list_generic() -> None:
    hint = TypeHint(List)
    assert isinstance(hint, ClassTypeHint)
    assert hint.hint == List
    assert hint.origin is list
    assert hint.args == ()
    assert str(hint.parameters) == "(~T,)"
    assert len(hint) == 0
    assert hint.type is list
    assert hint.bases == (object,)


def test__TypeHint__list_templatized() -> None:
    hint = TypeHint(List[T])  # type: ignore[valid-type]
    assert isinstance(hint, ClassTypeHint)
    assert hint.hint == List[T]  # type: ignore[valid-type]
    assert hint.origin is list
    assert hint.args == (T,)  # type: ignore[valid-type]
    assert str(hint.parameters) == "(~T,)"
    assert len(hint) == 1
    assert hint.type is list
    assert hint.bases == (object,)


def test__TypeHint__list_specialized() -> None:
    hint = TypeHint(List[int])
    assert isinstance(hint, ClassTypeHint)
    assert hint.hint == List[int]
    assert hint.origin is list
    assert hint.args == (int,)
    assert hint.parameters == ()
    assert len(hint) == 1
    assert hint.type is list
    assert hint.bases == (object,)

    hint_0 = hint[0]
    assert isinstance(hint_0, ClassTypeHint)
    assert hint_0.type is int
    assert hint_0.bases == (object,)


@mark.parametrize(
    argnames="is_at_least_3_10",
    argvalues=[False, True] if IS_PYTHON_AT_LEAST_3_10 else [False],
    ids=["typing.Union", "types.UnionType"] if IS_PYTHON_AT_LEAST_3_10 else ["typing.Union"],
)
def test__TypeHint__union(is_at_least_3_10: bool) -> None:
    if is_at_least_3_10:
        # Test native union type in Python 3.10+
        hint = TypeHint(eval("int | str"))
    else:
        hint = TypeHint(Union[int, str])

    assert isinstance(hint, UnionTypeHint)
    assert hint.hint == Union[int, str]
    assert hint.origin is Union
    assert hint.args == (int, str)
    assert hint.parameters == ()
    assert len(hint) == 2

    hint_0 = hint[0]
    assert isinstance(hint_0, ClassTypeHint)
    assert hint_0.type is int

    hint_1 = hint[1]
    assert isinstance(hint_1, ClassTypeHint)
    assert hint_1.type is str


def test__UnionTypeHint__none_type() -> None:
    hint = TypeHint(Union[int, None])
    assert isinstance(hint, UnionTypeHint)
    assert hint.has_none_type()
    new_hint = hint.without_none_type()
    assert isinstance(new_hint, ClassTypeHint)
    assert new_hint.type is int

    hint = TypeHint(Union[int, str, None])
    assert isinstance(hint, UnionTypeHint)
    assert hint.has_none_type()
    new_hint = hint.without_none_type()
    assert isinstance(new_hint, UnionTypeHint)
    assert new_hint.args == (int, str)


def test__TypeHint__literal() -> None:
    hint = TypeHint(Literal[42, "foo"])
    assert isinstance(hint, LiteralTypeHint)
    assert hint.hint == Literal[42, "foo"]
    assert hint.origin is Literal
    assert hint.args == ()
    assert hint.parameters == ()
    assert hint.values == (42, "foo")
    assert len(hint) == 0


def test__TypeHint__annotated() -> None:
    hint = TypeHint(Annotated[int, 42, "foo"])
    assert isinstance(hint, AnnotatedTypeHint)
    assert hint.hint == Annotated[int, 42, "foo"]
    assert hint.origin is Annotated
    assert hint.args == (int,)
    assert hint.parameters == ()
    assert hint.metadata == (42, "foo")
    assert len(hint) == 1

    hint_0 = hint[0]
    assert isinstance(hint_0, ClassTypeHint)
    assert hint_0.type is int


def test__TypeHint__custom_generic_class() -> None:
    class MyGeneric(Generic[T, U]):
        pass

    hint = TypeHint(MyGeneric)
    assert isinstance(hint, ClassTypeHint)
    assert hint.hint == MyGeneric
    assert hint.origin is None
    assert hint.args == ()
    assert hint.parameters == (T, U)
    assert len(hint) == 0
    assert hint.bases == (Generic[T, U],)

    hint = TypeHint(MyGeneric[int, str])
    assert isinstance(hint, ClassTypeHint)
    assert hint.hint == MyGeneric[int, str]
    assert hint.origin is MyGeneric
    assert hint.args == (int, str)
    assert hint.parameters == ()
    assert len(hint) == 2
    assert hint.bases == (Generic[T, U],)

    hint = TypeHint(MyGeneric[int, T])  # type: ignore[valid-type]
    assert isinstance(hint, ClassTypeHint)
    assert hint.hint == MyGeneric[int, T]  # type: ignore[valid-type]
    assert hint.origin is MyGeneric
    assert hint.args == (int, T)
    assert hint.parameters == (T,)
    assert len(hint) == 2
    assert hint.bases == (Generic[T, U],)

    hint_0 = hint[0]
    assert isinstance(hint_0, ClassTypeHint)
    assert hint_0.type is int

    hint_1 = hint[1]
    assert isinstance(hint_1, TypeVarTypeHint)
    assert str(hint_1.hint) == "~T"


def test__TypeHint__from_TypeVar() -> None:
    hint = TypeHint(T)
    assert isinstance(hint, TypeVarTypeHint)
    assert hint.hint == T
    assert hint.origin is None
    assert hint.args == ()
    assert hint.parameters == ()
    assert hint.name == "T"
    assert not hint.covariant
    assert not hint.contravariant
    assert hint.bound is None
    assert hint.constraints == ()


def test__TypeHint__from_string() -> None:
    hint = TypeHint("int")
    assert isinstance(hint, ForwardRefTypeHint)
    assert hint.hint == "int"
    assert hint.origin is None
    assert hint.args == ()
    assert hint.parameters == ()
    assert hint.ref == ForwardRef("int")


def test__TypeHint__from_ForwardRef_with_literal() -> None:
    hint = TypeHint(ForwardRef("Literal[42, 'universe']")).evaluate({"Literal": Literal})
    assert isinstance(hint, LiteralTypeHint)
    assert hint.hint == Literal[42, "universe"]
    assert hint.origin is Literal
    assert hint.args == ()
    assert hint.values == (42, "universe")
    assert hint.parameters == ()


def test__TypeHint__from_ForwardRef_instance() -> None:
    hint = TypeHint(ForwardRef("int"))
    assert isinstance(hint, ForwardRefTypeHint)
    assert hint.hint == ForwardRef("int")
    assert hint.origin is None
    assert hint.args == ()
    assert hint.parameters == ()
    assert hint.ref == ForwardRef("int")


def test__TypeHint__from_future_syntax_ForwardRef_builtin_subscript() -> None:
    hint = TypeHint(ForwardRef("list[int]")).evaluate({})
    assert isinstance(hint, ClassTypeHint)
    assert hint.hint == List[int]
    assert hint.origin is list
    assert hint.args == (int,)
    assert hint.parameters == ()


def test__TypeHint__from_future_syntax_ForwardRef_union() -> None:
    hint = TypeHint(ForwardRef("int | list[int]")).evaluate({})
    assert isinstance(hint, UnionTypeHint)
    assert hint.hint == Union[int, List[int]]
    assert hint.origin is Union
    assert hint.args == (int, List[int])
    assert hint.parameters == ()

    hint = TypeHint(ForwardRef("int | None")).evaluate({})
    assert isinstance(hint, UnionTypeHint)
    assert hint.hint == Optional[int]
    assert hint.origin is Union
    assert hint.args == (int, type(None))
    assert hint.parameters == ()


def test__TypeHint__from_newtype() -> None:
    MyInt = NewType("MyInt", int)
    hint = TypeHint(MyInt)
    assert isinstance(hint, ClassTypeHint)
    assert hint.args == ()
    assert hint.bases == (object,)
    assert hint.origin is None
    assert hint.type is int
    assert hint.hint is MyInt


def test__TypeHint__from_generic_with_unbound_typevar() -> None:
    """
    Inheriting from a generic base class without parameterizing it is not valid and databind cannot handle the
    case correctly. The `TypeHint.bases` will appear as the bases' bases (that is because `__orig_bases__` is not
    set on the new subclass and instead it reads the attribute from the parent).
    """

    T = TypeVar("T")
    U = TypeVar("U")

    class Base(Generic[T]):
        a: int

    class Incorrect(Base):  # type: ignore[type-arg]
        b: str

    class Correct(Base[U]):
        b: str

    hint = TypeHint(Base)
    assert isinstance(hint, ClassTypeHint)
    assert hint.type == Base
    assert hint.bases == (Generic[T],)
    assert hint.origin is None
    assert "__orig_bases__" in vars(Base)

    hint = TypeHint(Incorrect)
    assert isinstance(hint, ClassTypeHint)
    assert hint.type == Incorrect
    assert hint.bases == (Generic[T],)  # Note how this is not (Base,)
    assert hint.origin is None
    assert "__orig_bases__" not in vars(Incorrect)

    hint = TypeHint(Correct)
    assert isinstance(hint, ClassTypeHint)
    assert hint.type == Correct
    assert hint.bases == (Base[U],)  # type: ignore[valid-type]
    assert hint.origin is None
    assert "__orig_bases__" in vars(Correct)


def test__ClassTypeHint__parametrize() -> None:
    """This method tests the infusion of type parameters into other types.

    This is relevant when you want to carry over a type parameter into the
    fields of a type, such as in dataclasses."""

    from dataclasses import dataclass, fields

    @dataclass
    class MyClass(Generic[T, U]):
        member1: T
        member2: Dict[T, U]

    hint = TypeHint(MyClass[int, str])
    assert isinstance(hint, ClassTypeHint)
    assert hint.args == (int, str)
    assert hint.parameters == ()
    assert hint.origin is MyClass
    assert hint.type is MyClass
    assert hint.bases == (Generic[T, U],)

    # How do we find out what type MyClass[int, str].member1 and .member2 actually is?
    # -> We can inspect the original type to look for its type parameters and
    #    map those to the arguments of the original hint.

    parameters_to_args = hint.get_parameter_map()
    assert parameters_to_args == {T: int, U: str}

    field_types = {}
    for field in fields(MyClass):
        field_types[field.name] = TypeHint(field.type).parameterize(parameters_to_args)

    member1_hint = field_types["member1"]
    assert isinstance(member1_hint, ClassTypeHint)
    assert member1_hint.hint is int
    assert member1_hint.type is int

    member2_hint = field_types["member2"]
    assert isinstance(member2_hint, ClassTypeHint)
    assert member2_hint.hint == Dict[int, str]
    assert member2_hint.args == (int, str)
    assert member2_hint.type is dict

    # What happens if we call get_parameter_map() on a generic or partial generic?
    hint = TypeHint(MyClass)
    assert isinstance(hint, ClassTypeHint)
    assert hint.get_parameter_map() == {}

    hint = TypeHint(MyClass[U, int])  # type: ignore[valid-type]
    assert isinstance(hint, ClassTypeHint)
    assert hint.get_parameter_map() == {T: U, U: int}


def test__ClassTypeHint__generic_class_hierarchy() -> None:
    class A(Generic[T]):
        pass

    class B(A[T], Generic[T, U]):
        pass

    hint = TypeHint(B[int, str])
    assert isinstance(hint, ClassTypeHint)
    assert hint.hint == B[int, str]
    assert hint.origin is B
    assert hint.bases == (A[T], Generic[T, U])  # type: ignore[valid-type]


def test__TypeHint__evaluate() -> None:
    MyVector = List["MyType"]  # noqa: F821

    class MyType:
        pass

    hint = TypeHint(MyVector)
    assert isinstance(hint, ClassTypeHint)
    assert hint.type is list

    item_hint = hint[0]
    assert isinstance(item_hint, ForwardRefTypeHint)
    assert item_hint.expr == "MyType"

    hint = hint.evaluate(locals())
    item_hint = hint[0]
    assert isinstance(item_hint, ClassTypeHint)
    assert item_hint.type is MyType


def test__TypeHint__evaluate_recursive() -> None:
    hint = TypeHint("List['int']")
    assert isinstance(hint, ForwardRefTypeHint)

    hint = hint.evaluate(globals())
    assert hint.hint == List[int]
    assert isinstance(hint, ClassTypeHint), hint
    assert isinstance(hint[0], ClassTypeHint), hint[0]


def test__TypeHint__evaluate_with_custom_mapping() -> None:
    class Mapping:
        def __getitem__(self, _k: str) -> Any:
            return int

    hint = TypeHint(List["str"]).evaluate(Mapping())
    item_hint = hint[0]
    assert isinstance(item_hint, ClassTypeHint)
    assert item_hint.type is int


def test__TypeHint__evaluate_forward_reference_on_class_level() -> None:
    class A:
        class B:
            pass

    hint = TypeHint("B", A)
    assert hint.evaluate() == TypeHint(A.B)

    hint = TypeHint("str", A)
    assert hint.evaluate() == TypeHint(str)


def test__TypeHint__tuple_evaluate() -> None:
    assert TypeHint(tuple, source=tuple).evaluate() == TypeHint(tuple)


def test__TypeHint__caching_same_named_type_hints() -> None:
    """
    This test ensures that type hint caching is stable if two different
    definitions with the same are encountered.
    """

    class A:
        pass

    hint = TypeHint(A)
    assert isinstance(hint, ClassTypeHint)
    assert hint.type is A

    OldA = A

    class A:  # type: ignore[no-redef]
        pass

    hint = TypeHint(A)
    assert isinstance(hint, ClassTypeHint)
    assert hint.type is not OldA
    assert hint.type is A


def test__TypeHint__parameterized_types() -> None:
    """This function tests support for the :meth:`TypeHint._copy_with_args()`
    implementation to assert the compatibility with certain special generic
    aliases."""

    def clsth(x: Any) -> ClassTypeHint:
        hint = TypeHint(x)
        assert isinstance(hint, ClassTypeHint)
        return hint

    assert clsth(Sequence[T]).parameterize({T: int}).hint == Sequence[int]  # type: ignore[valid-type]
    assert clsth(List[T]).parameterize({T: int}).hint == List[int]  # type: ignore[valid-type]
    assert clsth(Dict[T, U]).parameterize({T: str, U: T}).hint == Dict[str, T]  # type: ignore[valid-type]

    class MyGeneric(Generic[U, T]):
        pass

    assert clsth(MyGeneric[T, U]).parameterize({T: int, U: str}).hint == MyGeneric[int, str]  # type: ignore[valid-type]

    def tupth(x: Any) -> TupleTypeHint:
        hint = TypeHint(x)
        assert isinstance(hint, TupleTypeHint)
        return hint

    assert tupth(Tuple[T, int]).parameterize({T: str}).hint == Tuple[str, int]
    assert tupth(Tuple[T, ...]).parameterize({T: str}).hint == Tuple[str, ...]


def test__TypeHint__native_tuple_type() -> None:
    hint = TypeHint(tuple)
    assert isinstance(hint, ClassTypeHint), hint
    assert len(hint) == 0
    assert hint.hint is tuple
    assert hint.origin is None
    assert hint.args == ()
    assert hint.parameters == ()
    assert hint.bases == (object,)

    hint = TypeHint(Tuple[Any, ...])
    assert isinstance(hint, TupleTypeHint), hint
    assert len(hint) == 1
    assert hint.hint == Tuple[Any, ...]
    assert hint.origin is tuple
    assert hint.args == (Any,)
    assert hint.parameters == ()
    assert hint.repeated
    assert hint.bases == (object,)


def test__TypeHint__empty_tuple() -> None:
    hint = TypeHint(Tuple[()])
    assert isinstance(hint, TupleTypeHint), hint
    assert len(hint) == 0
    assert hint.hint == Tuple[()]
    assert hint.origin is tuple
    assert hint.args == ()
    assert hint.parameters == ()
    assert not hint.repeated


def test__TypeHint__single_item() -> None:
    hint = TypeHint(Tuple[int])
    assert isinstance(hint, TupleTypeHint), hint
    assert len(hint) == 1
    assert hint.hint == Tuple[int]
    assert hint.origin is tuple
    assert hint.args == (int,)
    assert hint.parameters == ()
    assert not hint.repeated


def test__TypeHint__two_items() -> None:
    hint = TypeHint(Tuple[int, str])
    assert isinstance(hint, TupleTypeHint), hint
    assert len(hint) == 2
    assert hint.hint == Tuple[int, str]
    assert hint.origin is tuple
    assert hint.args == (int, str)
    assert hint.parameters == ()
    assert not hint.repeated


def test__TypeHint__repeated() -> None:
    hint = TypeHint(Tuple[int, ...])
    assert isinstance(hint, TupleTypeHint), hint
    assert len(hint) == 1
    assert hint.hint == Tuple[int, ...]
    assert hint.origin is tuple
    assert hint.args == (int,)
    assert hint.parameters == ()
    assert hint.repeated


def test__ClassTypeHint__recurse_bases_generic() -> None:
    class A:
        pass

    class B(A, int):
        pass

    class C(B, Generic[T]):
        pass

    class D(C[T]):
        pass

    hint = TypeHint(C)
    assert isinstance(hint, ClassTypeHint)
    assert hint.type is C
    assert hint.bases == (B, Generic[T])
    assert list(hint.recurse_bases("bfs")) == [
        TypeHint(C),
        TypeHint(B),
        TypeHint(Generic[T]),
        TypeHint(A),
        TypeHint(int),
        TypeHint(object),
        TypeHint(object),
        TypeHint(object),
    ]
    assert list(hint.recurse_bases("dfs")) == [
        TypeHint(C),
        TypeHint(B),
        TypeHint(A),
        TypeHint(object),
        TypeHint(int),
        TypeHint(object),
        TypeHint(Generic[T]),
        TypeHint(object),
    ]

    hint = TypeHint(D[int])
    assert isinstance(hint, ClassTypeHint)
    assert hint.type is D
    assert hint.bases == (C[T],)  # type: ignore[valid-type]
    assert list(hint.recurse_bases("bfs")) == [
        TypeHint(D[int]),
        TypeHint(C[int]),
        TypeHint(B),
        TypeHint(Generic[T]),
        TypeHint(A),
        TypeHint(int),
        TypeHint(object),
        TypeHint(object),
        TypeHint(object),
    ]


def test__ClassTypeHint__recurse_bases_for_list_subclass() -> None:
    class CustomList(List[T]):
        pass

    hint = TypeHint(CustomList)
    assert isinstance(hint, ClassTypeHint)
    assert hint.type is CustomList
    assert hint.bases == (List[T],)  # type: ignore[valid-type]
    assert list(hint.recurse_bases("bfs")) == [
        TypeHint(CustomList),
        TypeHint(List[T]),  # type: ignore[valid-type]
        TypeHint(object),
    ]

    hint = TypeHint(CustomList[int])
    assert isinstance(hint, ClassTypeHint)
    assert hint.type is CustomList
    assert hint.bases == (List[T],)  # type: ignore[valid-type]
    assert list(hint.recurse_bases("bfs")) == [
        TypeHint(CustomList[int]),
        TypeHint(List[int]),
        TypeHint(object),
    ]


def test__TypeHint__with_TypeAlias() -> None:
    hint = TypeHint(TypeAlias)
    assert isinstance(hint, TypeAliasTypeHint)
    assert hint.hint == TypeAlias
    assert hint.args == ()


def test__TypeHint__with_ClassVar() -> None:
    hint = TypeHint(ClassVar)
    assert isinstance(hint, ClassVarTypeHint)
    assert hint.hint == ClassVar
    assert hint.args == ()

    hint = TypeHint(ClassVar[Union[int, str]])
    assert isinstance(hint, ClassVarTypeHint)
    assert hint.hint == ClassVar[Union[int, str]]
    assert hint.args == (Union[int, str],)
    assert hint[0] == TypeHint(Union[int, str])


def test__ClassVarTypeHint__copy_with_args() -> None:
    hint = TypeHint(ClassVar[int])
    assert hint._copy_with_args((str,)).hint == ClassVar[str]
