"""Authentication helper functions for Streamlit pages.

This module centralises logic for determining whether a user is logged in and
whether they have administrative privileges.  Pages can import
``require_login`` to ensure a user is present in ``st.session_state``.  The
``is_admin`` function checks if the current user’s e‑mail address is listed
in :data:`streamlit_app.config.ADMIN_EMAILS`.
"""

from __future__ import annotations

import streamlit as st

from config import ADMIN_EMAILS


def require_login() -> bool:
    """Return True if a user is logged in, otherwise show an error and stop.

    If ``st.session_state`` does not contain a ``'user'`` key, this function
    displays an error message prompting the user to log in on the Login page
    and calls ``st.stop()`` to prevent the rest of the page from rendering.

    Returns:
        True if a user is logged in, otherwise does not return.
    """
    if 'user' not in st.session_state:
        st.error("You must log in via the Login page before accessing this page.")
        st.stop()
    return True


def is_admin() -> bool:
    """Return True if the current user has administrative privileges."""
    user = st.session_state.get('user')
    if not user:
        return False
    email = user.get('email')
    return email in ADMIN_EMAILS
