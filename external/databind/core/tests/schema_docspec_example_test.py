import dataclasses
import typing as t

from typeapi import TypeHint

from databind.core.schema import Field, Schema, convert_dataclass_to_schema


@dataclasses.dataclass
class ApiObject:
    location: str
    name: str


@dataclasses.dataclass
class HasMembers(ApiObject):
    members: t.Sequence[ApiObject]


@dataclasses.dataclass
class Module(HasMembers):
    members: t.List["Module"]


def test__convert_dataclass_to_schema__multiple_levels_of_inheritance() -> None:
    assert convert_dataclass_to_schema(ApiObject) == Schema(
        {
            "location": Field(TypeHint(str), True),
            "name": Field(TypeHint(str), True),
        },
        ApiObject,
        ApiObject,
    )
    assert convert_dataclass_to_schema(HasMembers) == Schema(
        {
            "location": Field(TypeHint(str), True),
            "name": Field(TypeHint(str), True),
            "members": Field(TypeHint(t.Sequence[ApiObject]), True),
        },
        HasMembers,
        HasMembers,
    )
    assert convert_dataclass_to_schema(Module) == Schema(
        {
            "location": Field(TypeHint(str), True),
            "name": Field(TypeHint(str), True),
            "members": Field(TypeHint(t.List[Module]), True),
        },
        Module,
        Module,
    )
