"""SQLite-based storage layer for Pixl.

Provides relational storage with FTS5 full-text search for RAG,
proper foreign keys for the roadmap->epic->feature hierarchy,
event sourcing for audit trails, and indexed queries.

Usage:
    # Preferred: use the factory (returns StorageBackend protocol)
    from pixl.storage import create_storage
    db = create_storage(project_path)

    # Direct: use the SQLite implementation
    from pixl.storage.db import PixlDB
    db = PixlDB(project_path)
    db.initialize()
"""

from pixl.storage.db.connection import PixlDB

__all__ = ["PixlDB"]
