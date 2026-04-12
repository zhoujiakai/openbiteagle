#!/usr/bin/env python3
"""Initialize database tables."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.db import AsyncSessionLocal, Base, engine
from app.models import analysis, document, news, token  # noqa: F401 import models


async def main():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✅ 数据库表创建完成!")


if __name__ == "__main__":
    asyncio.run(main())
