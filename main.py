from toggle_service.app import create_app

# Expose a module-level ASGI app so uvicorn/gunicorn can load it:
app = create_app()

