"""Instructor analysis page for running bots and viewing logs."""

import streamlit as st

from helpers.auth_utils import require_login, is_admin
from helpers.bot_utils import run_bots_once, run_bots_once_callback
from typing import Dict, List
import pandas as pd
from helpers.appwrite_utils import list_documents
from config import POSTS_COLLECTION_ID, COMMENTS_COLLECTION_ID


def run_analysis_page() -> None:
    """Render the admin analysis panel."""
    require_login()
    if not is_admin():
        st.error("You do not have permission to view this page.")
        return
    st.title("Bot Analysis (Instructor Only)")
    st.write(
        "Press the button below to run all bots. During execution, a live line chart will update "
        "after each bot cycle showing the popularity (total likes) per user. Logs of bot actions "
        "will appear below the chart."
    )
    # Prepare a log container in session state
    logs: List[str] = st.session_state.setdefault("bot_logs", [])
    # Maintain a history of popularity snapshots for the current run
    if "run_popularity_history" not in st.session_state:
        st.session_state["run_popularity_history"] = []  # list of {step: int, totals: dict}

    # Chart placeholder (sticky at top)
    chart_placeholder = st.empty()
    st.subheader("Execution log")
    log_container = st.container()

    # Helper to compute popularity snapshot
    def compute_popularity_snapshot() -> Dict[str, int]:
        totals: Dict[str, int] = {}
        # Sum likes on posts
        posts = list_documents(POSTS_COLLECTION_ID)
        for p in posts:
            uid = p.get("userid")
            if not uid:
                continue
            likes = p.get("likes", 0)
            totals[uid] = totals.get(uid, 0) + likes
        # Sum likes on comments
        comments = list_documents(COMMENTS_COLLECTION_ID)
        for c in comments:
            uid = c.get("userid")
            if not uid:
                continue
            likes = c.get("likes", 0)
            totals[uid] = totals.get(uid, 0) + likes
        return totals

    # If the run button is pressed
    if st.button("Run bots"):
        # Clear previous logs and history for this run
        logs.clear()
        st.session_state["run_popularity_history"] = []

        # Callback to append logs and update log display
        def append_log(message: str) -> None:
            logs.append(message)
            # Keep log display updated with most recent entries
            log_container.markdown("\n".join(logs[-100:]) if logs else "No bot activity yet.")

        # Callback to compute snapshot and update chart
        def snapshot_callback() -> None:
            totals = compute_popularity_snapshot()
            step = len(st.session_state["run_popularity_history"])
            st.session_state["run_popularity_history"].append({"step": step, "totals": totals})
            # Prepare DataFrame for line chart
            rows = []
            for entry in st.session_state["run_popularity_history"]:
                s = entry["step"]
                for uid, likes in entry["totals"].items():
                    rows.append({"step": s, "user_id": uid, "total_likes": likes})
            if rows:
                df = pd.DataFrame(rows)
                pivot = df.pivot(index="step", columns="user_id", values="total_likes").fillna(0)
                chart_placeholder.line_chart(pivot)

        try:
            # Run bots with live callbacks
            run_bots_once_callback(append_log, snapshot_callback)
            st.success("Bots executed. See logs below.")
        except Exception as exc:
            st.error(f"Error running bots: {exc}")
    else:
        # Show existing logs and last chart when not running
        if logs:
            log_container.markdown("\n".join(logs[-100:]))
        else:
            log_container.write("No bot activity yet.")
        # If there is a previous run's history, display the last snapshot as line chart
        if st.session_state.get("run_popularity_history"):
            rows = []
            for entry in st.session_state["run_popularity_history"]:
                s = entry["step"]
                for uid, likes in entry["totals"].items():
                    rows.append({"step": s, "user_id": uid, "total_likes": likes})
            if rows:
                df = pd.DataFrame(rows)
                pivot = df.pivot(index="step", columns="user_id", values="total_likes").fillna(0)
                chart_placeholder.line_chart(pivot)


if __name__ == "__main__":
    run_analysis_page()