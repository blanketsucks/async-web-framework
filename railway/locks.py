import asyncio
import collections
from typing import Deque, Optional

__all__ = (
    'Semaphore',
    'Lock'
)

class _LockMixin:
    def __init__(self, *, loop: asyncio.AbstractEventLoop=None):
        self._waiters: Deque['asyncio.Future[None]']= collections.deque()
        self._loop = loop or asyncio.get_event_loop()

    @property
    def loop(self):
        """
        The event loop used.
        """
        return self._loop

    async def acquire(self):
        raise NotImplementedError

    def release(self):
        raise NotImplementedError

    async def __aenter__(self):
        await self.acquire()

    async def __aexit__(self, *args):
        self.release()

class Semaphore(_LockMixin):
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
    def __init__(self, value: int, *, loop: asyncio.AbstractEventLoop=None) -> None:
        if not isinstance(value, int):
            raise TypeError('value must be an integer')

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

    def is_locked(self):
        """
        True if the semaphore is locked, False otherwise.
        """
        return self._value <= 0

    async def wait(self):
        """
        Waits until the semaphore is released.
        """
        waiter = self.loop.create_future()
        self._waiters.append(waiter)

        try:
            await waiter
        except:
            waiter.cancel()
            if self.value > 0 and not waiter.cancelled():
                self.wakeup()

            raise

    async def acquire(self, *, wait: bool=True) -> bool:
        """
        Acquires the semaphore.
        If ``wait`` is False, and the semaphore is locked, this method returns False immediately,
        otherwise it waits until the semaphore is released and returns True.

        Parameters
        ----------
        wait: :class:`bool`
            Whether to wait for the semaphore to be released. Defaults to ``True``.    
    
        """
        if not wait and self.is_locked():
            return False

        while self.is_locked():
            await self.wait()

        self._value -= 1
        return True

    def release(self):
        """
        Releases the semaphore.
        """
        self._value += 1
        self.wakeup()

class Lock(_LockMixin):
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
    def __init__(self, *, loop: asyncio.AbstractEventLoop=None):
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

    async def wait(self):
        """
        Waits until the lock is released.
        """
        waiter = self._loop.create_future()
        self._waiters.append(waiter)

        try:
            await waiter
        except:
            waiter.cancel()
            if not waiter.cancelled():
                self.wakeup()

            raise

    async def acquire(self, *, wait: bool=True):
        """
        Acquires the lock.
        If ``wait`` is False, and the lock is locked, this method returns False immediately,
        otherwise it waits until the lock is released and returns True.

        Parameters
        ----------
        wait: :class:`bool`
            Whether to wait for the lock to be released. Defaults to ``True``.    
        """
        if not wait and self.is_locked():
            return False

        while self.is_locked():
            await self.wait()

        self._is_locked = True
        return True

    def release(self):
        """
        Releases the lock.
        """
        self._is_locked = False
        self.wakeup()

class _MaybeSemaphore:
    def __init__(self, value: Optional[int]):
        self.semaphore = Semaphore(value) if value else None

    async def __aenter__(self):
        if self.semaphore:
            await self.semaphore.acquire()

    async def __aexit__(self):
        if self.semaphore:
            self.semaphore.release()