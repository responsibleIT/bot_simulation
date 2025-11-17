"""Login and registration page for the Bot Workshop.

This Streamlit page allows users to sign in with their e‑mail address and
optionally select a popularity score.  If the e‑mail does not exist in the
database it is created; otherwise the existing user document is loaded.
"""

import streamlit as st

from helpers.appwrite_utils import q_equal, list_documents, create_document
from config import USERS_COLLECTION_ID


def run_login_page() -> None:
    """Render the login/registration form and handle user sign‑in."""
    st.title("Welcome to the Bot Workshop")
    st.write(
        "Enter your school e‑mail address to create an account or log in. "
        "You can optionally choose whether you are an 'important' user. Bots will "
        "prefer interacting with important users when generating posts and comments."
    )
    # If already logged in, inform the user
    if 'user' in st.session_state:
        user = st.session_state['user']
        st.info(f"You are already logged in as {user.get('email')}. Use the sidebar to navigate to other pages.")
        return
    email = st.text_input("School e‑mail address")
    popularity = st.selectbox(
        "Popularity score (1 = important, 0 = ordinary)", options=[1, 0], index=1
    )
    if st.button("Log in / Register"):
        if not email:
            st.warning("Please enter an e‑mail address.")
            return
        try:
            users = list_documents(
                USERS_COLLECTION_ID,
                [q_equal("email", email)],
            )
        except Exception as exc:
            st.error(f"Failed to contact Appwrite: {exc}")
            return
        if users:
            user = users[0]
        else:
            # Create a new user document
            data = {
                "email": email,
                "popularityscore": int(popularity),
            }
            try:
                # Use a generated ID for new users to ensure uniqueness across SDK and REST modes
                from helpers.appwrite_utils import generate_id  # imported lazily to avoid circular import
                user = create_document(USERS_COLLECTION_ID, generate_id(), data)
            except Exception as exc:
                st.error(f"Failed to create user: {exc}")
                return
        # Save user in session and reload
        st.session_state['user'] = user
        st.success("Logged in!")
        st.rerun()


# When the module is run directly by Streamlit, execute the page function
if __name__ == "__main__":
    run_login_page()