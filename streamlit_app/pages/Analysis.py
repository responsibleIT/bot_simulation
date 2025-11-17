"""Instructor analysis page for running bots and viewing logs."""

import streamlit as st

from helpers.auth_utils import require_login, is_admin
from helpers.bot_utils import run_bots_once


def run_analysis_page() -> None:
    """Render the admin analysis panel."""
    require_login()
    if not is_admin():
        st.error("You do not have permission to view this page.")
        return
    st.title("Bot Analysis (Instructor Only)")
    st.write(
        "Press the button below to run all bots once. Logs of their actions will "
        "appear in the panel. Refresh the page to see new database state."
    )
    # Prepare a log container in session state
    logs = st.session_state.setdefault("bot_logs", [])
    if st.button("Run bots"):
        try:
            run_bots_once(logs)
            st.success("Bots executed. See logs below.")
        except Exception as exc:
            st.error(f"Error running bots: {exc}")
    # Show logs
    st.subheader("Execution log")
    if logs:
        for entry in reversed(logs[-100:]):  # show the most recent 100 entries
            st.write(entry)
    else:
        st.write("No bot activity yet.")


if __name__ == "__main__":
    run_analysis_page()