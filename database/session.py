"""Database session management.

Responsibilities:
- Create engine from DATABASE_URL
- Provide async-friendly session dependency for FastAPI
"""

from __future__ import annotations

import os
from sqlmodel import SQLModel, create_engine


def get_engine():
    database_url = os.getenv("DATABASE_URL", "sqlite:///./devflow.db")
    return create_engine(database_url, echo=False)


def init_db():
    """Create tables (placeholder)."""
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
