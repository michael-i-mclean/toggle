from typing import Optional
import asyncio
from watchfiles import awatch

async def watch_ftp(
        queue: asyncio.Queue,
        directory: Optional[str] = "" 
    ):
    print(f"[WATCHER] Starting on {directory}")
    async for changes in awatch(directory):
        for change, path in changes:
            await queue.put({"type": change.name, "path": path})
