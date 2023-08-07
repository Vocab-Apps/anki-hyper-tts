__version__ = "0.1.0"

import collections
import functools
import itertools
import typing as t

if t.TYPE_CHECKING:
    from ._optional import Optional

from ._notset import NotSet

R = t.TypeVar("R")
T = t.TypeVar("T")
T_co = t.TypeVar("T_co", covariant=True)
U = t.TypeVar("U")
U_co = t.TypeVar("U_co", covariant=True)
Aggregator = t.Callable[[T, U], T]
Collector = t.Callable[[t.Iterable[T]], R]


class Stream(t.Generic[T_co], t.Iterable[T_co]):
    """
    A stream is an iterable with utility methods to transform it.
    """

    def __init__(self, iterable: t.Optional[t.Iterable[T_co]] = None) -> None:
        if iterable is None:
            iterable = ()
        self._it = iter(iterable)
        self._original: t.Optional[t.Iterable[T_co]] = iterable

    def __iter__(self) -> "Stream[T_co]":
        return self

    def __next__(self) -> T_co:
        self._original = None
        return next(self._it)

    @t.overload
    def __getitem__(self, val: slice) -> "Stream[T_co]":
        ...

    @t.overload
    def __getitem__(self, val: int) -> T_co:
        ...

    def __getitem__(self, val):  # type: ignore[no-untyped-def]
        if isinstance(val, slice):
            return self.slice(val.start, val.stop, val.step)
        elif isinstance(val, int):
            if val >= 0:
                for index, value in enumerate(self):
                    if index == val:
                        return value
                raise IndexError("Stream has no element at position {}".format(val))
            else:
                queue = collections.deque(self, maxlen=abs(val))
                if len(queue) < abs(val):
                    raise IndexError("Stream has no element at position {}".format(val))
                return queue[0]
        else:
            raise TypeError("{} object is only subscriptable with slices".format(type(self).__name__))

    def next(self) -> T_co:
        return next(self._it)

    def append(self, *its: t.Iterable[T_co]) -> "Stream[T_co]":
        return Stream(itertools.chain(self._it, *its))

    @t.overload
    def batch(self, n: int) -> "Stream[t.List[T_co]]":
        ...

    @t.overload
    def batch(self, n: int, collector: Collector[T_co, R]) -> "Stream[R]":
        ...

    def batch(self, n, collector=None):  # type: ignore[no-untyped-def]
        """
        Convert the stream into a stream of batches of size *n*, where each element of the stream
        contains the result of the *collector* after passing up to *n* elements of the original
        stream into it.
        """

        iterable = iter(self._it)
        if collector is None:
            collector = list

        def take(first: T) -> t.Iterator[T_co]:
            yield t.cast(T_co, first)
            count = 1
            while count < n:
                try:
                    yield next(iterable)
                except StopIteration:
                    break
                count += 1

        def generate_batches() -> t.Iterator[R]:
            while True:
                try:
                    first = next(iterable)
                except StopIteration:
                    break
                yield collector(take(first))

        return Stream(generate_batches())

    def bipartition(self, predicate: t.Callable[[T_co], bool]) -> "t.Tuple[Stream[T_co], Stream[T_co]]":
        """
        Use a predicate to partition items into false and true entries.
        Returns a tuple of two streams with the first containing all elements
        for which *pred* returned #False and the other containing all elements
        where *pred* returned #True.
        """

        t1, t2 = itertools.tee(self._it)
        return Stream(itertools.filterfalse(predicate, t1)), Stream(filter(predicate, t2))

    def call(self: "Stream[t.Callable[..., R]]", *a: t.Any, **kw: t.Any) -> "Stream[R]":
        """
        Calls every item in *iterable* with the specified arguments.
        """

        return Stream(x(*a, **kw) for x in self._it)

    @t.overload
    def collect(self) -> t.List[T_co]:
        ...

    @t.overload
    def collect(self, collector: Collector[T_co, R]) -> R:
        ...

    def collect(self, collector=list):  # type: ignore[no-untyped-def]
        """
        Collects the stream into a collection.
        """

        if isinstance(collector, type) and isinstance(self._original, collector):
            # NOTE(NiklasRosenstein): This is an optimization to retrieve the original underlying
            #   collection if the stream has not been advanced yet.
            return self._original

        return collector(self._it)

    def count(self) -> int:
        """
        Returns the number of items in the stream. This fully consumes the stream.
        """

        count = 0
        while True:
            try:
                next(self._it)
            except StopIteration:
                break
            count += 1
        return count

    @t.overload
    def concat(s: "Stream[str]") -> "Stream[str]":
        ...

    @t.overload
    def concat(s: "Stream[t.Iterable[T]]") -> "Stream[T]":
        ...

    def concat(self):  # type: ignore[no-untyped-def]
        """
        Concatenate all values in the stream into a single stream of values.
        """

        def generator():  # type: ignore[no-untyped-def]
            for it in self:
                for element in t.cast(t.Iterable[t.Any], it):
                    yield element

        return Stream(generator())  # type: ignore[no-untyped-call]

    def consume(self, n: t.Optional[int] = None) -> "Stream[T_co]":
        """
        Consume the contents of the stream, up to *n* elements if the argument is specified.
        """

        if n is not None:
            for _ in range(n):
                try:
                    next(self._it)
                except StopIteration:
                    break
        else:
            while True:
                try:
                    next(self._it)
                except StopIteration:
                    break
        return self

    def distinct(
        self,
        key: t.Optional[t.Callable[[T_co], t.Any]] = None,
        skip: t.Union[t.MutableSet[T_co], t.MutableSequence[T_co], None] = None,
    ) -> "Stream[T_co]":
        """
        Yields unique items from *iterable* whilst preserving the original order. If *skip* is
        specified, it must be a set or sequence of items to skip in the first place (ie. items to
        exclude from the returned stream). The specified set/sequence is modified in-place. Using a
        set is highly recommended for performance purposes.
        """

        if key is None:
            key_func = lambda x: x  # noqa: E731
        else:
            key_func = key

        def generator() -> t.Generator[T_co, None, None]:
            seen = set() if skip is None else skip
            mark_visited = seen.add if isinstance(seen, t.MutableSet) else seen.append
            check_visited = seen.__contains__
            for item in self._it:
                key_val = key_func(item)  # type: ignore[no-untyped-call]
                if not check_visited(key_val):
                    mark_visited(key_val)
                    yield item

        return Stream(generator())

    def dropwhile(self, predicate: t.Callable[[T_co], bool]) -> "Stream[T_co]":
        return Stream(itertools.dropwhile(predicate, self._it))

    def dropnone(self: "Stream[t.Optional[T_co]]") -> "Stream[T_co]":
        return Stream(x for x in self._it if x is not None)

    def filter(self, predicate: t.Callable[[T_co], bool]) -> "Stream[T_co]":
        """
        Agnostic to Python's built-in `filter()` function.
        """

        return Stream(x for x in self._it if predicate(x))

    def first(self) -> t.Optional[T_co]:
        """
        Returns the first element of the stream, or `None`.
        """

        try:
            return self.next()
        except StopIteration:
            return None

    def firstopt(self) -> "Optional[T_co]":
        """
        Returns the first element of the stream as an `Optional`.
        """

        from ._optional import Optional

        return Optional(self.first())

    def flatmap(self, func: t.Callable[[T_co], t.Iterable[R]]) -> "Stream[R]":
        """
        Same as #map() but flattens the result.
        """

        def generator() -> t.Generator[R, None, None]:
            for x in self._it:
                for y in func(x):
                    yield y

        return Stream(generator())

    @t.overload
    def groupby(self, key: t.Callable[[T_co], R]) -> "Stream[t.Tuple[R, t.Iterable[T_co]]]":
        ...

    @t.overload
    def groupby(
        self, key: t.Callable[[T_co], R], collector: t.Callable[[t.Iterable[T_co]], U]
    ) -> "Stream[t.Tuple[R, U]]":
        ...

    def groupby(self, key: t.Callable[[T_co], U], collector: t.Optional[Collector[T_co, R]] = None):  # type: ignore[no-untyped-def]  # noqa: E501
        if collector is None:
            return Stream(itertools.groupby(self._it, key))
        else:

            def generator():  # type: ignore[no-untyped-def]
                assert collector is not None
                g: t.Iterable[T_co]
                for k, g in itertools.groupby(self._it, key):
                    yield k, collector(g)

            return Stream(generator())  # type: ignore[no-untyped-call]

    def map(self, func: t.Callable[[T_co], R]) -> "Stream[R]":
        """
        Agnostic to Python's built-in `map()` function.
        """

        return Stream(func(x) for x in self._it)

    def of_type(self, type: t.Type[U_co]) -> "Stream[U_co]":
        """
        Filters using #isinstance().
        """

        return Stream(x for x in self._it if isinstance(x, type))

    @t.overload
    def reduce(self, aggregator: Aggregator[T_co, T_co]) -> T_co:
        ...

    @t.overload
    def reduce(self, aggregator: Aggregator[R, T_co], initial: R) -> R:
        ...

    def reduce(self, aggregator, initial=NotSet.Value):  # type: ignore[no-untyped-def]
        if initial is NotSet.Value:
            return functools.reduce(aggregator, self._it)
        else:
            return functools.reduce(aggregator, self._it, initial)

    @t.overload
    def slice(self, stop: int) -> "Stream[T_co]":
        ...

    @t.overload
    def slice(self, start: int, stop: int, step: int = 1) -> "Stream[T_co]":
        ...

    def slice(self, start, stop=None, step=None):  # type: ignore[no-untyped-def]
        return Stream(itertools.islice(self._it, start, stop, step))

    def sortby(self, by: t.Union[str, t.Callable[[T_co], t.Any]], reverse: bool = False) -> "Stream[T_co]":
        """
        Creates a new sorted stream. Internally the #sorted() built-in function is used so a new list
        will be created temporarily.

        # Parameters
        by (str, callable): Specify by which dimension to sort the stream. If a string is specified,
          it will be used to retrieve a key or attribute from the values in the stream. In the case of
          a callable, it will be used directly as the `key` argument to #sorted().
        """

        if isinstance(by, str):
            lookup_attr = by

            def by(item):  # type: ignore[no-untyped-def]
                if isinstance(item, t.Mapping):
                    return item[lookup_attr]
                else:
                    return getattr(item, lookup_attr)

        by = t.cast(t.Callable[[T_co], t.Any], by)
        return Stream(sorted(self._it, key=by, reverse=reverse))

    def sort(self: "Stream[T]", reverse: bool = False) -> "Stream[T]":
        return self.sortby(lambda x: x, reverse)

    def takewhile(self, predicate: t.Callable[[T_co], bool]) -> "Stream[T_co]":
        return Stream(itertools.takewhile(predicate, self._it))
