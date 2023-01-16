from sqlalchemy import String, BigInteger
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class Base(DeclarativeBase):
    ...


class GuildSettings(Base):
    __tablename__ = "GuildSettings"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    key: Mapped[String] = mapped_column(String(256))
    value: Mapped[String] = mapped_column(String(512))


class Database:
    def __init__(self, db_uri: str):
        self.__db = create_async_engine(db_uri)
        self.__connection: AsyncEngine | None = None
        self.__session_maker = async_sessionmaker(self.__db, expire_on_commit=False)

    async def connect(self):
        self.__connection = await self.__db.connect()

    async def disconnect(self):
        if self.__connection:
            await self.__connection.close()

    async def update_tables(self):
        async with self.__db.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def new_session(self) -> AsyncSession:
        return self.__session_maker()
