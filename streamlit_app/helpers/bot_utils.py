"""High‑level domain logic for bots and social interactions.

This module encapsulates the main logic for interacting with the Appwrite
databases and for running bots.  It depends on the low‑level functions in
:mod:`streamlit_app.helpers.appwrite_utils` and the OpenAI helpers in
:mod:`streamlit_app.helpers.openai_utils`.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from helpers.appwrite_utils import (
    q_equal,
    list_documents,
    create_document,
    update_document,
    generate_id,
)
from helpers.openai_utils import (
    generate_post_using_chatgpt,
    generate_comment_using_chatgpt,
    call_openai_image,
)
from config import (
    BOTS_COLLECTION_ID,
    POSTS_COLLECTION_ID,
    USERS_COLLECTION_ID,
    COMMENTS_COLLECTION_ID,
)


def find_important_people() -> List[str]:
    """Return a list of user IDs with a popularity score of 1."""
    docs = list_documents(USERS_COLLECTION_ID, [q_equal("popularityscore", 1)])
    return [doc.get("$id") for doc in docs]


def get_user_posts(user_id: str) -> List[Dict[str, Any]]:
    """Return all posts created by a specific user."""
    return list_documents(POSTS_COLLECTION_ID, [q_equal("userid", user_id)])


def create_post(title: str, content: str, imageurl: Optional[str], user_id: str) -> None:
    """Create a post in the posts collection.

    The content length is truncated to 500 characters as in the JavaScript
    implementation.  Likes are initialised to 0.
    """
    if len(content) > 500:
        content = content[:500]
    data = {
        "title": title,
        "content": content,
        "imageurl": imageurl,
        "likes": 0,
        "userid": user_id,
    }
    # Use generate_id() to obtain a unique document ID across both SDK and REST modes
    create_document(POSTS_COLLECTION_ID, generate_id(), data)


def create_comment(content: str, post_id: str, user_id: str) -> None:
    """Create a comment for a given post.

    Likes are initialised to 0.
    """
    data = {
        "content": content,
        "postid": post_id,
        "userid": user_id,
        "likes": 0,
    }
    create_document(COMMENTS_COLLECTION_ID, generate_id(), data)


def add_like_to_post(post_id: str, current_likes: int) -> None:
    """Increment the like count on a post."""
    update_document(POSTS_COLLECTION_ID, post_id, {"likes": current_likes + 1})


def add_like_to_comment(comment_id: str, current_likes: int) -> None:
    """Increment the like count on a comment."""
    update_document(COMMENTS_COLLECTION_ID, comment_id, {"likes": current_likes + 1})


def get_comments_for_post(post_id: str) -> List[Dict[str, Any]]:
    """Return all comments belonging to a particular post."""
    return list_documents(COMMENTS_COLLECTION_ID, [q_equal("postid", post_id)])


def run_post_bot(bot: Dict[str, Any], important_people: List[str], logs: List[str]) -> None:
    """Execute a single iteration of a post bot.

    Chooses a random important user, selects one of their posts, and posts a new
    generated message (with optional image) to the feed.  All noteworthy
    actions are appended to ``logs``.
    """
    tone = bot.get("tone")
    if not important_people:
        logs.append(f"Bot {bot.get('$id')} could not find any important people to post about.")
        return
    target_user = random.choice(important_people)
    posts = get_user_posts(target_user)
    if not posts:
        logs.append(f"Bot {bot.get('$id')} found no posts by important user {target_user}.")
        return
    post = random.choice(posts)
    original_text = f"title: {post.get('title', '')}, content: {post.get('content', '')}"
    generated = generate_post_using_chatgpt(original_text, tone)
    if not generated:
        logs.append(f"Bot {bot.get('$id')} could not generate a post via ChatGPT.")
        return
    title = generated.get("title", "")
    content = generated.get("content", "")
    # Generate an image using OpenAI if configured
    image_file_id = None
    if content:
        openai_image_url = call_openai_image(content)
        if openai_image_url:
            try:
                from helpers.appwrite_utils import upload_image_from_url
                image_file_id = upload_image_from_url(openai_image_url)
            except Exception as exc:
                logs.append(f"Bot {bot.get('$id')} failed to upload image: {exc}")

    create_post(title, content, image_file_id, bot.get("$id"))
    logs.append(f"Bot {bot.get('$id')} posted a new message titled '{title}'.")


def run_comment_bot(bot: Dict[str, Any], important_people: List[str], logs: List[str]) -> None:
    """Execute a single iteration of a comment bot."""
    tone = bot.get("tone")
    if not important_people:
        logs.append(f"Bot {bot.get('$id')} could not find any important people to comment on.")
        return
    target_user = random.choice(important_people)
    posts = get_user_posts(target_user)
    if not posts:
        logs.append(f"Bot {bot.get('$id')} found no posts by important user {target_user} to comment on.")
        return
    post = random.choice(posts)
    content_dict = generate_comment_using_chatgpt(f"content: {post.get('content', '')}", tone)
    if not content_dict or not content_dict.get("comment"):
        logs.append(f"Bot {bot.get('$id')} could not generate a comment via ChatGPT.")
        return
    create_comment(content_dict["comment"], post.get("$id"), bot.get("$id"))
    logs.append(f"Bot {bot.get('$id')} commented on post {post.get('$id')}.")


def run_reaction_bot(bot: Dict[str, Any], important_people: List[str], bot_ids: List[str], logs: List[str]) -> None:
    """Execute a single iteration of a reaction bot.

    Likes a random important user’s post and then likes any comments on that post
    made by bots or important users.
    """
    if not important_people:
        logs.append(f"Bot {bot.get('$id')} could not find any important people to react to.")
        return
    target_user = random.choice(important_people)
    posts = get_user_posts(target_user)
    if not posts:
        logs.append(f"Bot {bot.get('$id')} found no posts by important user {target_user} to react to.")
        return
    post = random.choice(posts)
    post_id = post.get("$id")
    current_likes = post.get("likes", 0)
    add_like_to_post(post_id, current_likes)
    logs.append(f"Bot {bot.get('$id')} liked post {post_id}.")
    # Like comments by bots or important people
    comments = get_comments_for_post(post_id)
    for comment in comments:
        comment_user_id = comment.get("userid")
        if comment_user_id in bot_ids or comment_user_id in important_people:
            add_like_to_comment(comment.get("$id"), comment.get("likes", 0))
            logs.append(
                f"Bot {bot.get('$id')} liked comment {comment.get('$id')} by user {comment_user_id}."
            )


def run_bots_once(logs: List[str]) -> None:
    """Run one iteration for every bot based on its type and activity level.

    This function fetches fresh bot and important people lists on each call to
    reflect the current database state.
    """
    # Fetch all bots
    bot_docs = list_documents(BOTS_COLLECTION_ID)
    if not bot_docs:
        logs.append("No bots found in the database.")
        return
    # Determine the list of important people
    important_people = find_important_people()
    # Precompute a list of bot IDs for reaction bots to identify comments by bots
    bot_ids = [b.get("$id") for b in bot_docs]
    for bot in bot_docs:
        bottype = bot.get("bottype")
        activity = bot.get("activitylevel", 0)
        # Ensure activity is an integer >= 0
        try:
            activity_count = int(activity)
        except (TypeError, ValueError):
            activity_count = 0
        for _ in range(activity_count):
            if bottype == "post":
                run_post_bot(bot, important_people, logs)
            elif bottype == "comment":
                run_comment_bot(bot, important_people, logs)
            elif bottype == "reaction":
                run_reaction_bot(bot, important_people, bot_ids, logs)
            else:
                logs.append(f"Bot {bot.get('$id')} has unknown type '{bottype}'.")
