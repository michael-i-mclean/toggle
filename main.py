from toggle_service.app import create_app
from monitor.watcher import watch_ftp

CONFIG = {
    "watcher_fn": watch_ftp
        }

# Expose a module-level ASGI app so uvicorn/gunicorn can load it:
# app = create_app(new_file_queue = new_file_queue, watcher.watch_ftp)
app = create_app(**CONFIG)
