#!/usr/bin/env python3
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.db.session import engine, Base
import app.models  # noqa: F401


def main() -> None:
    """Create all database tables from SQLAlchemy models."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created (if the database exists and is reachable).")


if __name__ == "__main__":
    main()
