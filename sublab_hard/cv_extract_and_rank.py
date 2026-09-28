"""Sublab Hard: stories in, CVs out, the best candidate by code.

Run: python -m sublab_hard.cv_extract_and_rank
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.llm import chat_json, chat_text, load_json, DATA_DIR  # noqa: E402

CANDIDATES_DIR = DATA_DIR / "candidates"
STORY_IDS = [f"story-{i:02d}" for i in range(1, 7)]

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "candidate_id": {"type": "string"},
        "full_name": {"type": ["string", "null"]},
        "degree": {"type": ["string", "null"]},
        "graduation_year": {"type": ["integer", "null"]},
        "gpa_4_scale": {"type": ["number", "null"]},
        "gpa_original_scale": {"type": ["string", "null"]},
        "languages": {"type": "array", "items": {"type": "string"}},
        "published_outputs_count": {"type": ["integer", "null"]},
        "non_published_outputs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title_or_topic": {"type": "string"},
                    "status": {"type": "string"},
                },
                "required": ["title_or_topic", "status"],
            },
        },
        "relevant_experience_months": {"type": ["integer", "null"]},
        "evidence": {
            "type": "object",
            "description": "field name -> verbatim quote from the story supporting it",
            "additionalProperties": {"type": "string"},
        },
        "ambiguities": {
            "type": "array",
            "items": {"type": "string"},
            "description": "contradictions found, and which field was set to null because of them",
        },
    },
    "required": [
        "candidate_id", "full_name", "degree", "graduation_year",
        "gpa_4_scale", "gpa_original_scale", "languages",
        "published_outputs_count", "non_published_outputs",
        "relevant_experience_months", "evidence", "ambiguities",
    ],
    "additionalProperties": False,
}
EXTRACTION_VALIDATOR = Draft7Validator(EXTRACTION_SCHEMA)

EXTRACTION_SYSTEM = (
    "You extract a structured CV record from one scholarship applicant's "
    "written story. The story may be in English or Kazakh; extract "
    "regardless of language, and keep quoted evidence in the story's "
    "original language.\n\n"
    "Rules, applied strictly:\n"
    "1. A fact the story does not state is null. Never estimate or infer a "
    "missing value (e.g. no GPA stated means gpa_4_scale is null - do not "
    "guess one from the degree or university).\n"
    "2. If the story gives a GPA on a scale other than 4.0, convert it to a "
    "4.0 scale for gpa_4_scale, and record the original number and scale as "
    "text in gpa_original_scale (e.g. \"4.6/5.0\"). If the GPA is already on "
    "a 4.0 scale, gpa_original_scale is still filled in (e.g. \"3.8/4.0\").\n"
    "3. Count a publication in published_outputs_count only when the story "
    "says it is published or accepted. 'Submitted', 'under review', 'in "
    "preparation', 'planned' and 'in press' are NOT published: list each of "
    "those in non_published_outputs with its status, and do not count it.\n"
    "4. If the story contradicts itself about a field (states two different "
    "values for the same fact with no correction), do not resolve it and do "
    "not average it: set that field to null and add a sentence to "
    "ambiguities describing the contradiction and both values.\n"
    "5. For every field you do fill in (not null), evidence must contain a "
    "short verbatim quote from the story that supports it, keyed by the "
    "field name.\n"
    "6. relevant_experience_months counts months of directly relevant work "
    "or internships; overlapping periods count once, not twice; a period "
    "with no dates given is not countable towards the number, but note it "
    "in ambiguities.\n\n"
    "Reply with a single JSON object matching exactly this schema, nothing "
    "else:\n" + json.dumps(EXTRACTION_SCHEMA, ensure_ascii=False)
)

RUBRIC = load_json("candidate_rubric.json")

SCORING_SCHEMA = {
    "type": "object",
    "properties": {
        "academic": {"type": "number", "minimum": 0, "maximum": 5},
        "research": {"type": "number", "minimum": 0, "maximum": 5},
        "experience": {"type": "number", "minimum": 0, "maximum": 5},
    },
    "required": ["academic", "research", "experience"],
    "additionalProperties": False,
}
SCORING_VALIDATOR = Draft7Validator(SCORING_SCHEMA)

SCORING_SYSTEM = (
    "You score one scholarship candidate's extracted CV record against a "
    "rubric. Score each of the three criteria from 0 to 5 using the rubric's "
    "own definitions of what 0 and 5 mean, and the counting rules given. Do "
    "not compute or return a weighted total or a ranking - only the three "
    "scores. A null field scores 0 on the criterion it belongs to, since a "
    "story with no information there does not earn credit for it.\n\n"
    "Rubric:\n" + json.dumps(RUBRIC, ensure_ascii=False) + "\n\n"
    "Reply with a single JSON object matching exactly this schema, nothing "
    "else:\n" + json.dumps(SCORING_SCHEMA, ensure_ascii=False)
)

PROSE_SYSTEM = (
    "You are advising a scholarship committee with one funded place and six "
    "candidates. You will be given all six candidates' extracted CV records "
    "and the scoring rubric. Answer in prose: who should win, and why. Do "
    "not return JSON."
)


def read_story(story_id: str) -> str:
    path = CANDIDATES_DIR / f"{story_id}.md"
    return path.read_text(encoding="utf-8")


def extract_candidate(story_id: str, story_text: str):
    user = f"Candidate id: {story_id}\n\nStory:\n{story_text}"
    parsed, raw, usage = chat_json(EXTRACTION_SYSTEM, user)
    parsed_ok = parsed is not None
    valid_ok = parsed_ok and EXTRACTION_VALIDATOR.is_valid(parsed)
    return {
        "story_id": story_id,
        "parsed": parsed,
        "raw": raw,
        "parsed_ok": parsed_ok,
        "valid_ok": valid_ok,
        "usage": usage,
    }


def score_candidate(extraction: dict):
    user = "Extracted CV record:\n" + json.dumps(extraction["parsed"], ensure_ascii=False)
    parsed, raw, usage = chat_json(SCORING_SYSTEM, user)
    parsed_ok = parsed is not None
    valid_ok = parsed_ok and SCORING_VALIDATOR.is_valid(parsed)
    return {
        "story_id": extraction["story_id"],
        "scores": parsed,
        "raw": raw,
        "parsed_ok": parsed_ok,
        "valid_ok": valid_ok,
    }


def weighted_total(scores: dict) -> float:
    weights = {c["id"]: c["weight"] for c in RUBRIC["criteria"]}
    total = (
        weights["academic"] * scores["academic"]
        + weights["research"] * scores["research"]
        + weights["experience"] * scores["experience"]
    )
    return round(total, 2)


def null_fields(record: dict) -> list:
    skip = {"candidate_id", "languages", "non_published_outputs", "evidence", "ambiguities"}
    return [k for k, v in record.items() if k not in skip and v is None]


def run():
    extractions = []
    for story_id in STORY_IDS:
        text = read_story(story_id)
        extractions.append(extract_candidate(story_id, text))

    print_extraction_table(extractions)
    print_story_06(extractions)

    scorings = []
    for ext in extractions:
        if ext["parsed_ok"]:
            scorings.append(score_candidate(ext))
        else:
            scorings.append({"story_id": ext["story_id"], "scores": None, "parsed_ok": False})

    ranking = print_scores_and_winner(scorings)

    prose = ask_prose_opinion(extractions)
    print("\n=== Model's prose answer (\"who should win?\") ===")
    print(prose)

    return extractions, scorings, ranking, prose


def print_extraction_table(extractions):
    print("=== Part 1: extraction, per story ===")
    for ext in extractions:
        if not ext["parsed_ok"]:
            print(f"{ext['story_id']:10} parsed=FALSE valid=FALSE")
            continue
        nulls = null_fields(ext["parsed"])
        ambiguities = ext["parsed"].get("ambiguities", [])
        print(
            f"{ext['story_id']:10} parsed=True valid={ext['valid_ok']!s:5} "
            f"null_fields={nulls} ambiguities={ambiguities}"
        )


def print_story_06(extractions):
    print("\n=== Extraction for story-06 (the self-contradicting one) ===")
    for ext in extractions:
        if ext["story_id"] == "story-06":
            print(json.dumps(ext["parsed"], ensure_ascii=False, indent=2))


def print_scores_and_winner(scorings):
    print("\n=== Part 2: scores (model) and weighted total (code) ===")
    ranking = []
    for s in scorings:
        if not s.get("parsed_ok"):
            print(f"{s['story_id']:10} SCORING FAILED")
            continue
        total = weighted_total(s["scores"])
        ranking.append((s["story_id"], s["scores"], total))
        print(
            f"{s['story_id']:10} academic={s['scores']['academic']} "
            f"research={s['scores']['research']} experience={s['scores']['experience']} "
            f"total={total}"
        )
    ranking.sort(key=lambda r: r[2], reverse=True)
    if ranking:
        print(f"\nWinner (computed by code): {ranking[0][0]} (total={ranking[0][2]})")
        if len(ranking) > 1:
            gap = round(ranking[0][2] - ranking[1][2], 2)
            print(f"Runner-up: {ranking[1][0]} (total={ranking[1][2]}, gap={gap})")
    return ranking


def ask_prose_opinion(extractions):
    records_block = json.dumps(
        [ext["parsed"] for ext in extractions if ext["parsed_ok"]], ensure_ascii=False, indent=2
    )
    user = "Candidate records:\n" + records_block
    raw, usage = chat_text(PROSE_SYSTEM, user)
    return raw


if __name__ == "__main__":
    run()
