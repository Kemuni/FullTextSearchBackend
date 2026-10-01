from typing import Generator, Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import engine, async_session_maker


def get_db() -> Generator[AsyncSession]:
    with async_session_maker(engine) as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db)]
