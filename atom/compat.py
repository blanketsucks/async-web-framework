import sys
import asyncio

if sys.platform == 'linux':
    try:
        import uvloop
    except ImportError:
        has_uvloop = False
    else:
        has_uvloop = True

    if has_uvloop:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

def get_running_loop():
    return asyncio.get_running_loop()

def get_event_loop():
    return asyncio.get_event_loop()
