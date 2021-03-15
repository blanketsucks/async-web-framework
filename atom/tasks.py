import asyncio

__all__ = (
    'task',
    'Task'
)


def task(*, seconds: int=0,
         minutes: int=0,
         hours: int=0,
         count: int=None,
         loop: asyncio.AbstractEventLoop=None):
    def wrapper(func):
        cls = Task(
            func,
            seconds,
            minutes,
            hours,
            count,
            loop
        )
        return cls

    return wrapper


class Task:
    def __init__(self, coro, seconds, minutes, hours, count: int = None, loop=None) -> None:
        self.coro = coro
        self.loop = loop
        self.count = count

        if not loop:
            self.loop = asyncio.get_event_loop()

        self._parse_duration(seconds, minutes, hours)

        self._task = None
        self.is_running = False

    async def _prepare(self):
        counter = 0
        await self._call('before_task')

        while True:
            await self.coro()
            await asyncio.sleep(self._duration)
            counter += 1

            if self.count == counter:
                break

        await self._call('after_task')

    def _parse_duration(self, seconds, minutes, hours):
        duration = seconds + (minutes * 60.0) + (hours * 3600.0)
        if duration < 0:
            raise ValueError('The total duration cannot be 0')

        self._duration = duration

    def start(self):
        self.is_running = True

        self._task = self.loop.create_task(self._prepare())
        return self._task

    def stop(self):
        self._task.cancel()

    async def _call(self, name: str):
        name = '_' + name
        try:
            coro = getattr(self, name)
        except AttributeError:
            return

        await coro()

    def before_task(self):
        def decorator(func):
            self._before_task = func

        return decorator

    def after_task(self):
        def decorator(func):
            self._after_task = func

        return decorator
