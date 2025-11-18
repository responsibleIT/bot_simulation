"""
Appwrite helpers built on the official Python SDK (TablesDB).

We expose a small set of convenience functions that the rest of the app uses:
- q_equal(field, value)
- list_documents(table_id, queries=None)
- create_document(table_id, document_id, data)
- update_document(table_id, document_id, data)
- generate_id()
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from config import IMAGE_BUCKET_ID

from appwrite.client import Client
from appwrite.id import ID
from appwrite.query import Query
from appwrite.services.tables_db import TablesDB
from appwrite.services.storage import Storage
from appwrite.input_file import InputFile
import requests

from config import (
    APPWRITE_ENDPOINT,
    APPWRITE_PROJECT_ID,
    APPWRITE_API_KEY,
    DATABASE_ID,
)

# ---------------------------------------------------------------------------
# Singleton client + TablesDB
# ---------------------------------------------------------------------------

_client: Optional[Client] = None
_tables_db: Optional[TablesDB] = None
_storage: Optional[Storage] = None


def _get_client() -> Client:
    """Return a singleton Appwrite Client configured from config.py."""
    global _client
    if _client is None:
        c = Client()
        (
            c.set_endpoint(APPWRITE_ENDPOINT)
             .set_project(APPWRITE_PROJECT_ID)
             .set_key(APPWRITE_API_KEY)
        )
        _client = c
    return _client


def _get_tables_db() -> TablesDB:
    """Return a singleton TablesDB service."""
    global _tables_db
    if _tables_db is None:
        _tables_db = TablesDB(_get_client())
    return _tables_db

def _get_storage() -> Storage:
    """Return a singleton Storage service."""
    global _storage
    if _storage is None:
        _storage = Storage(_get_client())
    return _storage

# ---------------------------------------------------------------------------
# Query helper
# ---------------------------------------------------------------------------

def q_equal(field: str, value: Any) -> str:
    """
    Thin wrapper around Query.equal.

    For a single value, usage is:

        q_equal("email", "test@hva.nl")

    which is equivalent to:

        Query.equal("email", "test@hva.nl")

    If you ever need multiple values, you can call Query.equal directly with
    a list, e.g. Query.equal("title", ["Avatar", "Lord of the Rings"]).
    """
    return Query.equal(field, value)


# ---------------------------------------------------------------------------
# “Document” helpers (actually rows in TablesDB)
# ---------------------------------------------------------------------------

def list_documents(
    table_id: str,
    queries: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    List rows from a table (called 'documents' in the rest of the app).

    Returns a list of row dicts. The SDK returns an object with a 'rows' field.
    """
    tables = _get_tables_db()
    kwargs: Dict[str, Any] = {
        "database_id": DATABASE_ID,
        "table_id": table_id,
    }
    if queries:
        kwargs["queries"] = queries

    result = tables.list_rows(**kwargs)
    # TablesDB returns: { "rows": [ ... ], "total": ..., ... }
    return result.get("rows", [])


def create_document(
    table_id: str,
    document_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a new row in a table.

    The rest of the app still calls this 'document' for backwards compatibility.
    """
    tables = _get_tables_db()
    return tables.create_row(
        database_id=DATABASE_ID,
        table_id=table_id,
        row_id=document_id,
        data=data,
    )


def update_document(
    table_id: str,
    document_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Update an existing row in a table.
    """
    tables = _get_tables_db()
    return tables.update_row(
        database_id=DATABASE_ID,
        table_id=table_id,
        row_id=document_id,
        data=data,
    )

# ---------------------------------------------------------------------------
# “Bucket” helpers for uploading images
# ---------------------------------------------------------------------------

def upload_image_file(file_name: str, file_bytes: bytes) -> str:
    """
    Upload an image to the configured IMAGE_BUCKET_ID and
    return the Appwrite file ID.
    """
    storage = _get_storage()
    result = storage.create_file(
        bucket_id=IMAGE_BUCKET_ID,
        file_id=ID.unique(),
        file=InputFile.from_bytes(file_bytes, file_name),
    )
    return result["$id"]


def get_image_bytes(file_id: str) -> bytes:
    """
    Download an image from the bucket as raw bytes, suitable for st.image().
    """
    storage = _get_storage()
    # get_file_view returns a bytes-like object for images
    return storage.get_file_view(bucket_id=IMAGE_BUCKET_ID, file_id=file_id)


def upload_image_from_url(url: str, file_name: str = "image.png") -> str:
    """
    Download an image from a URL and upload it to Appwrite.
    Returns the new file ID.
    Useful for bot-generated images (e.g. from OpenAI).
    """
    resp = requests.get(url)
    resp.raise_for_status()
    return upload_image_file(file_name, resp.content)


def generate_id() -> str:
    """
    Generate a unique ID using Appwrite's ID.unique() helper.
    """
    return ID.unique()
