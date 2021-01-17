import asyncio

def task(*, seconds=0, minutes=0, hours=0, count=0, loop=None):
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
    def __init__(self, coro, seconds, minutes, hours, count: int, loop=None) -> None:
        self.coro = coro
        self.loop = loop
        self.count = count

        if not loop:
            self.loop = asyncio.get_event_loop()

        self._parse_duration(seconds, minutes, hours)

        self.seconds = seconds
        self.minutes = minutes
        self.hours = hours

    async def _loop(self):
        counter = 0
        await self._call_task_functions('_before_task')

        while counter < self.count:
            await self.coro()
            await asyncio.sleep(self._duration)
            counter += 1
            
        await self._call_task_functions('_after_task')

    def _parse_duration(self, seconds, minutes, hours):
        duration = seconds + (minutes * 60.0) + (hours * 3600.0)
        if duration < 0:
            raise ValueError('The total duration cannot be 0')

        self._duration = duration

    def start(self):
        self._task = self.loop.create_task(self._loop())
        return self._task

    async def _call_task_functions(self, name: str):
        try:
            coro = getattr(self, name)
        except AttributeError:
            return
            
        await coro()

    def before_task(self, coro):
        self._before_task = coro
        return coro

    def after_task(self, coro):
        self._after_task = coro
        return coro

