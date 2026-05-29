import ssl
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

db_url = settings.database_url.split("?")[0]

ssl_context = ssl.create_default_context()

engine = create_async_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,        # cheaply detect dead connections before use
    pool_size=5,               # keep warm connections so most requests skip handshake
    max_overflow=5,
    pool_recycle=280,          # recycle before Neon drops idle connections (~5 min)
    pool_timeout=30,
    connect_args={
        "ssl": ssl_context,
        "timeout": 15,         # fail a stalled connect fast — asyncpg defaults to 60s
        "command_timeout": 30, # cap any single query
    },
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session