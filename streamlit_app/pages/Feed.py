"""Social feed page for viewing, creating and interacting with posts."""

import streamlit as st

from helpers.auth_utils import require_login
from helpers.appwrite_utils import list_documents
from helpers.bot_utils import (
    create_post,
    create_comment,
    add_like_to_post,
    add_like_to_comment,
    get_comments_for_post,
)
from config import POSTS_COLLECTION_ID


def run_feed_page() -> None:
    """Render the main social feed with posts, likes and comments."""
    # Ensure the user is logged in
    require_login()
    user = st.session_state['user']
    st.title("Social Feed")
    # Provide a button to refresh the feed
    if st.button("Refresh feed"):
        st.rerun()
    # Fetch all posts
    try:
        posts = list_documents(POSTS_COLLECTION_ID)
    except Exception as exc:
        st.error(f"Failed to load posts: {exc}")
        posts = []
    # Sort posts by likes descending then creation time (assuming $createdAt exists)
    posts.sort(key=lambda p: (p.get("likes", 0), p.get("$createdAt", "")), reverse=True)
    # New post form at the top
    st.subheader("Create a new post")
    new_title = st.text_input("Title", key="new_post_title")
    new_content = st.text_area("Content", key="new_post_content")
    if st.button("Publish post"):
        if not new_title or not new_content:
            st.warning("Please fill in both the title and content.")
        else:
            try:
                create_post(new_title, new_content, None, user.get("$id"))
                st.success("Post published!")
            except Exception as exc:
                st.error(f"Error creating post: {exc}")
            st.rerun()
    st.markdown("---")
    # Display posts
    for post in posts:
        post_id = post.get("$id")
        st.markdown(f"### {post.get('title')}")
        st.write(post.get("content"))
        # Display image if available
        img_url = post.get("imageurl")
        if img_url:
            st.image(img_url, use_column_width=True)
        likes = post.get("likes", 0)
        st.write(f"Likes: {likes}")
        # Like button
        if st.button(f"Like post {post_id}", key=f"like_post_{post_id}"):
            try:
                add_like_to_post(post_id, likes)
            except Exception as exc:
                st.error(f"Error liking post: {exc}")
            st.rerun()
        # Comments section
        with st.expander("Comments"):
            try:
                comments = get_comments_for_post(post_id)
            except Exception as exc:
                st.error(f"Failed to load comments: {exc}")
                comments = []
            for comment in comments:
                comment_id = comment.get("$id")
                comment_content = comment.get("content")
                comment_likes = comment.get("likes", 0)
                st.write(f"{comment_content} (likes: {comment_likes})")
                if st.button(
                    f"Like comment {comment_id}",
                    key=f"like_comment_{comment_id}",
                ):
                    try:
                        add_like_to_comment(comment_id, comment_likes)
                    except Exception as exc:
                        st.error(f"Error liking comment: {exc}")
                    st.rerun()
            # Add a new comment
            new_comment = st.text_input("Your comment", key=f"new_comment_{post_id}")
            if st.button(f"Add comment to {post_id}", key=f"add_comment_{post_id}"):
                if not new_comment:
                    st.warning("Please enter a comment.")
                else:
                    try:
                        create_comment(new_comment, post_id, user.get("$id"))
                        st.success("Comment added!")
                    except Exception as exc:
                        st.error(f"Error adding comment: {exc}")
                    st.rerun()
        st.markdown("---")


if __name__ == "__main__":
    run_feed_page()