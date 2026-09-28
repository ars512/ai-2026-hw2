"""Small shared wrapper around the OpenAI chat completions API.

Kept deliberately thin: every sublab needs (a) a JSON-only call, (b) a
free-text call, and (c) the actual token usage the API reports for that
call. Nothing here decides what to send - that is each sublab's job.
"""
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

if sys.platform == "win32":
    # Windows consoles default to a legacy codepage (e.g. cp1251) that
    # cannot print Kazakh-specific characters; UTF-8 output is otherwise
    # never lossy, so reconfigure it unconditionally.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

load_dotenv(REPO_ROOT / ".env")

DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
BASE_URL = os.environ.get("OPENAI_BASE_URL")  # set to point the same SDK at an OpenAI-compatible provider

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=BASE_URL) if BASE_URL else OpenAI()
    return _client


def _usage_dict(resp) -> dict:
    u = resp.usage
    return {
        "prompt_tokens": u.prompt_tokens,
        "completion_tokens": u.completion_tokens,
        "total_tokens": u.total_tokens,
    }


def chat_raw(messages, model: str = None, temperature: float = 0.3, json_mode: bool = False):
    """Send a full, already-assembled message list (including system) as-is.

    Returns (raw_text, usage_dict). This is the primitive every other helper
    here builds on - it sends exactly the list it is given, nothing more.

    Retries on 429 (rate limit) with a short backoff: the free-tier providers
    this can point at have small per-minute token budgets, and a burst of
    calls from one script run routinely trips them for under a second.
    """
    client = get_client()
    model = model or DEFAULT_MODEL
    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    max_attempts = 8
    for attempt in range(max_attempts):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                **kwargs,
            )
            break
        except RateLimitError:
            if attempt == max_attempts - 1:
                raise
            time.sleep(min(2 ** attempt, 30))
    raw = resp.choices[0].message.content
    return raw, _usage_dict(resp)


def chat_json(system: str, messages, model: str = None, temperature: float = 0):
    """Call the model and expect a single JSON object back.

    `messages` is either a user string (single turn) or a list of
    {"role", "content"} dicts that follow the system message.
    Returns (parsed_dict_or_None, raw_text, usage_dict).
    """
    if isinstance(messages, str):
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": messages}]
    else:
        msgs = [{"role": "system", "content": system}] + list(messages)
    raw, usage = chat_raw(msgs, model=model, temperature=temperature, json_mode=True)
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        parsed = None
    return parsed, raw, usage


def chat_text(system: str, messages, model: str = None, temperature: float = 0.3):
    """Call the model and return free text (no JSON constraint)."""
    if isinstance(messages, str):
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": messages}]
    else:
        msgs = [{"role": "system", "content": system}] + list(messages)
    return chat_raw(msgs, model=model, temperature=temperature, json_mode=False)


def load_json(name: str):
    with open(DATA_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)
