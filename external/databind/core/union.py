""" Provides the interface and implementations for representing the members of a union type. """

import abc
import dataclasses
import importlib
import types
import typing as t

import pkg_resources
from typeapi import ClassTypeHint, TypeHint

from databind.core.utils import T

__all__ = ["UnionMembers", "StaticUnionMembers", "EntrypointUnionMembers", "ImportUnionMembers", "ChainUnionMembers"]


class UnionMembers(abc.ABC):
    """Interface for representing the members of a union type. It defines methods to look up member type details
    based on name and Python type hints."""

    @abc.abstractmethod
    def get_type_id(self, type_: t.Any) -> str:
        """Given a Python type, return the ID of the type among the union members.

        Arguments:
          type_: The Python type to retrieve the ID for.
        Raises:
          ValueError: If the *type_* is not a member of the union.
        """

    @abc.abstractmethod
    def get_type_by_id(self, type_id: str) -> t.Any:
        """Given type ID, return the Python type associated with that ID among the union members.

        Arguments:
          type_id: The ID of the type to retrieve.
        Raises:
          ValueError: If the *type_id* is not an ID among the union members.
        """

    @abc.abstractmethod
    def get_type_ids(self) -> t.List[str]:
        """
        Returns:
          A list of the type names known to the union subtypes.
        Raises:
          NotImplementedError: If the method not supported by this implementation.
        """


@dataclasses.dataclass
class StaticUnionMembers(UnionMembers):
    """An implementation of #UnionMembers that reads statically from a dictionary. The dictionary can be altered
    subsequently, which is commonly done to explicitly register a member. The #members dictionary values may
    contain Python types or type hints understood by databind converters, as well as functions that return these
    types of values to allow for deferred evaluation.

    Example:

    ```py
    from databind.core.union import StaticUnionMembers

    members = StaticUnionMembers()

    @members.register('my-type')
    class MyType:
      pass
    ```

    The #register() method is also exposed for your convenience on the #Union settings type (see #Union.register()).
    """

    _TypeType = t.Union[type, TypeHint, t.Any]
    _TypeProvider = t.Union[_TypeType, t.Callable[[], _TypeType]]
    _MembersMappingType = t.Mapping[str, _TypeProvider]
    _MembersDictType = t.Dict[str, _TypeProvider]

    #: The member types dictionary.
    members: _MembersDictType = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        self._eval_cache: t.Dict[str, StaticUnionMembers._TypeType] = {}

    def get_type_id(self, type_: t.Any) -> str:
        for type_id in self.members:
            reference_type = self.get_type_by_id(type_id)
            # NOTE (@NiklasRosenstein): If we have a TypeHint hint, it could represent a generic alias, but we get
            #   passed the type of a value here as type_ which would have lost any generic aliasing if it was even
            #   present in the first place. We compare to the underlying type instead, but this means you cannot have
            #   a union with two members of the "same type" (even if they might differ in type parametrization).
            if reference_type == type_ or isinstance(reference_type, ClassTypeHint) and reference_type.type == type_:
                return type_id
        raise ValueError(f"type {type_} is not a member of {self}")

    def get_type_by_id(self, type_id: str) -> t.Any:
        try:
            return self._eval_cache[type_id]
        except KeyError:
            pass

        try:
            member = self.members[type_id]
        except KeyError:
            raise ValueError(f"{type_id!r} is not a type ID of {self}")

        if isinstance(member, types.FunctionType):
            member = self._eval_cache[type_id] = member()

        return member

    def get_type_ids(self) -> t.List[str]:
        return list(self.members.keys())

    def register(self, name: t.Optional[str] = None) -> t.Callable[[t.Type[T]], t.Type[T]]:
        def _decorator(type_: t.Type[T]) -> t.Type[T]:
            self.members[name or type_.__name__] = type_
            return type_

        return _decorator


@dataclasses.dataclass
class EntrypointUnionMembers(UnionMembers):
    """An implementation of #UnionMembers to treat the member type ID as a name for an entry in a entrypoint group."""

    group: str

    def __post_init__(self) -> None:
        self._entrypoints_cache: t.Optional[t.Dict[str, pkg_resources.EntryPoint]] = None

    @property
    def _entrypoints(self) -> t.Dict[str, pkg_resources.EntryPoint]:
        if self._entrypoints_cache is None:
            self._entrypoints_cache = {}
            for ep in pkg_resources.iter_entry_points(self.group):
                self._entrypoints_cache[ep.name] = ep
        return self._entrypoints_cache

    def get_type_id(self, type_: t.Any) -> str:
        for ep in self._entrypoints.values():
            if ep.load() == type_:
                return ep.name
        raise ValueError(f"unable to resolve type {type_!r} to a type ID for {self}")

    def get_type_by_id(self, type_id: str) -> t.Any:
        try:
            return self._entrypoints[type_id].load()
        except KeyError:
            raise ValueError(f"{type_id!r} is not a valid type ID for {self}")

    def get_type_ids(self) -> t.List[str]:
        return list(self._entrypoints.keys())


class ImportUnionMembers(UnionMembers):
    """This #UnionMembers subclass treats type IDs as fully qualified identifiers by which to import Python classes.

    This implementation does not support #UnionMembers.get_type_ids()."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"

    def get_type_id(self, type_: t.Any) -> str:
        if not isinstance(type_, type):
            raise ValueError(f"{type_!r} is not a type object and thus not a member of {self}")
        type_name = f"{type_.__module__}.{type_.__qualname__}"
        if "<" in type_.__qualname__:
            raise ValueError(f"non-global type {type_name} is not addressible")
        return type_name

    def get_type_by_id(self, type_id: str) -> t.Any:
        parts = type_id.split(".")
        offset = 1
        module_name = parts[0]
        module = importlib.import_module(module_name)

        # Import as many modules as we can.
        for offset, part in enumerate(parts[offset:], offset):
            sub_module_name = module_name + "." + part
            try:
                module = importlib.import_module(sub_module_name)
                module_name = sub_module_name
            except ImportError as exc:
                if sub_module_name in str(exc):
                    break
                raise

        # Read the class.
        target = module
        for offset, part in enumerate(parts[offset:], offset):
            target = getattr(target, part)

        if not isinstance(target, type):  # type: ignore[unreachable]
            raise ValueError(f"{type_id!r} does not point to a type (got {type(target).__name__} instead)")

        return target  # type: ignore[unreachable]

    def get_type_ids(self) -> t.List[str]:
        raise NotImplementedError


@dataclasses.dataclass
class ChainUnionMembers(UnionMembers):
    """Chain multiple implementations of #UnionMembers."""

    delegates: t.List[UnionMembers]

    def __init__(self, *delegates: UnionMembers) -> None:
        self.delegates = list(delegates)

    def get_type_id(self, type_: t.Any) -> str:
        errors = []
        for delegate in self.delegates:
            try:
                return delegate.get_type_id(type_)
            except ValueError as exc:
                errors.append(exc)
        raise ValueError(f"{type_!r} is not a member of {self}\n" + "- \n".join(map(str, errors)))

    def get_type_by_id(self, type_id: str) -> t.Any:
        errors = []
        for delegate in self.delegates:
            try:
                return delegate.get_type_by_id(type_id)
            except ValueError as exc:
                errors.append(exc)
        raise ValueError(f"{type_id!r} type ID is not a member of {self}\n" + "- \n".join(map(str, errors)))

    def get_type_ids(self) -> t.List[str]:
        from nr.stream import Stream

        def _gen() -> t.Iterator[str]:
            for delegate in self.delegates:
                try:
                    yield from delegate.get_type_ids()
                except NotImplementedError:
                    pass

        return Stream(_gen()).concat().distinct().collect()
