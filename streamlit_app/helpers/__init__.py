"""Helper modules for the Bot Workshop app.

This package provides reusable functions for interacting with Appwrite,
generating content with OpenAI, managing bots, and authentication helpers.
"""

from .appwrite_utils import q_equal, list_documents, create_document, update_document
from .openai_utils import generate_post_using_chatgpt, generate_comment_using_chatgpt, call_openai_image
from .bot_utils import (
    find_important_people,
    get_user_posts,
    create_post,
    create_comment,
    add_like_to_post,
    add_like_to_comment,
    get_comments_for_post,
    run_post_bot,
    run_comment_bot,
    run_reaction_bot,
    run_bots_once,
)
from .auth_utils import require_login, is_admin

__all__ = [
    "q_equal",
    "list_documents",
    "create_document",
    "update_document",
    "generate_post_using_chatgpt",
    "generate_comment_using_chatgpt",
    "call_openai_image",
    "find_important_people",
    "get_user_posts",
    "create_post",
    "create_comment",
    "add_like_to_post",
    "add_like_to_comment",
    "get_comments_for_post",
    "run_post_bot",
    "run_comment_bot",
    "run_reaction_bot",
    "run_bots_once",
    "require_login",
    "is_admin",
]