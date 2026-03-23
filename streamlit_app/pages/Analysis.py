"""Instructor analysis page for running bots and viewing logs."""

import streamlit as st
import plotly.graph_objects as go

from helpers.auth_utils import require_login, is_admin
from helpers.bot_utils import run_bots_once, run_bots_once_callback
from typing import Dict, List
from helpers.appwrite_utils import list_documents
from config import POSTS_COLLECTION_ID, COMMENTS_COLLECTION_ID, USERS_COLLECTION_ID


# Distinct, high-contrast colour palette for chart lines
_CHART_COLORS = [
    "#FFD700",  # gold
    "#00BFFF",  # deep sky blue
    "#FF6347",  # tomato
    "#32CD32",  # lime green
    "#FF69B4",  # hot pink
    "#FFA500",  # orange
    "#7B68EE",  # medium slate blue
    "#00CED1",  # dark turquoise
    "#FF4500",  # orange-red
    "#ADFF2F",  # green-yellow
]


def _build_user_label_map() -> Dict[str, str]:
    """Return a mapping from user $id to a short, human-readable label.

    Uses the email prefix (everything before '@') when available, otherwise
    falls back to the first 8 characters of the ID.
    """
    label_map: Dict[str, str] = {}
    try:
        users = list_documents(USERS_COLLECTION_ID)
        for u in users:
            uid = u.get("$id", "")
            email = u.get("email", "")
            if email and "@" in email:
                label_map[uid] = email.split("@")[0]
            elif email:
                label_map[uid] = email
            else:
                label_map[uid] = uid[:8]
    except Exception:
        pass
    return label_map


def _render_plotly_chart(history: List[dict], placeholder) -> None:
    """Build a Plotly line chart from the popularity history and render it."""
    if not history:
        return

    label_map = _build_user_label_map()

    # Collect all user IDs that appear in history
    all_uids: List[str] = []
    seen = set()
    for entry in history:
        for uid in entry["totals"]:
            if uid not in seen:
                seen.add(uid)
                all_uids.append(uid)

    fig = go.Figure()
    for idx, uid in enumerate(all_uids):
        color = _CHART_COLORS[idx % len(_CHART_COLORS)]
        label = label_map.get(uid, uid[:8])
        xs = [e["step"] for e in history]
        ys = [e["totals"].get(uid, 0) for e in history]

        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="lines+markers",
            name=label,
            line=dict(width=3, color=color),
            marker=dict(size=6, color=color),
        ))

        # Annotate the last data point directly on the chart
        if ys:
            fig.add_annotation(
                x=xs[-1], y=ys[-1],
                text=f"  {label}",
                showarrow=False,
                font=dict(size=13, color=color, family="Arial Black"),
                xanchor="left",
            )

    fig.update_layout(
        xaxis_title="Cycle",
        yaxis_title="Total Likes",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=14),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=40, r=120, t=30, b=80),
        height=450,
        template="plotly_dark",
    )

    placeholder.plotly_chart(fig, use_container_width=True)


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
            _render_plotly_chart(st.session_state["run_popularity_history"], chart_placeholder)

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
            _render_plotly_chart(st.session_state["run_popularity_history"], chart_placeholder)


if __name__ == "__main__":
    run_analysis_page()