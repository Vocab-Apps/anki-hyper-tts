"""
Provides a wrapper for #dataclasses.dataclass and #dataclasses.field that supports non-default arguments
following default arguments. The arguments can be specified as positional arguments if the intermediate
default arguments are populated as well, or as keyword arguments. The module is supposed to be a drop-in
replacement of wherever #dataclasses is used.

Requires the #databind.mypy module to support type checking.

Note: `make_dataclass` is not currently overridden, so it will not support non-default arguments
following default arguments.
"""

import dataclasses
import typing as t
from dataclasses import (
    MISSING,
    Field,
    FrozenInstanceError,
    InitVar,
    asdict,
    astuple,
    fields,
    is_dataclass,
    make_dataclass,
    replace,
)

from databind.core.utils import NotSet

__all__ = [
    "ANNOTATIONS_METADATA_KEY",
    # dataclasses API
    "dataclass",
    "field",
    "fields",
    "Field",
    "FrozenInstanceError",
    "InitVar",
    "MISSING",
    # Helper functions
    "fields",
    "asdict",
    "astuple",
    "make_dataclass",
    "replace",
    "is_dataclass",
]

ANNOTATIONS_METADATA_KEY = "databind.core.annotations"


def _field_has_default(field: Field) -> bool:
    return any(x != MISSING for x in (field.default, field.default_factory))  # type: ignore


def _process_class(cls, **kwargs):
    # Collect a list of the fields that have no default values but follow after a default argument.
    no_default_fields: t.List[str] = []
    existing_fields = getattr(cls, "__dataclass_fields__", {})  # For subclasses of dataclasses
    annotations = getattr(cls, "__annotations__", {})
    if "__annotations__" not in cls.__dict__:
        # Make sure that __annotations__ exists on the class itself.
        cls.__annotations__ = annotations

    # Make sure each annotated field actually has a #Field. For fields without
    # defaults, we will set #Field.default to #NotSet.Value so we can later
    # check if the field was set in __post_init__().
    for key in annotations.keys():
        if not hasattr(cls, key):
            f = existing_fields.get(key, field())
            setattr(cls, key, f)
        else:
            f = getattr(cls, key)
            if not isinstance(f, Field):
                continue
        if not _field_has_default(f):
            # This prevents a SyntaxError if non-default arguments follow default arguments.
            f.default = NotSet.Value
            no_default_fields.append(key)

    # Override the `__post_init__` method that is called by the dataclass `__init__`.
    orig_postinit = getattr(cls, "__post_init__", None)

    def __post_init__(self):
        # Ensure that no field has a "uninitialized" value.
        for key in self.__dataclass_fields__.keys():
            if getattr(self, key) == NotSet.Value:
                raise TypeError(f"missing required argument {key!r}")
        if orig_postinit:
            orig_postinit(self)

    cls.__post_init__ = __post_init__

    # Do the stdlib dataclass magic.
    cls = dataclasses.dataclass(cls, **kwargs)

    # After setting #Field.default for non-default fields, the default will be propagated
    # on the class level, so we delete that again from the class.
    for key in no_default_fields:
        if key in no_default_fields:
            delattr(cls, key)

    return cls


def dataclass(cls=None, **kwargs):
    """
    A wrapper for the #dataclasses.dataclass() decorator that allows non-default arguments to
    follow default arguments.
    """

    def wrap(cls):
        return _process_class(cls, **kwargs)

    if cls is not None:
        return wrap(cls)

    return wrap


def field(*, annotations=None, metadata=None, **kwargs):
    """
    A wrapper for #dataclasses.field() that accepts an additional "annotations" argument that will
    propagated into the field's "databind.core.annotations" metadata field.
    """

    if annotations:
        if metadata is None:
            metadata = {}
        metadata[ANNOTATIONS_METADATA_KEY] = annotations
    return dataclasses.field(**kwargs, metadata=metadata)
