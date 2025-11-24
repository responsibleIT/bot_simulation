"""Helper functions for interacting with the OpenAI API.

This module wraps the HTTP calls to OpenAI's ChatGPT and DALL·E endpoints.
It uses the API key defined in :mod:`streamlit_app.config`.  If no API key
is present, the functions return ``None`` to indicate that no generation
should occur.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import requests

from config import OPENAI_API_KEY


def call_openai_chat(
    messages: List[Dict[str, str]],
    functions: Optional[List[Dict[str, Any]]] = None,
    function_call: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    """Call the OpenAI chat completions API and return function call arguments.

    Args:
        messages: List of message dicts with ``role`` and ``content`` keys.
        functions: Optional list of function specifications as accepted by
            OpenAI.  See the original JavaScript for examples.
        function_call: Optional directive specifying which function to call.

    Returns:
        Parsed JSON arguments from the function call if present, else ``None``.
        If no API key is configured, returns ``None``.
    """
    if not OPENAI_API_KEY:
        return None
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": "gpt-4o",
        "messages": messages,
        "max_tokens": 400,
    }
    if functions:
        payload["functions"] = functions
    if function_call:
        payload["function_call"] = function_call
    try:
        response = requests.post(url, headers=headers, json=payload)
    except requests.exceptions.RequestException:
        return None
    if not response.ok:
        return None
    result = response.json()
    try:
        message = result["choices"][0]["message"]
        func_call = message.get("function_call", {})
        arguments = func_call.get("arguments", "{}")
        return json.loads(arguments)
    except (IndexError, KeyError, json.JSONDecodeError):
        return None


def call_openai_image(prompt: str) -> Optional[str]:
    """Generate an image using OpenAI’s DALL·E API and return its URL.

    Returns ``None`` if no API key is configured or if generation fails.
    """
    if not OPENAI_API_KEY:
        return None
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "dall-e-3",
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
    except requests.exceptions.RequestException:
        return None
    if not response.ok:
        return None
    data = response.json().get("data", [])
    if not data:
        return None
    return data[0].get("url")


def generate_post_using_chatgpt(original_post: str, bot_tone: str) -> Optional[Dict[str, str]]:
    """Generate a new post title and content using ChatGPT.

    Returns a dictionary with ``title`` and ``content`` keys, or ``None`` if
    generation is disabled or fails.
    """
    functions = [
        {
            "name": "generate_post",
            "description": (
                f"Generate a new post based on the original post: {original_post}. Write the post like someone would on social media. Make it seem it's written by a human and not AI."
                f"The new post should have a specific tone: {bot_tone}. Also make sure that this tone is reflected in both the title and content of the post in a human on social media way."
                "The new post should be generated using the ChatGPT model."
            ),
            "parameters": {
                "type": "object",
                "required": ["title", "content"],
                "properties": {
                    "title": {
                        "type": "string",
                        "description": (
                            "The title of the new post, related to the original post, "
                            "but with a specific tone"
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": (
                            "The content of the post, related to the original post, "
                            "but with a specific tone"
                        ),
                    },
                },
                "additionalProperties": False,
            },
        }
    ]
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Use the supplied tools to assist the user in a human way."},
        {
            "role": "user",
            "content": (
                f"Hey, can you generate a title and content for a social media post "
                f"for me related this original post: {original_post}. Post something similar "
                f"being positive, neutral or critical based on the following tone value: {bot_tone}"
            ),
        },
    ]
    return call_openai_chat(messages, functions, {"name": "generate_post"})


def generate_comment_using_chatgpt(original_post: str, bot_tone: str) -> Optional[Dict[str, str]]:
    """Generate a new comment using ChatGPT.

    Returns a dictionary with a single key ``comment`` or ``None``.
    """
    functions = [
        {
            "name": "generate_comment",
            "description": (
                f"Generate a new comment based on the original post: {original_post}. Write the comment like someone would on social media. Make it seem it's written by a human and not AI."
                f"The new comment should have a specific tone: {bot_tone}. Also make sure that this tone is reflected in the comment in a human on social media way."
                "The new comment should be generated using the ChatGPT model."
            ),
            "parameters": {
                "type": "object",
                "required": ["comment"],
                "properties": {
                    "comment": {
                        "type": "string",
                        "description": (
                            "The content of the comment, related to the original post, but with a specific tone"
                        ),
                    },
                },
                "additionalProperties": False,
            },
        }
    ]
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Use the supplied tools to assist the user."},
        {
            "role": "user",
            "content": (
                f"Hey, can you generate a comment for me related this original post: {original_post}. "
                f"Post something similar being positive, neutral or critical based on the following tone value: {bot_tone}"
            ),
        },
    ]
    return call_openai_chat(messages, functions, {"name": "generate_comment"})
