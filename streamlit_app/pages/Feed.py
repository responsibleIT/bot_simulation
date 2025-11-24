"""Social feed page for viewing, creating and interacting with posts."""

import streamlit as st

from helpers.auth_utils import require_login
from helpers.bot_utils import (
    create_post,
    create_comment,
    add_like_to_post,
    add_like_to_comment,
    get_comments_for_post,
)
from helpers.appwrite_utils import (
    list_documents,
    # …whatever else you already import …
    get_image_bytes,
    upload_image_file,
)
from config import POSTS_COLLECTION_ID
import hashlib

def user_color(user_id: str) -> str:
    """Generate a deterministic color hex based on the user_id."""
    colors = [
        "#e57373", "#64b5f6", "#81c784", "#ffb74d",
        "#ba68c8", "#4dd0e1", "#ffd54f", "#90a4ae",
    ]
    h = int(hashlib.sha256(user_id.encode("utf-8")).hexdigest(), 16)
    return colors[h % len(colors)]


def user_badge(user_id: str) -> str:
    """Return small HTML badge with colored circle + userid."""
    color = user_color(user_id)
    return f"""
    <span style="display:inline-flex;align-items:center;gap:6px;font-size:0.8rem;color:#aaa;">
      <span style="width:12px;height:12px;border-radius:50%;background:{color};display:inline-block;"></span>
      <span>posted by: <code>{user_id}</code></span>
    </span>
    """

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
    new_title = st.text_input("Title", key="new_post_title", placeholder="Write the title here")
    new_content = st.text_area("Content", key="new_post_content", placeholder="Write the content here")
    uploaded_image = st.file_uploader(
        "Optional image",
        type=["png", "jpg", "jpeg", "gif"],
        key="new_post_image",
    )

    if st.button("Publish post", key="publish_post_button"):
        user = st.session_state.get("user")
        if not user:
            st.warning("You must be logged in to post.")
        elif not new_title or not new_content:
            st.warning("Please fill in both the title and content.")
        else:
            image_file_id = None
            if uploaded_image is not None:
                try:
                    image_file_id = upload_image_file(
                        uploaded_image.name,
                        uploaded_image.getvalue(),
                    )
                except Exception as exc:
                    st.error(f"Failed to upload image: {exc}")
            create_post(new_title, new_content, image_file_id, user.get("$id"))
            st.success("Post published!")
            st.rerun()
    st.markdown("---")
    # Display posts
    for post in posts:
        post_id = post.get("$id")
        st.markdown(f"### {post.get('title')}")
        st.write(post.get("content"))
        post_user_id = post.get("userid", "unknown")
        st.markdown(user_badge(post_user_id), unsafe_allow_html=True)
        # Display image if available
        image_file_id = post.get("imageurl")
        if image_file_id:
            try:
                img_bytes = get_image_bytes(image_file_id)
                st.image(img_bytes, use_column_width=True)
            except Exception as exc:
                st.error(f"Could not load image: {exc}")
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
                comment_user_id = comment.get("userid", "unknown")

                st.markdown(
                    user_badge(comment_user_id),
                    unsafe_allow_html=True,
                )
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
            new_comment = st.text_input("Your comment", key=f"new_comment_{post_id}", placeholder="Write your comment here")
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