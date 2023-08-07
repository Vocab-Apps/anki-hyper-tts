import logging
import threading
from typing import Any, Callable, Generic, List, Tuple, TypeVar

T = TypeVar("T")
R = TypeVar("R")

logger = logging.getLogger(__name__)
Subscriber = Callable[["Refreshable[T]"], None]


class Refreshable(Generic[T]):
    def __init__(self, initial: T) -> None:
        self._lock = threading.Lock()
        self._current = initial
        self._subscribers: "List[Subscriber[T]]" = []

    def __getstate__(self) -> "Tuple[Any, ...]":
        return self, (self._current, self._subscribers)

    def __setstate__(self, state: "Tuple[Any, ...]") -> None:
        self._lock = threading.Lock()
        self._current, self._subscribers = state[1]

    def get(self) -> T:
        with self._lock:
            return self._current

    def update(self, value: T) -> None:
        with self._lock:
            self._current = value
            subscribers = self._subscribers[:]
        for subscriber in subscribers:
            try:
                subscriber(self)
            except Exception:
                logger.exception("Error in Refreshable subscriber")

    def subscribe(self, subscriber: "Subscriber[T]") -> None:
        with self._lock:
            self._subscribers.append(subscriber)
        try:
            subscriber(self)
        except Exception:
            logger.exception("Error in Refreshable subscriber")

    def map(self, mapper: Callable[[T], R]) -> "Refreshable[R]":
        """
        Map the value of the refreshable to a new refreshable that automatically gets updated when the
        parent is updated. Be aware that this method should be used sparingly as it registers a new
        subscriber to this refreshable that will never be disposed of again.
        """

        child = Refreshable(mapper(self.get()))

        def refresh(_parent: Refreshable[T]) -> None:
            child.update(mapper(self.get()))

        self.subscribe(refresh)
        return child
