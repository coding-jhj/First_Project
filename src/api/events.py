import asyncio
import json
from collections import defaultdict
from contextlib import asynccontextmanager


_subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)


@asynccontextmanager
async def subscribe(session_id: str):
    queue: asyncio.Queue = asyncio.Queue(maxsize=16)
    _subscribers[session_id].add(queue)
    try:
        yield queue
    finally:
        _subscribers[session_id].discard(queue)
        if not _subscribers[session_id]:
            _subscribers.pop(session_id, None)


async def publish(session_id: str, event: dict) -> None:
    payload = json.dumps(event, ensure_ascii=False)
    for queue in list(_subscribers.get(session_id, ())):
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            pass
