"""Token counting for messages we are ABOUT to send.

Uses tiktoken with OpenAI's documented per-message overhead so the two
sublab_medium runs (compressed vs. not) are counted the same way and are
comparable to each other, even if the model itself is newer than tiktoken's
built-in table.
"""
import tiktoken


def _get_encoding(model: str):
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_message_tokens(messages, model: str) -> int:
    enc = _get_encoding(model)
    tokens_per_message = 3
    tokens_per_name = 1
    num_tokens = 0
    for msg in messages:
        num_tokens += tokens_per_message
        for key, value in msg.items():
            num_tokens += len(enc.encode(str(value)))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3
    return num_tokens
