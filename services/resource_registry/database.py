"""
数据库连接和会话管理
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator
import os
from .models import Base

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/intent_system"
)

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库（创建表）"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话（依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """获取数据库会话（上下文管理器）"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
