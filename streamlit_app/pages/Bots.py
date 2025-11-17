"""Bot creation page for the Bot Workshop."""

import streamlit as st

from helpers.auth_utils import require_login
from helpers.appwrite_utils import create_document
from config import BOTS_COLLECTION_ID


def run_bots_page() -> None:
    """Render the bot creation form."""
    require_login()
    st.title("Create a Bot")
    st.write(
        "Configure a bot to simulate posting, commenting or reacting behaviour. "
        "Bots run when an instructor triggers them from the analysis screen."
    )
    bottype = st.selectbox("Bot type", options=["post", "comment", "reaction"])
    activity = st.slider("Activity level (number of actions per run)", min_value=1, max_value=10, value=1)
    tone = st.selectbox(
        "Tone", options=["positive", "neutral", "critical"], index=1
    )
    if st.button("Create bot"):
        data = {
            "bottype": bottype,
            "activitylevel": int(activity),
            "tone": tone,
        }
        try:
            # Import lazily to avoid circular import
            from helpers.appwrite_utils import generate_id
            create_document(BOTS_COLLECTION_ID, generate_id(), data)
            st.success("Bot created!")
        except Exception as exc:
            st.error(f"Failed to create bot: {exc}")


if __name__ == "__main__":
    run_bots_page()