"""Sublab Medium: memory you choose - the `compress` command.

Run:
  python -m sublab_medium.chat_memory
  python -m sublab_medium.chat_memory --interactive
"""
import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.llm import chat_raw, load_json, DEFAULT_MODEL  # noqa: E402
from common.tokens import count_message_tokens  # noqa: E402

COMPRESS_COMMAND = "<compress>"

OFFICE_SYSTEM_PROMPT = (
    "You are the office assistant for a university grant office, chatting "
    "with an applicant. Known records: A-202 is Daniyar Qoshan, Almaty, GPA "
    "2.9, income band 2, documents on file: transcript only (id_card is "
    "missing). Policy: GPA >= 2.67 and income band in {1,2} and both "
    "transcript and id_card on file -> granted, band 1 = 250000 tenge, band "
    "2 = 150000 tenge; missing a required document with everything else ok "
    "-> more_info naming what is missing. Use these facts when they are "
    "relevant, answer conversationally otherwise, and never invent a fact "
    "the applicant has not told you and the records do not show. Keep "
    "replies short. Always reply in English regardless of what language the "
    "applicant writes in. Write amounts in tenge with a comma thousands "
    "separator (e.g. 150,000). When writing an applicant id, use a plain "
    "ASCII hyphen exactly as given (A-202), never a typographic dash."
)

STATE_SCHEMA = load_json("memory_state.schema.json")
STATE_VALIDATOR = Draft7Validator(STATE_SCHEMA)

COMPRESS_SYSTEM = (
    "You compress a support conversation into one structured state object. "
    "Only record what the applicant actually said - never invent or infer a "
    "fact that was not stated. `facts` are things the applicant stated. "
    "`decisions` are things settled during the conversation. `constraints` "
    "are conditions on how or when something can happen (a day, a deadline, "
    "a requirement the applicant set). `open_questions` are things asked "
    "and not yet answered. Reply with a single JSON object matching this "
    "schema exactly, nothing else:\n" + json.dumps(STATE_SCHEMA, ensure_ascii=False)
)


class ChatSession:
    """One conversation, with an optional compression point.

    `turns` holds the whole conversation (every user/assistant message ever
    sent), used as the source when compress() is called. `active_context`
    is what actually gets resent on every call: the full `turns` list until
    a compression happens, then the compressed state plus whatever turns
    have occurred since.
    """

    def __init__(self, model: str = None):
        self.model = model or DEFAULT_MODEL
        self.turns = []
        self.state = None
        self.post_compress_turns = []
        self.last_usage = None
        self.last_tokens_sent = None
        self.last_compress_failed_reason = None

    def _active_context(self):
        if self.state is None:
            return list(self.turns)
        summary_msg = {
            "role": "system",
            "content": "Conversation summary so far (structured, compressed):\n"
            + json.dumps(self.state, ensure_ascii=False),
        }
        return [summary_msg] + list(self.post_compress_turns)

    def send(self, user_text: str):
        messages = (
            [{"role": "system", "content": OFFICE_SYSTEM_PROMPT}]
            + self._active_context()
            + [{"role": "user", "content": user_text}]
        )
        tokens_sent = count_message_tokens(messages, self.model)
        raw, usage = chat_raw(messages, model=self.model, temperature=0.3)

        user_msg = {"role": "user", "content": user_text}
        assistant_msg = {"role": "assistant", "content": raw}
        self.turns.append(user_msg)
        self.turns.append(assistant_msg)
        if self.state is not None:
            self.post_compress_turns.append(user_msg)
            self.post_compress_turns.append(assistant_msg)

        self.last_usage = usage
        self.last_tokens_sent = tokens_sent
        return raw, tokens_sent, usage

    def compress(self):
        """Summarise the whole conversation so far. Returns (ok, state_or_raw)."""
        transcript = "\n".join(
            f"{t['role']}: {t['content']}" for t in self.turns
        )
        messages = [
            {"role": "system", "content": COMPRESS_SYSTEM},
            {"role": "user", "content": "Conversation so far:\n" + transcript},
        ]
        tokens_sent = count_message_tokens(messages, self.model)
        raw, usage = chat_raw(messages, model=self.model, temperature=0, json_mode=True)
        self.last_usage = usage
        self.last_tokens_sent = tokens_sent
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            self.last_compress_failed_reason = "reply was not valid JSON"
            return False, raw
        if not STATE_VALIDATOR.is_valid(parsed):
            errors = sorted(STATE_VALIDATOR.iter_errors(parsed), key=str)
            self.last_compress_failed_reason = "; ".join(e.message for e in errors)
            return False, raw
        self.state = parsed
        self.post_compress_turns = []
        self.last_compress_failed_reason = None
        return True, parsed


def run_probes(session: ChatSession, probes):
    results = []
    for probe in probes:
        reply, tokens_sent, usage = session.send(probe["question"])
        retrieved = any(s.lower() in reply.lower() for s in probe["expect_contains"])
        results.append(
            {
                "id": probe["id"],
                "tests": probe["tests"],
                "retrieved": retrieved,
                "reply": reply,
                "tokens_sent": tokens_sent,
            }
        )
    return results


def run_scripted(compress_enabled: bool):
    script = load_json("chat_script.json")
    session = ChatSession()
    call_log = []  # list of {"label": str, "tokens_sent": int}
    compress_result = None

    turn_no = 0
    for line in script["conversation"]:
        if line == COMPRESS_COMMAND:
            if compress_enabled:
                ok, result = session.compress()
                compress_result = (ok, result)
                call_log.append({"label": "compress()", "tokens_sent": session.last_tokens_sent})
            continue
        turn_no += 1
        _, tokens_sent, _ = session.send(line)
        call_log.append({"label": f"turn {turn_no}", "tokens_sent": tokens_sent})

    probe_results = run_probes(session, script["probes"])
    return {
        "call_log": call_log,
        "compress_result": compress_result,
        "probe_results": probe_results,
        "final_state": session.state,
    }


def print_scripted_report():
    print(f"Model: {DEFAULT_MODEL}\n")

    run_a = run_scripted(compress_enabled=False)
    run_b = run_scripted(compress_enabled=True)

    print("=== A: never compressed (the `compress` marker is skipped entirely, 11 real calls) ===")
    for c in run_a["call_log"]:
        print(f"  {c['label']:12}: {c['tokens_sent']} tokens sent")
    peak_a = max(c["tokens_sent"] for c in run_a["call_log"])
    total_a = sum(c["tokens_sent"] for c in run_a["call_log"])
    print(f"  peak: {peak_a}   total: {total_a}\n")

    print("=== B: compressed at the <compress> turn (9 turns + compress() + 2 turns = 12 calls) ===")
    for c in run_b["call_log"]:
        print(f"  {c['label']:12}: {c['tokens_sent']} tokens sent")
    if run_b["compress_result"]:
        ok, result = run_b["compress_result"]
        print(f"  compress() ok={ok}")
        if ok:
            print("  state:", json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("  compress FAILED, kept full history:", result)
    peak_b = max(c["tokens_sent"] for c in run_b["call_log"])
    total_b = sum(c["tokens_sent"] for c in run_b["call_log"])
    print(f"  peak: {peak_b}   total: {total_b}\n")

    print("=== Probes: A (never compressed) ===")
    for p in run_a["probe_results"]:
        print(f"  {p['id']:6} retrieved={p['retrieved']!s:5} tests={p['tests']}")
        print(f"         answer: {p['reply']}")

    print("\n=== Probes: B (compressed) ===")
    for p in run_b["probe_results"]:
        print(f"  {p['id']:6} retrieved={p['retrieved']!s:5} tests={p['tests']}")
        print(f"         answer: {p['reply']}")

    retrieved_a = sum(1 for p in run_a["probe_results"] if p["retrieved"])
    retrieved_b = sum(1 for p in run_b["probe_results"] if p["retrieved"])
    print(f"\nRetrieved: A {retrieved_a}/5   B {retrieved_b}/5")


def run_interactive():
    print(f"Interactive chat (model: {DEFAULT_MODEL}).")
    print("Type a message, `compress` to compress history, `tokens` to see the "
          "last call's cost, `quit` to exit.\n")
    session = ChatSession()
    while True:
        try:
            text = input("you> ").strip()
        except EOFError:
            break
        if not text:
            continue
        if text.lower() == "quit":
            break
        if text.lower() == "tokens":
            if session.last_usage is None:
                print("(no calls made yet)")
            else:
                print(
                    f"last call: {session.last_tokens_sent} tokens sent (local count), "
                    f"api usage: {session.last_usage}"
                )
            continue
        if text.lower() == "compress":
            ok, result = session.compress()
            if ok:
                print("compressed. new state:")
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"compress FAILED ({session.last_compress_failed_reason}); history kept.")
            continue
        reply, tokens_sent, usage = session.send(text)
        print(f"assistant> {reply}")
        print(f"  ({tokens_sent} tokens sent)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()
    if args.interactive:
        run_interactive()
    else:
        print_scripted_report()


if __name__ == "__main__":
    main()
