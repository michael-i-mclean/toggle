import asyncio
import pytest
from pathlib import Path

from monitor import watcher


@pytest.mark.asyncio
async def test_watch_ftp_detects_new_file(tmp_path):
    """Start the watcher, create a file in the temp dir, and assert a queue event."""

    q = asyncio.Queue()

    # Start the watcher as a background task
    task = asyncio.create_task(watcher.watch_ftp(q, directory=str(tmp_path)))

    try:
        # Give the watcher a moment to start
        await asyncio.sleep(0.1)

        # Create a new file which should trigger an event
        new_file = tmp_path / "newfile.txt"
        new_file.write_bytes(b"hello world")

        # Await an item on the queue (with timeout)
        item = await asyncio.wait_for(q.get(), timeout=5.0)

        assert isinstance(item, dict)
        assert item["path"].endswith("newfile.txt")
        assert item["type"] in ("added", "modified")

    finally:
        # Cancel the watcher task and ensure it shuts down
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
