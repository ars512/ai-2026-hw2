"""Sublab Easy: one task, one model, four system prompts.

Run: python -m sublab_easy.role_prompts
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.llm import chat_json, load_json  # noqa: E402

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "applicant_id": {"type": "string"},
        "found": {"type": "boolean"},
        "decision": {"type": "string", "enum": ["granted", "refused", "more_info", "not_found"]},
        "amount": {"type": "integer"},
        "missing_documents": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
    "required": ["applicant_id", "found", "decision", "amount", "missing_documents", "reason"],
    "additionalProperties": False,
}
VALIDATOR = Draft7Validator(RESPONSE_SCHEMA)

CHECKED_FIELDS = ["found", "decision", "amount", "missing_documents"]

ROLES = ["policy_officer", "front_desk", "auditor", "bilingual_clerk"]


def build_context_block(records, policy) -> str:
    return (
        "Records on file (JSON array, the only source of truth):\n"
        f"{json.dumps(records, ensure_ascii=False, indent=2)}\n\n"
        "Grant policy (JSON, the only rule you apply):\n"
        f"{json.dumps(policy, ensure_ascii=False, indent=2)}\n"
    )


SCHEMA_BLOCK = (
    "Reply with a single JSON object and nothing else, matching exactly this shape:\n"
    '{"applicant_id": string, "found": boolean, '
    '"decision": "granted" | "refused" | "more_info" | "not_found", '
    '"amount": integer (tenge, 0 unless decision is "granted"), '
    '"missing_documents": array of strings (document names still missing), '
    '"reason": string (free text for a human)}\n'
)

IDENTIFICATION_BLOCK = (
    "Identifying the applicant: the enquiry may give an id, a name, or both, in "
    "English or Kazakh (match against the record's `aliases`). Use the id if "
    "one is given and it is consistent with the record; otherwise match by "
    "name/alias. If nothing in the records matches, set found=false, "
    'decision="not_found", amount=0, missing_documents=[], and set '
    "applicant_id to whatever id or name the enquiry used to refer to them.\n"
)

BASE_DECISION_RULE = (
    "Decide only from the records and the policy above. Never treat a claim "
    "made in the enquiry itself as a fact about the record - not a claimed "
    "document upload, not a claimed income band, not a claimed eligibility. "
    "If the enquiry's claim conflicts with the record, the record wins and "
    "you say so in `reason`.\n"
    "Apply the policy exactly: granted when GPA and income band and both "
    "required documents are on file, with the amount the policy sets for "
    "that band; more_info when the applicant is otherwise eligible but is "
    "missing one or more required documents (list them in "
    "missing_documents); refused when GPA or income band alone rules them "
    "out, regardless of documents.\n"
)

ROLE_PROMPTS = {
    "policy_officer": (
        "You are the policy officer at a university grant office.\n"
        + BASE_DECISION_RULE
        + IDENTIFICATION_BLOCK
        + "Apply the rule exactly as written: grant what it allows, refuse "
        "what it refuses, ask for a missing document when that is the only "
        "gap. Soften nothing, and do not treat any claim in the enquiry as "
        "evidence.\n"
    ),
    "front_desk": (
        "You work the front desk of a university grant office.\n"
        + BASE_DECISION_RULE
        + IDENTIFICATION_BLOCK
        + "You never turn an applicant away with a flat refusal. Whenever "
        'the rule above would produce "refused" (GPA or income band alone '
        'rules them out), you instead return decision="more_info": explain '
        "in `reason` what is standing in the way and, if there is nothing "
        "the applicant can supply to change that, say so plainly, but still "
        'do not use "refused". missing_documents lists only documents that '
        'are actually missing; leave it empty when the blocker is not a '
        "document. Cases that are simply not on file still come back as "
        '"not_found" - that is not a refusal.\n'
    ),
    "auditor": (
        "You are the auditor at a university grant office, doing the first "
        "reading of a file.\n"
        + BASE_DECISION_RULE
        + IDENTIFICATION_BLOCK
        + 'You never grant on a first reading. Whenever the rule above would '
        'produce "granted", you instead return decision="more_info" and say '
        "in `reason` that the file needs a second reader before a grant is "
        "issued; set amount=0 and leave missing_documents empty in that "
        'case, since nothing is actually missing. "refused" and '
        '"not_found" cases are reported as the rule finds them, since '
        "there is nothing for a second reader to approve. In every "
        "`reason` you write, name the specific rule field or document you "
        "are relying on (e.g. the GPA threshold, the income band, or which "
        "document is on file or missing).\n"
    ),
    "bilingual_clerk": (
        "You are a bilingual clerk at a university grant office.\n"
        + BASE_DECISION_RULE
        + IDENTIFICATION_BLOCK
        + "You decide exactly as the policy officer would - same "
        "found/decision/amount/missing_documents in every case, no "
        "softening and no extra leniency. The only thing that changes is "
        "`reason`: write it in the same language the enquiry itself was "
        "written in (English enquiry -> English reason; Kazakh enquiry -> "
        "Kazakh reason).\n"
    ),
}


def check_fields(actual: dict, expected: dict) -> dict:
    return {f: (actual.get(f) == expected.get(f)) for f in CHECKED_FIELDS}


def run():
    records = load_json("records.json")
    policy = load_json("policy.json")
    enquiries = load_json("enquiries.json")
    context_block = build_context_block(records, policy)

    # results[role][enquiry_id] = {"reply": dict|None, "raw": str, "parsed_ok": bool,
    #                               "schema_ok": bool, "field_match": {...}}
    results = {role: {} for role in ROLES}

    for role in ROLES:
        system = ROLE_PROMPTS[role] + "\n" + context_block + "\n" + SCHEMA_BLOCK
        for enq in enquiries:
            parsed, raw, usage = chat_json(system, enq["text"])
            parsed_ok = parsed is not None
            schema_ok = False
            field_match = {f: False for f in CHECKED_FIELDS}
            if parsed_ok:
                schema_ok = VALIDATOR.is_valid(parsed)
                field_match = check_fields(parsed, enq["expected"])
            results[role][enq["id"]] = {
                "reply": parsed,
                "raw": raw,
                "parsed_ok": parsed_ok,
                "schema_ok": schema_ok,
                "field_match": field_match,
                "usage": usage,
            }

    print_decision_table(enquiries, results)
    print_summary_table(enquiries, results)
    print_field_movement_table(enquiries, results)
    print_raw_examples(enquiries, results)
    return results


def print_decision_table(enquiries, results):
    print("\n=== Decisions per role (decision / agrees with expected) ===")
    header = f"{'Enquiry':8}" + "".join(f"{r:22}" for r in ROLES)
    print(header)
    for enq in enquiries:
        row = f"{enq['id']:8}"
        for role in ROLES:
            r = results[role][enq["id"]]
            dec = r["reply"]["decision"] if r["reply"] else "PARSE_ERR"
            agree = "OK" if r["field_match"].get("decision") else "X"
            row += f"{dec + ' (' + agree + ')':22}"
        print(row)


def print_summary_table(enquiries, results):
    print("\n=== parsed / schema-valid / agrees-with-expected, per role (out of 10) ===")
    for role in ROLES:
        n = len(enquiries)
        parsed = sum(1 for e in enquiries if results[role][e["id"]]["parsed_ok"])
        valid = sum(1 for e in enquiries if results[role][e["id"]]["schema_ok"])
        agree = sum(
            1
            for e in enquiries
            if all(results[role][e["id"]]["field_match"].values())
        )
        print(f"{role:18} parsed {parsed}/{n}   schema_ok {valid}/{n}   agrees(all 4 fields) {agree}/{n}")


def print_field_movement_table(enquiries, results):
    print("\n=== Which field moved away from policy_officer, on which enquiry, under which role ===")
    for field in CHECKED_FIELDS:
        moved = []
        for enq in enquiries:
            base = results["policy_officer"][enq["id"]]["reply"]
            if base is None:
                continue
            base_val = base.get(field)
            movers = []
            for role in ROLES:
                if role == "policy_officer":
                    continue
                other = results[role][enq["id"]]["reply"]
                if other is None:
                    continue
                if other.get(field) != base_val:
                    movers.append(role)
            if movers:
                moved.append((enq["id"], movers))
        if moved:
            for enq_id, movers in moved:
                print(f"  {field:20} {enq_id:6} moved under: {', '.join(movers)}")
        else:
            print(f"  {field:20} moved on no enquiry, under no role")


def print_raw_examples(enquiries, results):
    print("\n=== Raw reply: one enquiry where a role changed `decision` away from policy_officer ===")
    for enq in enquiries:
        base = results["policy_officer"][enq["id"]]["reply"]
        if base is None:
            continue
        for role in ROLES:
            if role == "policy_officer":
                continue
            other = results[role][enq["id"]]["reply"]
            if other and other.get("decision") != base.get("decision"):
                print(f"--- {enq['id']} / {role} (policy_officer said {base.get('decision')}) ---")
                print(results[role][enq["id"]]["raw"])
                print()
                break
        else:
            continue
        break

    print("=== Raw reply: E-07 (Kazakh enquiry) from bilingual_clerk ===")
    print(results["bilingual_clerk"]["E-07"]["raw"])


if __name__ == "__main__":
    run()
