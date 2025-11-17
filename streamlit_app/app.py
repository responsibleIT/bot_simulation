"""Entry point for the multi‑page Bot Workshop Streamlit application.

This page serves as the home screen for the app.  It displays a welcome
message and basic instructions for navigating the app.  The actual
functionality is implemented in the pages contained in the ``pages`` directory.
"""

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="Bot Workshop", page_icon="🤖")
    st.title("Bot Workshop")
    st.write(
        "Welcome to the Bot Workshop! Use the navigation menu in the sidebar "
        "to log in, view the social feed, create bots, or (if you are an instructor) "
        "run bots and view their activity logs."
    )
    if 'user' in st.session_state:
        user = st.session_state['user']
        st.info(f"Logged in as {user.get('email')}. Navigate to the Feed, Bots or Analysis pages using the sidebar.")
    else:
        st.info("Please select the Login page from the sidebar to sign in or register.")


if __name__ == "__main__":
    main()