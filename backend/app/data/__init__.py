"""数据层 - 数据库、缓存和消息队列。"""

from app.data.logger import create_logger


def __getattr__(name):
    """延迟加载重量级依赖，避免在模块加载时就需要它们。"""
    _lazy = {
        # 数据库
        "AsyncSession": "app.data.db",
        "AsyncSessionLocal": "app.data.db",
        "Base": "app.data.db",
        "engine": "app.data.db",
        "get_db": "app.data.db",
        # 缓存
        "Cache": "app.data.cache",
        "get_cache": "app.data.cache",
        "close_cache": "app.data.cache",
        # 消息队列
        "RabbitMQ": "app.data.rabbit",
        "get_rabbit": "app.data.rabbit",
        "close_rabbit": "app.data.rabbit",
        "IncomingMessage": "app.data.rabbit",
        "RobustChannel": "app.data.rabbit",
        "RobustConnection": "app.data.rabbit",
        # 任务工作器
        "Worker": "app.data.mq",
    }
    if name in _lazy:
        import importlib

        module = importlib.import_module(_lazy[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # 数据库
    "AsyncSession",
    "AsyncSessionLocal",
    "Base",
    "engine",
    "get_db",
    # 日志
    "create_logger",
    # 缓存
    "Cache",
    "get_cache",
    "close_cache",
    # 消息队列
    "RabbitMQ",
    "get_rabbit",
    "close_rabbit",
    "IncomingMessage",
    "RobustChannel",
    "RobustConnection",
    # 任务工作器
    "Worker",
]
