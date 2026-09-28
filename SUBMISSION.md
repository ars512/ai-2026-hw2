# HW2 submission

**Name:** Arseny
**Student ID:** 23071798
**Group:** mon 9:30
**Repository:** https://github.com/ars512/ai-2026-hw2

## AI tool disclosure

Claude Code (Anthropic) was used to write all three programs
(`sublab_easy/role_prompts.py`, `sublab_medium/chat_memory.py`,
`sublab_hard/cv_extract_and_rank.py`), the shared `common/` helpers, and the
analysis below, based on a close reading of this repository's `README.md`
and every file under `data/`.

**Model note:** the README names a model, `gpt-5.6-luna`, that does not
exist in OpenAI's public catalog (it reads as a placeholder for the course's
own setup). All final numbers in this submission are from a real OpenAI
account, using **`gpt-4o-mini`** (set via `OPENAI_MODEL` in `.env`) through
the standard `openai` Python SDK - the same provider and env var
(`OPENAI_API_KEY`) the README asks for. While waiting for my OpenAI billing
to be set up, I first developed and dry-ran everything against Groq's free
OpenAI-compatible API (`openai/gpt-oss-120b`) purely to validate the code
without spending money; every table, transcript and score below is from the
final OpenAI reruns, not the Groq dry runs. `common/llm.py` supports an
optional `OPENAI_BASE_URL` override for that reason, but it is unset for
the run behind this submission. Every comparison (the four roles, the two
memory runs, the six candidates) ran on exactly one model throughout, which
is the property the comparisons actually depend on.

>

---

## Sublab Easy — one task, four roles

### Decisions per role

One row per enquiry. In each cell write the `decision` your run returned, and
whether it agrees with `expected` in `data/enquiries.json`:

| Enquiry | policy_officer | front_desk | auditor | bilingual_clerk |
|---|---|---|---|---|
| E-01 | granted (agrees) | granted (agrees) | more_info (**moved**) | granted (agrees) |
| E-02 | more_info (agrees) | more_info (agrees) | refused (**moved**, disagrees) | more_info (agrees) |
| E-03 | refused (agrees) | more_info (**moved**) | refused (agrees) | refused (agrees) |
| E-04 | refused (agrees) | more_info (**moved**) | refused (agrees) | refused (agrees) |
| E-05 | granted (agrees) | granted (agrees) | more_info (**moved**) | granted (agrees) |
| E-06 | more_info (**wrong** — expected granted) | more_info (wrong) | refused (wrong) | granted (agrees) |
| E-07 | granted (agrees) | granted (agrees) | more_info (**moved**) | granted (agrees) |
| E-08 | not_found (agrees) | not_found (agrees) | not_found (agrees) | not_found (agrees) |
| E-09 | refused (agrees) | more_info (**moved**) | refused (agrees) | refused (agrees) |
| E-10 | refused (**wrong** — expected more_info) | more_info (decision label matches, but see note) | refused (wrong) | refused (wrong) |
| **agrees with `expected`** | 8/10 | 5/10 | 4/10 | 9/10 |
| **parsed** | 10/10 | 10/10 | 10/10 | 10/10 |
| **schema-valid** | 10/10 | 10/10 | 10/10 | 10/10 |

`front_desk` and `auditor` disagree with `expected` on E-01/E-03/E-04/E-05/
E-07/E-09 **by design**: `expected` is the policy officer's answer, and
those two roles are defined to deliberately depart from it. E-02, E-06 and
E-10 are different: there `policy_officer` itself - the role that is
supposed to reproduce `expected` exactly - got the wrong answer. That is a
genuine model reasoning error with `gpt-4o-mini`, not a role effect; see the
raw replies and written answers below for what actually went wrong.

### Which field moved, on which enquiry, under which role

| Field | Enquiries that moved | Role(s) that moved it |
|---|---|---|
| `found` | moved on no enquiry, under no role | — |
| `decision` | E-01, E-05, E-07 | `auditor` (clean grant→more_info override) |
| `decision` | E-03, E-04, E-09, E-10 | `front_desk` (refused→more_info override) |
| `decision` | E-02 | `auditor` (see note below - not the intended override) |
| `decision` | E-06 | `auditor`, `bilingual_clerk` |
| `amount` | E-01, E-05, E-07 | `auditor` |
| `amount` | E-06 | `bilingual_clerk` |
| `missing_documents` | E-02 | `auditor` |
| `missing_documents` | E-03, E-09 | `front_desk` |
| `missing_documents` | E-06 | `front_desk`, `auditor`, `bilingual_clerk` |

`found` never moved under any role, on any enquiry - identity resolution is
read straight off the record and no role paragraph gives the model room to
reinterpret it. Note on E-02: `auditor`'s design only overrides *granted*
cases; E-02 is a `more_info` case from the start (missing `id_card`), so
`auditor` moving its `decision` to `refused` here is **not** the intended
grant→more_info override - it is `auditor` mishandling a case its own
prompt never explicitly addresses (see written answer 2). E-06 is the
opposite kind of surprise: `policy_officer` itself is wrong there (see the
decisions table), so "moved away from `policy_officer`" on E-06 partly means
`bilingual_clerk` moved *away from an error*, not away from a correct
baseline.

### Raw replies

Paste the full reply for **one enquiry where a role changed the decision** away
from the policy officer's:

```
--- E-01 / auditor (policy_officer said granted) ---
{"applicant_id":"A-201","found":true,"decision":"more_info","amount":0,"missing_documents":[],"reason":"The file needs a second reader before a grant is issued, as the GPA is 3.4 and the income band is 1, with both required documents (transcript and id_card) on file."}
```

Paste the full reply for **E-07 (the Kazakh enquiry)** from the bilingual
clerk, so the `reason` language is visible:

```
{"applicant_id":"A-201","found":true,"decision":"granted","amount":250000,"missing_documents":[],"reason":"Сіздің GPA 3.4, табыс тобы 1, және барлық қажетті құжаттарыңыз (транскрипт, жеке куәлік) бар. Сіз грант алуға құқылысыз."}
```

Two more raw replies, pasted here because they are the actual `policy_officer`
model errors the tables above refer to - not a role effect, so they earn a
closer look than a summary line:

```
--- E-06 / policy_officer (expected: granted, 150000) ---
{"applicant_id":"A-206","found":true,"decision":"more_info","amount":0,"missing_documents":["id_card"],"reason":"Sanzhar Beket has a GPA of 2.7 and is in income band 2, which qualifies him for the grant, but he is missing the required id_card."}
```
The record (`data/records.json`) lists A-206's documents as
`["transcript", "id_card"]` - both present. The model invented a missing
document that is not in the record it was given.

```
--- E-10 / policy_officer (expected: more_info, missing id_card) ---
{"applicant_id":"A-202","found":true,"decision":"refused","amount":0,"missing_documents":[],"reason":"The GPA of 2.9 does not meet the minimum requirement of 2.67 for the grant."}
```
2.9 is greater than 2.67. The policy's own threshold check
(`data/policy.json`: `"gpa_min": 2.67`) is satisfied, and the model's own
sentence states both numbers correctly - it just compared them wrong.

```
--- E-10 / front_desk (expected: more_info, missing id_card) ---
{"applicant_id":"A-202","found":true,"decision":"more_info","amount":0,"missing_documents":[],"reason":"The GPA of 2.9 does not meet the minimum requirement of 2.67 for the grant. Therefore, even with the uploaded id card, the application cannot be granted."}
```
Checked specifically because the decisions table shows `front_desk` landing
on the "right" label here: it made the **same** GPA comparison error as
`policy_officer`, word for word. It only ends up saying `more_info` because
its role converts anything it thinks isn't grantable into `more_info`
regardless of why - and even then, its `missing_documents` is `[]`, not the
expected `["id_card"]`, because as far as it (wrongly) believes, GPA is the
blocker, not the document. So this is not a case of the role reasoning
correctly through the trap; it is one wrong answer and one role-shaped
label collision that happens to read as correct on `decision` alone.

### Written answers

**1. Which fields are role-sensitive and which are not?** Point at rows in your
tables.

> `decision` and `amount` are role-sensitive; `found` is not (0 movements,
> see the field-movement table). `missing_documents` is mostly not
> role-sensitive either, except where a role's *decision* error drags it
> along (E-06). The clean, by-design contrast: `auditor` moves `decision` on
> every enquiry that would otherwise be `granted` (E-01, E-05, E-07 - 3/10),
> turning it into `more_info`; `front_desk` moves it on every enquiry that
> would otherwise be `refused` (E-03, E-04, E-09, E-10 - 4/10), also into
> `more_info`. `bilingual_clerk` moves `decision` on no enquiry except E-06 -
> and E-06 is the case where `policy_officer` itself was wrong, so
> `bilingual_clerk` "moving" there is really it independently landing on the
> *correct* answer rather than copying an error; everywhere else, the only
> thing it touches is `reason`'s language, exactly as the role was written
> to do. `auditor` also moved `decision` on E-02, but that is not the
> intended grant→more_info override (E-02 was never `granted` to begin
> with) - it's the same kind of base-model slip discussed in question 2,
> not a role effect.

**2. Which enquiries are most sensitive to the role, and why those?** Say what
E-03, E-04, E-07 and E-10 are each testing.

> E-03 and E-04 are straightforward `refused` cases (GPA/band alone rule the
> applicant out) - they test whether a role is willing to actually refuse
> someone. `front_desk` is defined not to, so both move under it and nowhere
> else, cleanly. E-07 is the Kazakh-language `granted` case, and it is the
> enquiry that moves under two different roles for two different reasons at
> once: `auditor` moves its `decision` (same as any other grant case), and
> `bilingual_clerk` moves only its `reason`'s language - so E-07 shows the
> widest range of *intended* role effects side by side, cleanly. E-10 tests
> something else: the applicant claims their ID card was updated
> "yesterday," but the record still shows it missing - it's meant to check
> whether a role treats the claim as fact. In my run, three of four roles
> (`policy_officer`, `auditor`, `bilingual_clerk`) answered `refused`, which
> is wrong on both counts: it is not what the trap is testing for (it should
> be `more_info`, since the applicant is otherwise eligible and only a
> document is missing) and the model's own stated reason was a GPA
> comparison error, not the intended "claims aren't facts" test at all (see
> the raw reply above - "2.9 does not meet 2.67" is simply false). Only
> `front_desk`'s `decision` label matches the expected `more_info`, and even
> that is coincidence, not correct reasoning: its raw reply repeats the
> *same* wrong GPA comparison almost word for word, and its
> `missing_documents` comes back `[]`, not the expected `["id_card"]`,
> because it too believes GPA is the blocker - it only reads as "right" on
> one field because its role forces `more_info` on anything it thinks isn't
> grantable. So E-10 is the clearest case in my run where role framing
> turned out to matter less than a plain model error sitting underneath
> every role.

**3. Where does discretion belong — the role paragraph, or code that reads
`decision` afterwards?** Say what a downstream program can and cannot tell
about which role produced a record.

> In this design, discretion lives entirely in the role paragraph - the
> JSON schema (`RESPONSE_SCHEMA` in `role_prompts.py`) has no field that
> names which role produced a record. That is a real gap: `decision:
> "more_info"` means at least three different things depending on who said
> it and why. From `auditor` on a grant case it means "eligible, held for a
> second reader" (amount would have been paid); from `front_desk` on a
> refusal it means "actually ineligible under the policy, phrased gently"
> (nothing was ever going to be paid); and, as E-02 and E-06 show, it can
> also just mean "the model made an arithmetic or record-reading error" -
> which looks identical on the wire to the other two. A downstream program
> that only reads the five checked fields cannot tell any of these apart; it
> would have to know which system prompt produced the record, and even then
> it could not distinguish a deliberate role override from a plain mistake.
> If that distinction mattered operationally, it belongs in code: compute
> the policy-true decision from `records.json` + `policy.json` directly (the
> rule is fully mechanical), and let the role only change tone/language
> around a decision the code - not the model - has already verified.

**4. Is a role a boundary?** Say in Week 2 terms what the role paragraph is
made of, and what you would put in code — not in the prompt — if a wrong
`decision` were expensive.

> No. In Week 2 terms, the role paragraph is just more tokens entering the
> same stack as everything else in the prompt - the model is still
> continuing a document, not obeying a chain of command, and nothing about
> a system message makes its instructions structurally different from an
> enquiry's text; it's a strong prior, not an enforced rule. This run makes
> that concrete rather than theoretical: `policy_officer` is the one role
> with no discretion at all - "apply the rule exactly as written" - and it
> still got E-06 and E-10 wrong, on the *same* shared decision rule every
> other role also received. A wrong comparison ("2.9 does not meet 2.67")
> or an invented missing document isn't a role failing to hold its
> boundary; it's proof there was never an enforced boundary to fail, only a
> pattern the model usually follows. If a wrong `decision` were expensive, I
> would not trust the model to *be* the decision authority at all: I would
> compute `decision` and `amount` from `records.json` + `policy.json`
> directly in Python (the rule is fully mechanical - one GPA comparison, one
> band lookup, two document checks - exactly the kind of thing this run
> shows a model can still get wrong), call the model only for `reason` and
> tone, and validate that the model's own `decision` field matches the
> code-computed one before anything reaches an applicant.

---

## Sublab Medium — memory you choose

### Tokens per call

Model: `gpt-4o-mini`. Run B has 12 calls (9 turns + the `compress()` call
itself + 2 turns); run A has only 11, because the `<compress>` marker is
skipped entirely rather than sent as a message — so "call 12" in A is blank
by construction, not a missing measurement.

| Call | A — never compressed | B — compressed at the `compress` turn |
|---|---|---|
| 1 | 245 | 245 |
| 2 | 283 | 283 |
| 3 | 365 | 355 |
| 4 | 422 | 425 |
| 5 | 469 | 463 |
| 6 | 534 | 534 |
| 7 | 604 | 600 |
| 8 | 686 | 679 |
| 9 | 747 | 734 |
| 10 (compress() in B) | 818 | 924 (the compress() call) |
| 11 | 856 | 443 (first call after compression) |
| 12 | — (marker skipped) | 482 |
| **peak** | 856 | 924 |
| **total for the run** | 6029 | 6167 |

### Probes after the conversation

| Probe | Tests | A retrieved? | A answer | B retrieved? | B answer |
|---|---|---|---|---|---|
| Q-1 identity | turn 1 | yes | "You are Daniyar Qoshan, and your applicant ID is A-202." | yes | "You are Daniyar Qoshan, and your applicant ID is A-202." |
| Q-2 missing document | turn 5 | yes | "The document still missing from your file is your ID card." | yes | "The document missing from your file is your id card." |
| Q-3 band and amount | turns 3–4 | yes | "Your income band is 2, which means you would receive 150,000 tenge if your application is approved." | yes | "Your income band is 2, which qualifies you for a grant of 150,000 tenge." |
| Q-4 the constraint | turn 6 | yes | "You can come to the office on Thursday, as you mentioned you have lab all week otherwise." | yes | "You can come to the office on Thursdays." |
| Q-5 the open question | turn 7 | yes | "You asked if a scanned letter from your employer would count, or if it had to be the original. I mentioned that a scanned letter is acceptable..." | yes | "You mentioned that a scanned letter from your employer is acceptable as long as it is clear and legible." |
| **retrieved** | | 5/5 | | 5/5 | |

`gpt-4o-mini` stayed in English throughout and used plain ASCII
punctuation, so all 5 probes were retrievable in both runs on the first
try - no methodology issue here (this is worth mentioning because an
earlier development pass against a different, free model *did* hit a
language-switching / typographic-punctuation issue that broke this exact
probe check without actually losing information; see the model note in the
AI tool disclosure section for why that pass isn't what these numbers come
from).

### The state my compression produced

```json
{
  "applicant_id": "A-202",
  "topic": "Study Grant Application",
  "facts": [
    "My name is Daniyar Qoshan.",
    "I sent my transcript last week.",
    "My income band is 2 - my family's certificate says so.",
    "I could not upload my id card because the scanner at home broke.",
    "I can only come to the office on Thursdays, I have lab all week otherwise.",
    "My sister Aruzhan applied last year and she is on file too."
  ],
  "decisions": [
    "You qualify for the grant of 150,000 tenge if you provide the id_card.",
    "A scanned letter from my employer is acceptable as long as it is clear and legible.",
    "If I bring the id_card on Thursday, the decision will be made the same day."
  ],
  "constraints": [
    "I can only come to the office on Thursdays."
  ],
  "open_questions": [],
  "language": "en"
}
```

### Written answers

**1. What did compression buy?** Peak tokens both ways, probes retrieved both
ways, and — if a probe was lost — which one and which turn it came from.

> No probe was lost either way - both A and B retrieved 5/5. At only 11
> turns, compression did not even lower the *peak*: peak(A) = 856 tokens,
> peak(B) = 924 tokens, because `compress()` has to read the entire
> transcript in one call, and that single call cost more than the biggest
> ordinary call in A. The payoff is visible per-call, not at the peak: the
> first call after compression (call 11 in B) cost 443 tokens versus 856 for
> the equivalent call in A - roughly half - and stayed at 482 for call 12
> instead of climbing further. So for an 11-turn script, compression is
> break-even to slightly worse on total/peak tokens (total(A) = 6029,
> total(B) = 6167), but it resets the growth curve; the longer the
> conversation continues past that point, the more it would have saved,
> since A's per-call cost grows without bound and B's does not.

**2. Why must the state be structured rather than a paragraph?** You could have
asked for "a summary". Say what changes when the summary is an object with
named fields.

> A paragraph gives you nothing to check before you trust it. With named
> fields I can validate the reply against `memory_state.schema.json`
> (`STATE_VALIDATOR.is_valid(...)` in `chat_memory.py`) before replacing the
> conversation, and fall back to keeping full history if it fails - that
> fallback is the whole point of the design ("losing a conversation to a
> malformed summary is the failure this design is meant to prevent"). A
> prose summary can't fail validation; it can only be silently incomplete.
> Named fields also make the state addressable: `open_questions` can be
> checked for emptiness, `constraints` can be diffed against later turns,
> and a future version of this program could drop just one field (say,
> `decisions`) without touching the rest - a paragraph would have to be
> re-parsed with another model call to get any of that back.

**3. What is missing from your state that you would add?** Name what you would
add and what you would drop to pay for it.

> In my run, "I can only come to the office on Thursdays" ended up stated
> almost verbatim in **both** `facts` and `constraints` - the model didn't
> dedupe across fields, so the same sentence is paid for twice. I would add
> a `documents_status` field - a small object like `{"id_card": "missing"}`
> - so a downstream program could read document state directly instead of
> re-parsing it out of prose `facts`/`decisions` strings. To pay for it
> within the same rough budget, I would drop the freestanding `topic`
> string: it carried one line of low-density information ("Study Grant
> Application") that is already implied by `applicant_id` plus the policy
> context the assistant already has, and I'd rather spend those tokens on a
> field the model duplicated for free than on one it barely used.

**4. When is compression the wrong choice?** Name a conversation where it would
lose something that cannot be recovered, and say whether your program would
notice.

> A conversation where the applicant states something verbatim that would
> matter later precisely because of its wording - e.g. quoting an exact
> clause from an appeal letter, or explicitly waiving a right in their own
> words - is a bad candidate for compression. `compress()` asks the model to
> paraphrase into `facts` as short strings; nothing requires or checks that
> the original wording survives. My program would **not** notice: its only
> safety check is JSON-schema validity (`STATE_VALIDATOR.is_valid`), not
> fidelity to the source text, so a fluent but lossy paraphrase of a legally
> load-bearing sentence would pass validation and silently replace the
> original wording.

---

## Sublab Hard — stories in, CVs out, the best candidate by code

### Part 1 — extraction

| Story | Parsed? | Valid? | Fields that came back `null` | Traps hit |
|---|---|---|---|---|
| story-01 (Aziza) | yes | yes | none | none — both papers explicitly "published"/"peer-reviewed", GPA already on 4.0 |
| story-02 (Dias) | yes | yes | `gpa_4_scale`, `gpa_original_scale` | **no GPA stated** ("no GPA figure... I am not going to make one up") |
| story-03 (Lyazzat) | yes | yes | none | **GPA on another scale** (4.6/5.0 → 3.68/4.0, correctly converted) + **paper not published** (one paper "under review", excluded and listed separately) |
| story-04 (Tamerlan) | yes | yes | none | **paper not published** (1 published, 3 excluded: 1 under review + 2 "in preparation") |
| story-05 (Aisha, Kazakh) | yes | yes | none | **paper not published** (a second paper "жазылып жатыр... еш жерге жіберілген жоқ" — being written, not submitted) |
| story-06 (Nurzhan) | yes | yes | none | **contradicts itself, only partially handled** — see below |

The four traps, for reference: no GPA stated · a GPA on another scale · a paper
that is not published · a story that contradicts itself. Three of the four
traps were handled correctly; the fourth (contradiction, story-06) exposed a
real gap - see the extraction below and written answer 1.

**story-06 did not behave the way Part 1's rule 4 specifies**, and this is
worth flagging honestly rather than glossing over: the story has *two*
contradictions (graduation year: 2024 vs. "final-year, graduating 2026"; GPA:
3.2 vs. 3.5). The model's `ambiguities` list correctly *names* the
graduation-year contradiction, but it left `graduation_year` filled in as
`2024` instead of nulling it - the rule says a contradicted field must be
null, not just flagged in prose. The GPA contradiction is worse: it is not
mentioned in `ambiguities` at all, and `gpa_4_scale` came back as a plain
`3.2`, as if the story had stated one clean number. Two validation runs (one
before, one after an unrelated schema fix) reproduced this identically, so
it isn't a one-off sampling fluke.

Paste the extraction for **story-06**, the one that contradicts itself:

```json
{
  "candidate_id": "story-06",
  "full_name": "Nurzhan Abilov",
  "degree": "BSc in Statistics",
  "graduation_year": 2024,
  "gpa_4_scale": 3.2,
  "gpa_original_scale": "3.2/4.0",
  "languages": ["Kazakh", "Russian", "English"],
  "published_outputs_count": 1,
  "non_published_outputs": [],
  "relevant_experience_months": 40,
  "evidence": {
    "degree": "BSc in Statistics",
    "graduation_year": "2024",
    "gpa_4_scale": "3.2",
    "gpa_original_scale": "3.2/4.0",
    "published_outputs_count": "one paper published",
    "relevant_experience_months": "about forty months",
    "languages": "Kazakh, Russian, English"
  },
  "ambiguities": [
    "The candidate states they graduated in 2024 but also mentions being a final-year student graduating in 2026, leading to a contradiction about their graduation status."
  ]
}
```

This is the actual model output, kept as-is rather than hand-corrected: it
shows the trap only being half-caught (see the note above the table).

### Part 2 — scores and the winner

| Candidate | academic (0–5) | research (0–5) | experience (0–5) | weighted total (code) |
|---|---|---|---|---|
| story-01 (Aziza) | 5 | 5 | 1 | **4.20** |
| story-02 (Dias) | 0 | 1 | 5 | 1.30 |
| story-03 (Lyazzat) | 5 | 1 | 1 | 3.00 |
| story-04 (Tamerlan) | 4 | 1 | 5 | 3.30 |
| story-05 (Aisha) | 5 | 1 | 1 | 3.00 |
| story-06 (Nurzhan) | 0 | 1 | 5 | 1.30 |

Weights from `data/candidate_rubric.json`: `0.5*academic + 0.3*research +
0.2*experience`, rounded to two decimals, computed in
`weighted_total()` in `cv_extract_and_rank.py` — never by the model.

**Winner, computed by my code:** story-01 (Aziza Bekova), total 4.20.
Runner-up: story-04 (Tamerlan), total 3.30, gap 0.90.

**The model's prose answer, asked separately ("who should win?"):**

> "After reviewing the candidates' records, I recommend awarding the
> scholarship to Aziza Bekova." The model wrote a full paragraph-by-paragraph
> comparison against every other candidate by name, citing her 3.8/4.0 GPA,
> her one cited publication (mentioning only one of her two, unlike the
> extraction which correctly counted both), her 8 months of experience, and
> her C1 English, and explicitly noted Nurzhan's "lower GPA of 3.2 and a
> contradictory graduation status" as a mark against him — the same
> contradiction that Part 1's extraction only half-handled. Full reply saved
> in `hard_output.txt` from the run.


### Part 3 — written answers

**1. Which rule did you have to add, and what broke without it?** Name the
story that forced it.

> Two rules, found by actually running it and reading the validation
> failures - not anticipated in advance. First: my initial `EXTRACTION_SYSTEM`
> said evidence "must contain a short verbatim quote," but did not say it
> had to be a *string*. On the first run, **story-04, story-05 and
> story-06** all came back `valid=False` because the model put bare numbers
> into `evidence` (e.g. `"evidence.graduation_year": 2024` instead of
> `"2024"`), which `EXTRACTION_SCHEMA`'s `additionalProperties: {"type":
> "string"}` rejects. Adding "every evidence value is a plain quoted string,
> even for a numeric field" fixed all three. Second, **story-01** stayed
> `valid=False` even after that fix, for a different reason: the model had
> copied schema *keywords* into its own answer - the object came back with
> stray top-level `"type": "object"` and `"properties": {}` keys, echoing
> the schema I had pasted into the prompt for reference. `additionalProperties:
> false` in `EXTRACTION_SCHEMA` is what caught this. I added an explicit
> "do not copy schema keywords like `type` or `properties` into your
> answer" sentence, reran, and all six stories validated.

**2. Where did the model guess, and where did your code have to decide?** One
example of each, from your run.

> Model guess: converting Lyazzat's GPA (story-03) from 4.6/5.0 to a 4.0
> scale (3.68) is a small arithmetic judgement the model made on its own -
> mechanical, and correct, but still the model doing the conversion,
> unverified by my code. Code decision: the weighted total and the winner
> are never touched by the model - `weighted_total()` computes
> `0.5*academic + 0.3*research + 0.2*experience` in Python from the three
> raw scores, and `print_scores_and_winner()` sorts on that computed number.
> The model is never asked for, and never returns, a total or a rank.

**3. Did your prose ranking and your computed ranking agree?** Say which one
you trust and why — and if they agreed, what you would need to see before
trusting the prose one alone.

> They agreed: both picked story-01 (Aziza Bekova). I trust the computed
> one anyway. The prose answer said Aziza has "one cited publication" and
> praised her for it - but the structured extraction (asked of the *same*
> model, on the *same* story) correctly recorded `published_outputs_count:
> 2`. So the model's own two outputs about the same candidate disagree with
> each other on a plain countable fact; the prose call isn't reliably
> re-deriving the record, it's writing a plausible-sounding paragraph around
> a vague impression of it. It happened to still rank the same candidate
> first, but "right conclusion, wrong supporting fact" is not something I'd
> want to build on. Before trusting a prose ranking alone, I would want it
> to state the exact field values it is using (so a mismatch like this is
> visible) and compute the same weighted arithmetic - at which point it
> stops being "prose" and becomes a check on the computed table, which is
> really the point of Part 2.

**4. The rubric has no anchor for a contradicted field.** The stories say 3.2
and then 3.5; the rubric defines a 0 and a 5 and nothing in between for this
case. Say what you did and what the rule should be.

> What actually happened is more revealing than what I designed. My rule
> says a contradiction nulls the field; in practice, `gpt-4o-mini` did *not*
> null `gpa_4_scale` for story-06 - it kept `3.2` and only narrated part of
> the contradiction in `ambiguities` (see Part 1). So the "null scores 0"
> path I built for Part 2 never actually fired for this field. And yet
> story-06 still scored `academic=0` - which means the scoring call reached
> the right number through a path I didn't design and can't rely on: it saw
> a non-null `3.2` plus a contradiction noted in `ambiguities` and
> apparently discounted the GPA anyway, on its own judgement. That's the
> real gap the rubric doesn't anchor: not just "what number does a
> contradicted field get," but "what happens when the upstream rule that
> was supposed to null it doesn't fire." The rule I'd propose: don't leave
> this to either model's judgement at all - have **code** scan
> `ambiguities` for a mention of the criterion in question and force that
> score (or a fixed floor, e.g. 1/5) deterministically before it ever
> reaches the model, so the outcome doesn't depend on whether extraction
> correctly nulled the field or the scoring call happened to notice the
> ambiguity text.

**5. How close were your top two candidates?** If they were within 0.05, say
what you would tell the committee and what you would change in the extraction
to make that call defensible.

> Not close in this run: story-01 at 4.20 versus story-04 at 3.30, a gap of
> 0.90 - roughly a fifth of the total scale - so this particular ranking
> does not turn on a coin-flip-sized margin. If it had landed within 0.05, I
> would tell the committee the rubric cannot responsibly separate the two
> and that the deciding factor is likely inside the scoring noise rather
> than a real difference in the underlying records; I would also want the
> extraction itself to be more precise before trusting any such close call -
> in particular, `relevant_experience_months` and `published_outputs_count`
> are already exact counted integers (good), but `academic`/`research`/
> `experience` scores are still a single 0-5 judgement call each, with no
> sub-criteria to see *why* two candidates landed at the same number - and,
> per question 4 above, I'd also want proof that any contradiction-driven
> score was actually enforced by code rather than by the model happening to
> notice it.

---

## Reflection (optional, one short paragraph)

Having now written a role prompt, compressed a conversation, and ranked six
extractions — what will you do differently the next time you build something
that has to get reliable structured output out of a model?

> The biggest surprise was how many failures showed up in the *base* case,
> before any role or trap was even involved. `policy_officer` - the role
> with the least discretion, just "apply the rule exactly as written" - still
> invented a missing document for E-06 and got a plain `2.9 > 2.67`
> comparison backwards for E-10. `gpt-4o-mini` also missed half of a
> contradiction it was explicitly told to catch in Sublab Hard (story-06's
> GPA), while catching the other half of the same story's contradiction
> (graduation year) only in prose, not in the field it was supposed to null.
> None of these were prompt-wording problems I could have caught by reading
> the prompt more carefully - they only showed up by actually running the
> code and checking the output against the record, which is exactly the
> discipline this homework is about. Next time I would treat "the base
> model got the mechanical part right" as something to verify on every run,
> not assume once and move on to comparing roles - and for anything where a
> wrong answer is costly, I would compute the mechanical part (GPA
> thresholds, document checks, contradiction-driven score floors) in code
> and let the model touch only the parts that are genuinely a judgement
> call, rather than trusting it to get arithmetic and record-reading right
> just because the prompt stated the rule clearly.
