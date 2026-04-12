"""Data layer - database, cache, and message queue."""

from app.data.logger import create_logger


def __getattr__(name):
    """Lazy import heavy dependencies to avoid requiring them at module load time."""
    _lazy = {
        # Database
        "AsyncSession": "app.data.db",
        "AsyncSessionLocal": "app.data.db",
        "Base": "app.data.db",
        "engine": "app.data.db",
        "get_db": "app.data.db",
        # Cache
        "Cache": "app.data.cache",
        "get_cache": "app.data.cache",
        "close_cache": "app.data.cache",
        # RabbitMQ
        "RabbitMQ": "app.data.rabbit",
        "get_rabbit": "app.data.rabbit",
        "close_rabbit": "app.data.rabbit",
        "IncomingMessage": "app.data.rabbit",
        "RobustChannel": "app.data.rabbit",
        "RobustConnection": "app.data.rabbit",
    }
    if name in _lazy:
        import importlib

        module = importlib.import_module(_lazy[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Database
    "AsyncSession",
    "AsyncSessionLocal",
    "Base",
    "engine",
    "get_db",
    # Logger
    "create_logger",
    # Cache
    "Cache",
    "get_cache",
    "close_cache",
    # RabbitMQ
    "RabbitMQ",
    "get_rabbit",
    "close_rabbit",
    "IncomingMessage",
    "RobustChannel",
    "RobustConnection",
]
