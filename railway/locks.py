from abc import ABC, abstractmethod
from typing import Any, Deque, Optional
import asyncio
import collections

from .compat import get_event_loop

__all__ = (
    'LockMixin',
    'Semaphore',
    'Lock'
)

class Locked(Exception):
    pass

class LockMixin(ABC):
    def __init__(self, *, loop: Optional[asyncio.AbstractEventLoop] = None):
        self._waiters: Deque['asyncio.Future[None]']= collections.deque()
        self._loop = loop or get_event_loop()

    @property
    def loop(self):
        """
        The event loop used.
        """
        return self._loop

    async def wait(self, *, timeout: Optional[float] = None):
        waiter = self.loop.create_future()
        self._waiters.append(waiter)

        try:
            await asyncio.wait_for(waiter, timeout=timeout)
        except:
            waiter.cancel()
            if self.should_wakeup() and not waiter.cancelled():
                self.wakeup()

            raise

    @abstractmethod
    async def acquire(self, *, wait: bool = True, timeout: Optional[float] = None) -> bool:
        raise NotImplementedError

    @abstractmethod
    def release(self) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def wakeup(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def should_wakeup(self) -> bool:
        raise NotImplementedError

    async def __aenter__(self):
        await self.acquire()

    async def __aexit__(self, *args: Any):
        self.release()

class Semaphore(LockMixin):
    """
    A semaphore, much like :class:`asyncio.Semaphore`

    Parameters
    ----------
    value: :class:`int`
        The internal counter used by the semaphore. Raises a :exc:`ValueError` if the value is negative, or
        a :exc:`TypeError` if the value is not an integer.
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop used by the semaphore.

    Example
    -------
    .. code-block:: python

        import railway
        import asyncio

        async def sleep(semaphore: railway.Semaphore):
            is_locked = semaphore.is_locked()
            print(is_locked)

            async with semaphore:
                await asyncio.sleep(2)

        async def main():
            semaphore = railway.Semaphore(2)

            tasks = [sleep(semaphore) for _ in range(3)]
            await asyncio.gather(*tasks)

        asyncio.run(main())
    """
    def __init__(self, value: int, *, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        if value < 0:
            raise ValueError('value must be a positive integer')

        self._value = value
        super().__init__(loop=loop)

    def __repr__(self) -> str:
        return f'<Semaphore value={self._value} is_locked={self.is_locked()}>'

    @property
    def value(self):
        """
        The internal counter.
        """
        return self._value

    def wakeup(self):
        """
        Wakes up a single waiter.
        """
        while self._waiters:
            waiter = self._waiters.popleft()

            if not waiter.done():
                waiter.set_result(None)
                return

    def should_wakeup(self) -> bool:
        return self._value > 0

    def is_locked(self):
        """
        True if the semaphore is locked, False otherwise.
        """
        return self._value <= 0

    async def acquire(self, *, wait: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquires the semaphore.
        If ``wait`` is False and the semaphore is locked, this method raisesan error.
        Otherwise it waits until the semaphore is released and returns True.

        Parameters
        ----------
        wait: :class:`bool`
            Whether to wait for the semaphore to be released. Defaults to ``True``.    
        timeout: :class:`float`
            The timeout in seconds. Defaults to ``None``.

        """
        if not wait and self.is_locked():
            raise Locked

        while self.is_locked():
            await self.wait(timeout=timeout)

        self._value -= 1
        return True

    def release(self):
        """
        Releases the semaphore.
        """
        self._value += 1
        self.wakeup()

class Lock(LockMixin):
    """
    A lock, much like :class:`asyncio.Lock`

    Parameters
    ----------
    loop: :class:`asyncio.AbstractEventLoop`
        The event loop used by the lock.

    Example
    -------
    .. code-block:: python

        import railway
        import asyncio

        async def sleep(lock: railway.Lock):
            is_locked = lock.is_locked()
            print(is_locked)

            async with lock:
                await asyncio.sleep(2)

        async def main():
            lock = railway.Lock()
            await asyncio.gather(sleep(lock), sleep(lock))

        asyncio.run(main())

    """
    def __init__(self, *, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        super().__init__(loop=loop)
        self._is_locked = False

    def __repr__(self) -> str:
        return f'<Lock is_locked={self.is_locked()}>'

    def is_locked(self):
        """
        True if the lock is locked, False otherwise.
        """
        return self._is_locked

    def wakeup(self):
        """
        Wakes up a single waiter.
        """
        if not self._waiters:
            return

        waiter = self._waiters.popleft()
        if not waiter.done():
            waiter.set_result(None)

    def should_wakeup(self) -> bool:
        return True

    async def acquire(self, *, wait: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquires the lock.
        If ``wait`` is False, and the lock is locked, this method raises an error,
        otherwise it waits until the lock is released and returns True.

        Parameters
        ----------
        wait: :class:`bool`
            Whether to wait for the lock to be released. Defaults to ``True``.  
        timeout: :class:`float`
            The timeout in seconds. Defaults to ``None``.
        """
        if not wait and self.is_locked():
            raise Locked

        while self.is_locked():
            await self.wait(timeout=timeout)

        self._is_locked = True
        return True

    def release(self):
        """
        Releases the lock.
        """
        self._is_locked = False
        self.wakeup()
