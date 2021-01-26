import asyncio

def task(*, seconds=0, minutes=0, hours=0, count=None, loop=None):
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
    def __init__(self, coro, seconds, minutes, hours, count: int=None, loop=None) -> None:
        self.coro = coro
        self.loop = loop
        self.count = count

        if not loop:
            self.loop = asyncio.get_event_loop()

        self._parse_duration(seconds, minutes, hours)
        self._task = None

        self._after_task = None
        self._before_task = None


    async def _prepare(self):
        if self.count:
            async def loop():
                counter = 0
                await self._call('before_task')

                while counter < self.count:
                    await self.coro()
                    await asyncio.sleep(self._duration)
                    counter += 1

                await self._call('after_task')

            return loop

        async def loop():
            await self._call('before_task')

            while True:
                await self.coro()

        return loop

    def _parse_duration(self, seconds, minutes, hours):
        duration = seconds + (minutes * 60.0) + (hours * 3600.0)
        if duration < 0:
            raise ValueError('The total duration cannot be 0')

        self._duration = duration

    def start(self):
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


