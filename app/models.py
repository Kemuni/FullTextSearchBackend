from datetime import datetime

from sqlalchemy import ARRAY, Column, DateTime, Integer, String, UnicodeText

from app.core.db import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(UnicodeText, nullable=False)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)  # type: ignore
    rubrics = Column(ARRAY(String), nullable=False)
