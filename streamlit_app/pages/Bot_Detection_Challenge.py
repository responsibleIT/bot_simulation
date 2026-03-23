"""Bot Detection Challenge — a gamified quiz for students.

Students are shown a shuffled mix of real and bot-generated posts and must
flag which ones they think were made by bots.  After submitting, the page
scores their answers, shows the correct labels, and provides feedback.
"""

from __future__ import annotations

import random
from typing import Dict, List

import streamlit as st

from helpers.auth_utils import require_login
from helpers.appwrite_utils import list_documents
from helpers.bot_utils import get_all_bot_ids
from config import POSTS_COLLECTION_ID, USERS_COLLECTION_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_user_label_map() -> Dict[str, str]:
    """Map user $id -> readable label."""
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


def _load_challenge_posts(n: int = 10) -> List[dict]:
    """Return up to *n* posts (mix of bot and human), shuffled.

    Each dict has keys: $id, title, content, userid, _is_bot (bool).
    """
    bot_ids = set(get_all_bot_ids())
    all_posts = list_documents(POSTS_COLLECTION_ID)

    bot_posts = [p for p in all_posts if p.get("userid") in bot_ids]
    human_posts = [p for p in all_posts if p.get("userid") not in bot_ids]

    # Try to get a balanced sample
    half = max(n // 2, 1)
    sample_bots = random.sample(bot_posts, min(half, len(bot_posts)))
    sample_humans = random.sample(human_posts, min(half, len(human_posts)))

    combined = sample_bots + sample_humans
    random.shuffle(combined)

    # Tag each
    for p in combined:
        p["_is_bot"] = p.get("userid") in bot_ids

    return combined[:n]


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def run_challenge_page() -> None:
    """Render the Bot Detection Challenge page."""
    require_login()
    st.title("🕵️ Bot Detection Challenge")
    st.write(
        "Can you tell which posts were written by bots? "
        "Read each post below and check the box if you think it was **bot-generated**. "
        "When you're ready, press **Submit** to see your score!"
    )

    # ---- Load / reset challenge posts -----
    if "challenge_posts" not in st.session_state or st.button("🔄 New challenge"):
        try:
            st.session_state["challenge_posts"] = _load_challenge_posts(10)
        except Exception as exc:
            st.error(f"Failed to load posts: {exc}")
            return
        st.session_state.pop("challenge_submitted", None)
        st.rerun()

    posts: List[dict] = st.session_state.get("challenge_posts", [])
    if not posts:
        st.info("No posts found. Create some posts and run the bots first!")
        return

    label_map = _build_user_label_map()

    # ---- Quiz form -----
    submitted = st.session_state.get("challenge_submitted", False)
    guesses: Dict[str, bool] = {}

    st.markdown("---")
    for idx, post in enumerate(posts):
        pid = post.get("$id", str(idx))
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"**Post {idx + 1}: {post.get('title', 'Untitled')}**")
            st.caption(post.get("content", "")[:300])
        with col2:
            if submitted:
                # Show locked checkbox after submission
                guesses[pid] = st.checkbox(
                    "Bot?",
                    key=f"challenge_{pid}",
                    disabled=True,
                )
            else:
                guesses[pid] = st.checkbox("Bot?", key=f"challenge_{pid}")

    st.markdown("---")

    # ---- Submit & score -----
    if not submitted:
        if st.button("✅ Submit answers", type="primary"):
            st.session_state["challenge_submitted"] = True
            st.rerun()
    else:
        # Score
        correct = 0
        total = len(posts)
        results_rows = []
        for idx, post in enumerate(posts):
            pid = post.get("$id", str(idx))
            is_bot = post.get("_is_bot", False)
            guessed_bot = guesses.get(pid, False)
            hit = guessed_bot == is_bot
            if hit:
                correct += 1
            author = label_map.get(post.get("userid", ""), post.get("userid", "?")[:8])
            results_rows.append({
                "#": idx + 1,
                "Title": post.get("title", "")[:40],
                "Your answer": "🤖 Bot" if guessed_bot else "👤 Human",
                "Actual": "🤖 Bot" if is_bot else "👤 Human",
                "Author": author,
                "Result": "✅" if hit else "❌",
            })

        pct = int(correct / total * 100) if total else 0

        # Headline score
        if pct >= 80:
            st.success(f"🎉 Great job! You scored **{correct}/{total}** ({pct}%)")
        elif pct >= 50:
            st.warning(f"🤔 Not bad — **{correct}/{total}** ({pct}%). Can you do better?")
        else:
            st.error(f"😬 Only **{correct}/{total}** ({pct}%). Bots are tricky!")

        # Detailed results table
        import pandas as pd
        df = pd.DataFrame(results_rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Educational tips
        with st.expander("💡 Tips for spotting bots"):
            st.markdown("""
- **Generic language**: bot posts often use generic, overly polished phrases.
- **Repetitive themes**: bots tend to riff on the same topic repeatedly.
- **No personal voice**: human posts often have typos, opinions, and unique style.
- **Suspicious timing**: in real platforms, bots post at regular intervals.
- **Engagement patterns**: bots may only comment on popular users' content.
""")


if __name__ == "__main__":
    run_challenge_page()
