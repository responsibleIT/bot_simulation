"""Interactive network graph showing who interacts with whom.

Nodes represent users (humans and bots).  Edges are drawn when one user
likes or comments on another user's post.  Edge thickness reflects the
number of interactions.  Bot nodes are coloured red; human nodes are blue.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Dict, List, Set, Tuple

import plotly.graph_objects as go
import streamlit as st

from helpers.auth_utils import require_login, is_admin
from helpers.appwrite_utils import list_documents
from helpers.bot_utils import get_all_bot_ids
from config import (
    POSTS_COLLECTION_ID,
    COMMENTS_COLLECTION_ID,
    USERS_COLLECTION_ID,
)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _build_interaction_edges() -> Tuple[
    Dict[str, Dict[str, int]],  # edges  source -> target -> weight
    Set[str],                    # all user ids
]:
    """Scan posts and comments to build a weighted directed edge map.

    An edge ``(A, B)`` with weight *w* means user A interacted with user B's
    content *w* times (via commenting on B's post).  Likes are counted once
    per post as an implicit interaction from every liker-bot to the post author.
    """
    edges: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    all_users: Set[str] = set()

    # Map post_id -> author_id
    posts = list_documents(POSTS_COLLECTION_ID)
    post_author: Dict[str, str] = {}
    for p in posts:
        pid = p.get("$id")
        uid = p.get("userid")
        if pid and uid:
            post_author[pid] = uid
            all_users.add(uid)

    # Comments: commenter -> post author
    comments = list_documents(COMMENTS_COLLECTION_ID)
    for c in comments:
        commenter = c.get("userid")
        post_id = c.get("postid")
        if not commenter or not post_id:
            continue
        target = post_author.get(post_id)
        if target and target != commenter:
            edges[commenter][target] += 1
            all_users.add(commenter)

    # Also add users from the users table so isolated nodes appear
    users = list_documents(USERS_COLLECTION_ID)
    for u in users:
        uid = u.get("$id")
        if uid:
            all_users.add(uid)

    return edges, all_users


def _build_user_label_map() -> Dict[str, str]:
    """Map user $id -> short readable label (email prefix or truncated id)."""
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


# ---------------------------------------------------------------------------
# Layout helper — simple force-directed (Fruchterman-Reingold-ish)
# ---------------------------------------------------------------------------

def _layout_nodes(
    nodes: List[str],
    edges: Dict[str, Dict[str, int]],
    iterations: int = 80,
) -> Dict[str, Tuple[float, float]]:
    """Return {node_id: (x, y)} positions using a spring layout."""
    rng = random.Random(42)
    pos: Dict[str, Tuple[float, float]] = {
        n: (rng.uniform(-1, 1), rng.uniform(-1, 1)) for n in nodes
    }
    if len(nodes) <= 1:
        return pos

    k = 1.0 / math.sqrt(len(nodes))  # ideal spring length

    for _ in range(iterations):
        disp: Dict[str, Tuple[float, float]] = {n: (0.0, 0.0) for n in nodes}

        # Repulsive forces between every pair
        node_list = list(nodes)
        for i in range(len(node_list)):
            for j in range(i + 1, len(node_list)):
                ni, nj = node_list[i], node_list[j]
                dx = pos[ni][0] - pos[nj][0]
                dy = pos[ni][1] - pos[nj][1]
                dist = max(math.sqrt(dx * dx + dy * dy), 0.01)
                force = k * k / dist
                fx, fy = force * dx / dist, force * dy / dist
                disp[ni] = (disp[ni][0] + fx, disp[ni][1] + fy)
                disp[nj] = (disp[nj][0] - fx, disp[nj][1] - fy)

        # Attractive forces along edges
        for src, targets in edges.items():
            if src not in pos:
                continue
            for tgt, w in targets.items():
                if tgt not in pos:
                    continue
                dx = pos[src][0] - pos[tgt][0]
                dy = pos[src][1] - pos[tgt][1]
                dist = max(math.sqrt(dx * dx + dy * dy), 0.01)
                force = dist * dist / k * (1 + w * 0.3)
                fx, fy = force * dx / dist, force * dy / dist
                disp[src] = (disp[src][0] - fx, disp[src][1] - fy)
                disp[tgt] = (disp[tgt][0] + fx, disp[tgt][1] + fy)

        # Apply displacement with cooling
        temp = max(0.1, 1.0 - _ / iterations)
        for n in nodes:
            dx, dy = disp[n]
            mag = max(math.sqrt(dx * dx + dy * dy), 0.01)
            pos[n] = (
                pos[n][0] + dx / mag * min(mag, temp),
                pos[n][1] + dy / mag * min(mag, temp),
            )

    return pos


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def run_network_graph_page() -> None:
    """Render the network graph page."""
    require_login()

    st.title("🌐 Interaction Network Graph")
    st.write(
        "This graph shows **who interacts with whom**.  Each node is a user; "
        "an arrow from A → B means A commented on B's post.  "
        "Thicker lines = more interactions.  "
        "**Red** nodes are bots, **blue** nodes are humans."
    )

    try:
        bot_ids = set(get_all_bot_ids())
    except Exception:
        bot_ids = set()

    label_map = _build_user_label_map()
    edges, all_users = _build_interaction_edges()

    if not all_users:
        st.info("No users or interactions found yet. Run the bots first!")
        return

    node_list = sorted(all_users)
    pos = _layout_nodes(node_list, edges)

    fig = go.Figure()

    # --- Draw edges ----------------------------------------------------------
    for src, targets in edges.items():
        for tgt, w in targets.items():
            if src not in pos or tgt not in pos:
                continue
            x0, y0 = pos[src]
            x1, y1 = pos[tgt]
            fig.add_trace(go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode="lines",
                line=dict(width=max(1, min(w * 1.5, 8)), color="rgba(180,180,180,0.45)"),
                hoverinfo="none",
                showlegend=False,
            ))

    # --- Draw nodes ----------------------------------------------------------
    # Separate bots and humans for distinct legend entries
    for is_bot, color, symbol, group_label in [
        (True, "#ff4b4b", "diamond", "Bot"),
        (False, "#636efa", "circle", "Human"),
    ]:
        xs, ys, texts, hovers = [], [], [], []
        for n in node_list:
            if (n in bot_ids) != is_bot:
                continue
            x, y = pos[n]
            xs.append(x)
            ys.append(y)
            label = label_map.get(n, n[:8])
            texts.append(label)
            # Count interactions
            out_count = sum(edges.get(n, {}).values())
            in_count = sum(
                targets.get(n, 0) for targets in edges.values()
            )
            hovers.append(
                f"<b>{label}</b><br>"
                f"{'🤖 Bot' if is_bot else '👤 Human'}<br>"
                f"Comments made: {out_count}<br>"
                f"Comments received: {in_count}"
            )
        if not xs:
            continue
        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="markers+text",
            marker=dict(size=18, color=color, symbol=symbol, line=dict(width=1, color="white")),
            text=texts,
            textposition="top center",
            textfont=dict(size=11, color="white"),
            hovertext=hovers,
            hoverinfo="text",
            name=group_label,
        ))

    fig.update_layout(
        showlegend=True,
        legend=dict(font=dict(size=14)),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=600,
        margin=dict(l=20, r=20, t=30, b=20),
        template="plotly_dark",
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Stats table ---------------------------------------------------------
    st.subheader("Interaction summary")
    rows = []
    for n in node_list:
        label = label_map.get(n, n[:8])
        out_count = sum(edges.get(n, {}).values())
        in_count = sum(targets.get(n, 0) for targets in edges.values())
        rows.append({
            "User": label,
            "Type": "🤖 Bot" if n in bot_ids else "👤 Human",
            "Comments made": out_count,
            "Comments received": in_count,
        })
    if rows:
        import pandas as pd
        df = pd.DataFrame(rows).sort_values("Comments received", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    run_network_graph_page()
