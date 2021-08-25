import sys
import asyncio

if sys.platform == 'linux':
    try:
        import uvloop
    except ImportError:
        uvloop = None

    if uvloop:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

def get_running_loop():
    return asyncio.get_running_loop()

def get_event_loop():
    return asyncio.get_event_loop()

def get_event_loop_policy():
    return asyncio.get_event_loop_policy()