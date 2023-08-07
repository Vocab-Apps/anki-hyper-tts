import enum
from typing import Any, Callable, Tuple, Type, TypeVar, Union, overload

T = TypeVar("T")
U = TypeVar("U")


class NotSet(enum.Enum):
    "A type to include in a union where `None` is a valid value and needs to be differentiated from 'not present'."

    Value = 0


def exception_safe_str(func: Callable[[T], str]) -> Callable[[T], str]:
    """Decorator for a #__str__() method of an #Exception subclass that catches an exception that occurs in the
    string formatting function, logs it and returns the message of the occurred exception instead."""

    import functools
    import logging

    @functools.wraps(func)
    def wrapper(self: T) -> str:
        try:
            return func(self)
        except Exception as exc:
            type_name = type(self).__module__ + "." + type(self).__name__
            logger = logging.getLogger(type_name)
            logger.exception("Unhandled exception in %s.__str__()", type_name)
            return str(exc)

    return wrapper


_T = TypeVar("_T")
_Message = Union[str, Callable[[], str]]
_Types = Union[type, Tuple[type, ...]]


def _get_message(message: _Message) -> str:
    if isinstance(message, str):
        return message
    else:
        return message()


def _repr_types(types: _Types) -> str:
    if isinstance(types, type):
        return types.__name__
    else:
        return "|".join(t.__name__ for t in types)


def check_not_none(value: "_T | None", message: "_Message | None" = None) -> _T:
    """
    Raises a #ValueError if *value* is `None`.
    """

    if value is None:
        raise ValueError(_get_message(message or "cannot be None"))
    return value


@overload
def check_instance_of(value: Any, types: Type[_T], message: "_Message | None" = None) -> _T:
    ...


@overload
def check_instance_of(value: Any, types: Tuple[type, ...], message: "_Message | None" = None) -> Any:
    ...


def check_instance_of(
    value: Any, types: "Type[_T] | Tuple[type, ...]", message: "_Message | None" = None
) -> "_T | Any":
    """
    Raises a #TypeError if *value* is not an instance of the specified *types*. If no message is
    provided, it will be auto-generated for the given *types*.
    """

    if not isinstance(value, types):
        if message is None:
            message = f"expected {_repr_types(types)}, got {type(value).__name__} instead"
        raise TypeError(_get_message(message))
    return value


def check_subclass_of(cls: type, types: _Types, message: "_Message | None" = None) -> type:
    """
    Raises a #TypeError if *cls* is not a subclass of one of the specified *types*. If *cls* is not
    a type, a different #TypeError is raised that does not include the specified *message*.
    """

    check_instance_of(cls, type)
    if not issubclass(cls, types):
        if message is None:
            message = f"{cls.__name__} is not a subclass of {_repr_types(types)}"
        raise TypeError(_get_message(message))
    return cls
