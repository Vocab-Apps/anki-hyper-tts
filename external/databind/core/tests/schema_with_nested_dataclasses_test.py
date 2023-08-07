from dataclasses import dataclass
from typing import List

from typeapi import TypeHint

from databind.core.schema import Field, Schema, convert_dataclass_to_schema


@dataclass
class Parent:
    @dataclass
    class Child:
        name: str

    @dataclass
    class Sibling:
        first: "Parent.Child"
        second: "Parent.Child"

    siblings: List[Sibling]


def test__convert_dataclass_to_schema__with_nested_dataclasses() -> None:
    schema = convert_dataclass_to_schema(Parent.Sibling)
    assert schema == Schema(
        fields={
            "first": Field(TypeHint(Parent.Child)),
            "second": Field(TypeHint(Parent.Child)),
        },
        constructor=Parent.Sibling,
        type=Parent.Sibling,
    )
