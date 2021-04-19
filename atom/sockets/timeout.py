
import asyncio
import enum
import typing

class State(enum.IntEnum):
    INIT = 1
    ENTER = 2
    TIMEOUT = 3
    EXIT = 0


class timeout:
    def __init__(self, *, delay: float=..., loop: asyncio.AbstractEventLoop=...) -> None:
        if loop is ...:
            loop = asyncio.get_event_loop()
        
        if delay is ...:
            delay = 180.0
        
        self.loop = loop

        self._state = State.INIT

        self._task = self._current_task()
        self._timeout_handler = None

        self.__time = delay
        self.shift_to(self.loop.time() + delay)

    def __repr__(self) -> str:
        return f'<timeout delay={self.__time}>'

    async def __aenter__(self):
        if self._state != State.INIT:
            raise RuntimeError("invalid state {}".format(self._state.value))
            
        self._state = State.ENTER
        return self

    async def __aexit__(self, type, *args):
        if type is asyncio.CancelledError and self._state == State.TIMEOUT:
            self._timeout_handler = None
            raise asyncio.TimeoutError

        self._state = State.EXIT
        self._cancel()

        return self

    def _current_task(self):
        return asyncio.current_task(loop=self.loop)

    def state(self) -> typing.Tuple[str, State]:
        if self._state is State.INIT:
            return "INIT", self._state

        if self._state is State.EXIT:
            return 'EXIT', self._state

        if self._state is State.ENTER:
            return 'ENTER', self._state

        if self._state is State.TIMEOUT:
            return 'TIMEOUT', self._state

    def cancel(self) -> None:
        if self._state not in (State.INIT, State.ENTER):
            raise RuntimeError("invalid state {}".format(self._state.value))

        self._cancel()

    def _cancel(self) -> None:
        if self._timeout_handler is not None:
            self._timeout_handler.cancel()
            self._timeout_handler = None

    def shift_to(self, delay: float) -> None:
        if self._state == State.EXIT:
            raise RuntimeError("cannot reschedule after exit from context manager")

        if self._state == State.TIMEOUT:
            raise RuntimeError("cannot reschedule expired timeout")

        if self._timeout_handler is not None:
            self._timeout_handler.cancel()

        self._delay = delay
        now = self.loop.time()

        if delay <= now:
            self._timeout_handler = None

            if self._state == State.INIT:
                raise asyncio.TimeoutError
            else:

                raise asyncio.CancelledError

        self._timeout_handler = self.loop.call_at(
            delay, self._on_timeout, self._task
        )

    def _on_timeout(self, task: asyncio.Task) -> None:
        task.cancel()
        self._state = State.TIMEOUT
