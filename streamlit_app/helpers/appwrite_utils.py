"""Appwrite helper utilities.

This module centralises all interaction with the Appwrite API.  It attempts to
use the official Python SDK whenever available for type‑safe access to
databases and queries.  If the SDK cannot be imported (for example when
developing offline), it falls back to simple REST calls via ``requests``.  The
rest of the application code can remain agnostic to whether the SDK or REST
implementation is being used.

Use :func:`q_equal` to build equality queries in a backend‑agnostic way.  Use
:func:`list_documents`, :func:`create_document` and :func:`update_document` to
interact with your collections.  See the README for details on configuring
Appwrite credentials via environment variables or a ``.env`` file.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

# Import configuration from the streamlit_app package.  Absolute import is used
# here to ensure the module resolves correctly when imported from subpackages.
from config import (
    APPWRITE_ENDPOINT,
    APPWRITE_PROJECT_ID,
    APPWRITE_API_KEY,
    DATABASE_ID,
)

# ----------------------------------------------------------------------------
# Official Appwrite SDK implementation
#
# This module now requires the ``appwrite`` Python package to be installed.
# It provides thin wrappers around the official SDK to simplify usage in the
# rest of the application.  Queries are constructed using the ``Query`` class
# and passed directly to the SDK without any manual HTTP handling.
#
# If the SDK cannot be imported, a clear ImportError will be raised when this
# module is imported.  Please ensure ``pip install appwrite`` is executed in
# your environment.
# ----------------------------------------------------------------------------

from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.query import Query
from appwrite.id import ID

_client: Optional[Client] = None
_databases: Optional[Databases] = None


def _ensure_client() -> Databases:
    """Initialise and cache the Appwrite client and database service.

    Returns the ``Databases`` service instance.  This function is idempotent and
    will only construct the client once.
    """
    global _client, _databases
    if _client is None or _databases is None:
        if not (APPWRITE_ENDPOINT and APPWRITE_PROJECT_ID and APPWRITE_API_KEY):
            raise RuntimeError(
                "Appwrite configuration is missing. Please set APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID and APPWRITE_API_KEY."
            )
        client = Client()
        client.set_endpoint(APPWRITE_ENDPOINT)
        client.set_project(APPWRITE_PROJECT_ID)
        client.set_key(APPWRITE_API_KEY)
        _client = client
        _databases = Databases(_client)
    return _databases  # type: ignore


def q_equal(field: str, value: Any) -> Query:
    """Construct a Query.equal() object for the given field and value.

    Appwrite expects the values to be provided as an array for equality checks.
    This helper wraps single values into a list automatically.  If ``value`` is
    already a list or tuple, it is passed through unchanged.

    Example::

        q_equal("email", "test@hva.nl")  # becomes Query.equal("email", ["test@hva.nl"])

    Returns a ``Query`` object suitable for use with the SDK.
    """
    # Wrap non-sequence values in a list
    if isinstance(value, (list, tuple)):
        vals = list(value)
    else:
        vals = [value]
    return Query.equal(field, vals)


def list_documents(collection_id: str, queries: Optional[List[Query]] = None) -> List[Dict[str, Any]]:
    """Retrieve documents from a collection using the Appwrite SDK.

    Args:
        collection_id: The collection identifier.
        queries: A list of ``Query`` objects.  If ``None``, no filtering is applied.

    Returns:
        A list of document dictionaries.
    """
    db = _ensure_client()
    resp = db.list_documents(
        database_id=DATABASE_ID,
        collection_id=collection_id,
        queries=queries or []
    )
    return resp.get("documents", [])


def create_document(collection_id: str, document_id: Any, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new document using the Appwrite SDK.

    Args:
        collection_id: The collection identifier.
        document_id: The desired document ID or ``ID.unique()`` for an auto ID.
        data: Dictionary of document fields.

    Returns:
        The created document.
    """
    db = _ensure_client()
    return db.create_document(
        database_id=DATABASE_ID,
        collection_id=collection_id,
        document_id=document_id,
        data=data
    )


def update_document(collection_id: str, document_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing document using the Appwrite SDK.

    Args:
        collection_id: The collection identifier.
        document_id: The document identifier.
        data: A dictionary of fields to update.

    Returns:
        The updated document.
    """
    db = _ensure_client()
    return db.update_document(
        database_id=DATABASE_ID,
        collection_id=collection_id,
        document_id=document_id,
        data=data
    )


def generate_id() -> Any:
    """Return a new unique identifier for a document using the SDK."""
    return ID.unique()
