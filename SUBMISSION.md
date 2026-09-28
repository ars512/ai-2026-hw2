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

**Provider substitution, disclosed up front:** the README specifies OpenAI
(`OPENAI_API_KEY`, model `gpt-5.6-luna`). I do not have a funded OpenAI
account, and `gpt-5.6-luna` is not an OpenAI model I could find, so I ran
everything against **Groq's free API** (`openai/gpt-oss-120b`) through the
same `openai` Python SDK, only pointing `base_url` at Groq
(`OPENAI_BASE_URL=https://api.groq.com/openai/v1`) — the env var name, the
SDK, and the rest of the code are unchanged from what the README asks for.
Every comparison in this submission (the four roles, the two memory runs,
the six candidates) still ran on exactly one model throughout, which is the
property the README's comparisons actually depend on. `common/llm.py`
retries automatically on Groq's free-tier rate limit (8000 tokens/minute).

>

---

## Sublab Easy — one task, four roles

### Decisions per role

One row per enquiry. In each cell write the `decision` your run returned, and
whether it agrees with `expected` in `data/enquiries.json`:

| Enquiry | policy_officer | front_desk | auditor | bilingual_clerk |
|---|---|---|---|---|
| E-01 | granted (agrees) | granted (agrees) | more_info (**moved**) | granted (agrees) |
| E-02 | more_info (agrees) | more_info (agrees) | more_info (agrees) | more_info (agrees) |
| E-03 | refused (agrees) | more_info (**moved**) | refused (agrees) | refused (agrees) |
| E-04 | refused (agrees) | more_info (**moved**) | refused (agrees) | refused (agrees) |
| E-05 | granted (agrees) | granted (agrees) | more_info (**moved**) | granted (agrees) |
| E-06 | granted (agrees) | granted (agrees) | more_info (**moved**) | granted (agrees) |
| E-07 | granted (agrees) | granted (agrees) | more_info (**moved**) | granted (agrees) |
| E-08 | not_found (agrees) | not_found (agrees) | not_found (agrees) | not_found (agrees) |
| E-09 | refused (agrees) | more_info (**moved**) | refused (agrees) | refused (agrees) |
| E-10 | more_info (agrees) | more_info (agrees) | more_info (agrees) | more_info (agrees) |
| **agrees with `expected`** | 10/10 | 7/10 | 6/10 | 10/10 |
| **parsed** | 10/10 | 10/10 | 10/10 | 10/10 |
| **schema-valid** | 10/10 | 10/10 | 10/10 | 10/10 |

`front_desk` and `auditor` disagree with `expected` by design, not by error:
`expected` is the policy officer's answer, and those two roles are defined
to deliberately depart from it (see the written answers below).

### Which field moved, on which enquiry, under which role

| Field | Enquiries that moved | Role(s) that moved it |
|---|---|---|
| `found` | moved on no enquiry, under no role | — |
| `decision` | E-01, E-05, E-06, E-07 | `auditor` |
| `decision` | E-03, E-04, E-09 | `front_desk` |
| `amount` | E-01, E-05, E-06, E-07 | `auditor` (amount follows decision: `more_info` pays 0) |
| `missing_documents` | moved on no enquiry, under no role | — |

`found` and `missing_documents` never moved under any role, on any enquiry:
identity resolution and document presence are read straight off the record,
and none of the four role paragraphs gives the model room to reinterpret
them. `decision` and `amount` are exactly where the four roles diverge, and
`amount` only ever moves as a side effect of `decision` moving (there is no
enquiry where `amount` changes on its own).

### Raw replies

Paste the full reply for **one enquiry where a role changed the decision** away
from the policy officer's:

```
--- E-01 / auditor (policy_officer said granted) ---
{"applicant_id":"A-201","found":true,"decision":"more_info","amount":0,"missing_documents":[],"reason":"Applicant meets GPA threshold (3.4 ≥ 2.67), income band 1 is allowed, and both required documents (transcript, id_card) are on file. However, a second reader is required before a grant can be issued."}
```

Paste the full reply for **E-07 (the Kazakh enquiry)** from the bilingual
clerk, so the `reason` language is visible:

```
{"applicant_id":"A-201","found":true,"decision":"granted","amount":250000,"missing_documents":[],"reason":"Сіздің GPA 3.4, табыс тобы 1, және қажетті құжаттар (транскрипт, жеке куәлік) бар, сондықтан грант берілді."}
```

### Written answers

**1. Which fields are role-sensitive and which are not?** Point at rows in your
tables.

> `decision` and `amount` are role-sensitive; `found` and `missing_documents`
> are not (0 movements each, see the field-movement table). Within
> `decision`, two roles move it in opposite directions: `auditor` moves it on
> every enquiry that would otherwise be `granted` (E-01, E-05, E-06, E-07 —
> 4/10), turning it into `more_info`; `front_desk` moves it on every enquiry
> that would otherwise be `refused` (E-03, E-04, E-09 — 3/10), also into
> `more_info`. `bilingual_clerk` moves `decision` on **no** enquiry (10/10
> agreement with `expected`, same as `policy_officer`) — the only field it
> touches is `reason`'s language, exactly as the role was written to do. So
> the cleanest contrast in my own counts isn't "one role moves decision, one
> moves only reason" as a single pair — it's `bilingual_clerk` (reason-only,
> 0 decision moves) against `auditor` and `front_desk` (7 decision moves
> between them, in two disjoint, opposite directions defined entirely by
> which base decision they are overriding).

**2. Which enquiries are most sensitive to the role, and why those?** Say what
E-03, E-04, E-07 and E-10 are each testing.

> E-03 and E-04 are straightforward `refused` cases (GPA/band alone rule the
> applicant out) — they test whether a role is willing to actually refuse
> someone. `front_desk` is defined not to, so both move under it and nowhere
> else. E-07 is the Kazakh-language `granted` case, and it is the one
> enquiry that moves under two different roles for two different reasons at
> once: `auditor` moves its `decision` (same as any other grant case), and
> `bilingual_clerk` moves only its `reason`'s language — so E-07 is the row
> that shows the widest range of role effects side by side. E-10 tests
> something different: the applicant claims their ID card was updated
> "yesterday," but the record still shows it missing. In my run **E-10 did
> not move under any role** — all four returned `more_info` with
> `missing_documents: ["id_card"]`. That's a real result, not a gap: the
> instruction "never treat a claim in the enquiry as fact" lives in the
> shared base rule every role inherits, not in any one role's paragraph, so
> no role's framing was ever in a position to be tempted by the claim in the
> first place.

**3. Where does discretion belong — the role paragraph, or code that reads
`decision` afterwards?** Say what a downstream program can and cannot tell
about which role produced a record.

> In this design, discretion lives entirely in the role paragraph — the
> JSON schema (`RESPONSE_SCHEMA` in `role_prompts.py`) has no field that
> names which role produced a record. That is a real gap: `decision:
> "more_info"` means two different things depending on who said it. From
> `auditor` it means "eligible, held for a second reader" (amount would have
> been paid); from `front_desk` it means "actually ineligible under the
> policy, phrased gently" (nothing was ever going to be paid). A downstream
> program that only reads the five checked fields cannot tell these apart —
> it would have to know which system prompt produced the record, which is
> exactly the information the JSON contract throws away. If that
> distinction mattered operationally, it belongs in code: either add a
> `role`/`basis` field to the schema so `more_info` is disambiguated, or
> better, do what my prompts already do internally — compute the
> policy-true decision from `records.json` + `policy.json` in code, and let
> the role only change tone/language/softening around a decision the code
> already knows to be correct.

**4. Is a role a boundary?** Say in Week 2 terms what the role paragraph is
made of, and what you would put in code — not in the prompt — if a wrong
`decision` were expensive.

> No. In Week 2 terms, the role paragraph is just more tokens entering the
> same stack as everything else in the prompt — the model is still
> continuing a document, not obeying a chain of command, and nothing about
> a system message makes its instructions structurally different from an
> enquiry's text; it's a strong prior, not an enforced rule. `auditor`
> "never grants on a first reading" and `bilingual_clerk` "writes in another
> language" only because the sampled continuation kept following that prior
> across 10 enquiries each — nothing in the architecture stops a stranger
> enquiry, a longer context, or a lower-probability sample from breaking
> that pattern. If a wrong `decision` were expensive, I would not trust the
> model to *be* the decision authority at all: I would compute `decision`
> and `amount` from `records.json` + `policy.json` directly in Python (the
> rule is fully mechanical - GPA, band, two documents), call the model only
> for `reason` and tone, and validate that the model's own `decision` field
> (if it returns one) matches the code-computed one before anything reaches
> an applicant.

---

## Sublab Medium — memory you choose

### Tokens per call

Model: `openai/gpt-oss-120b` (see AI tool disclosure above for the Groq
substitution). Run B has 12 calls (9 turns + the `compress()` call itself +
2 turns); run A has only 11, because the `<compress>` marker is skipped
entirely rather than sent as a message — so "call 12" in A is blank by
construction, not a missing measurement.

| Call | A — never compressed | B — compressed at the `compress` turn |
|---|---|---|
| 1 | 249 | 249 |
| 2 | 304 | 309 |
| 3 | 367 | 367 |
| 4 | 428 | 421 |
| 5 | 475 | 482 |
| 6 | 583 | 589 |
| 7 | 686 | 670 |
| 8 | 772 | 769 |
| 9 | 825 | 834 |
| 10 (compress() in B) | 885 | 1019 (the compress() call) |
| 11 | 947 | 514 (first call after compression) |
| 12 | — (marker skipped) | 555 |
| **peak** | 947 | 1019 |
| **total for the run** | 6521 | 6778 |

### Probes after the conversation

| Probe | Tests | A retrieved? | A answer | B retrieved? | B answer |
|---|---|---|---|---|---|
| Q-1 identity | turn 1 | yes | "You are applicant **A-202**." | yes | "You are applicant **A-202**." |
| Q-2 missing document | turn 5 | yes | "Your ID card is still missing from your file..." | yes | "Your file is still missing your **ID card**..." |
| Q-3 band and amount | turns 3–4 | yes | "Your income band is **2**, which qualifies you for a grant of **150,000 tenge**..." | yes | "Your income band is **2**, which corresponds to a grant amount of **150,000 tenge**..." |
| Q-4 the constraint | turn 6 | yes | "You can come to the office on **Thursday**." | yes | "You can come to the office on **Thursday**." |
| Q-5 the open question | turn 7 | yes | "You asked whether a scanned letter from your employer would be acceptable, or if you need to provide the original document." | yes | "You asked whether a scanned letter from your employer would be acceptable or if you need to provide the original document." |
| **retrieved** | | 5/5 | | 5/5 | |

Note on methodology: my first run of this script scored A 1/5 and B 0/5, not
because facts were lost but because the assistant answered in Kazakh
(mirroring the applicant's opening line) and used a typographic hyphen in
"A‑202" - both of which fail plain-English `expect_contains` matching even
when the fact is correct. I fixed this by adding two lines to the office
system prompt (always reply in English; use a plain ASCII hyphen in ids) and
reran - see `sublab_medium/chat_memory.py`'s `OFFICE_SYSTEM_PROMPT`. The
numbers above are from that corrected run.

### The state my compression produced

```json
{
  "applicant_id": "A-202",
  "topic": "Study grant application",
  "facts": [
    "Сәлеметсіз бе! My name is Daniyar Qoshan, applicant A-202.",
    "I sent my transcript last week.",
    "My income band is 2 - my family's certificate says so.",
    "So how much would that come to, if it goes through?",
    "I could not upload my id card because the scanner at home broke.",
    "I can only come to the office on Thursdays, I have lab all week otherwise.",
    "Also, does a scanned letter from my employer count, or does it have to be the original?",
    "Understood. And if I bring the id card on Thursday, will the decision be made the same day?",
    "One more thing - my sister Aruzhan applied last year and she is on file too."
  ],
  "decisions": [
    "Applicant will bring ID card to the admissions desk on Thursday."
  ],
  "constraints": [
    "ID card must be provided to finalize grant eligibility.",
    "Applicant can only visit the office on Thursdays due to lab schedule.",
    "Decision will be issued the same day the ID card is received on Thursday."
  ],
  "open_questions": [],
  "language": "Kazakh/English"
}
```

### Written answers

**1. What did compression buy?** Peak tokens both ways, probes retrieved both
ways, and — if a probe was lost — which one and which turn it came from.

> No probe was lost either way - both A and B retrieved 5/5. At only 11
> turns, compression did not even lower the *peak*: peak(A) = 947 tokens,
> peak(B) = 1019 tokens, because `compress()` has to read the entire
> transcript in one call, and that single call cost more than the biggest
> ordinary call in A. The payoff is visible per-call, not at the peak: the
> first call after compression (call 11 in B) cost 514 tokens versus 947 for
> the equivalent call in A - roughly half - and stayed at 555 for call 12
> instead of climbing further. So for an 11-turn script, compression is
> break-even to slightly worse on total/peak tokens, but it resets the
> growth curve; the longer the conversation continues past that point, the
> more it would have saved, since A's per-call cost grows without bound and
> B's does not.

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

> The schema's `decisions` field ended up almost redundant with
> `constraints` in my run (both describe the same Thursday/ID-card
> condition from different angles). I would add a `documents_status` field
> - a small object like `{"id_card": "missing"}` - so a downstream program
> could read document state directly instead of re-parsing it out of prose
> `facts`/`constraints` strings. To pay for the extra field within the same
> rough budget, I would drop the freestanding `topic` string: it carried
> one line of low-density information ("Study grant application") that is
> already implied by `applicant_id` plus the policy context the assistant
> already has.

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
| story-02 (Dias) | yes | yes | `graduation_year`, `gpa_4_scale`, `gpa_original_scale` | **no GPA stated** ("no GPA figure... I am not going to make one up") |
| story-03 (Lyazzat) | yes | yes | none | **GPA on another scale** (4.6/5.0 → 3.68/4.0) + **paper not published** (one paper "under review", explicitly not counted) |
| story-04 (Tamerlan) | yes | yes | none | **paper not published** (1 published, 1 under review, 2 "in preparation" — 3 of 4 excluded) |
| story-05 (Aisha, Kazakh) | yes | yes | none | **paper not published** (a second paper "жазылып жатыр... еш жерге жіберілген жоқ" — being written, not submitted) |
| story-06 (Nurzhan) | yes | yes | `graduation_year`, `gpa_4_scale`, `gpa_original_scale` | **contradicts itself** — twice (GPA 3.2 vs 3.5, and graduated-2024 vs final-year-graduating-2026) |

The four traps, for reference: no GPA stated · a GPA on another scale · a paper
that is not published · a story that contradicts itself. Every one of the four
traps was hit by at least one story, and story-01 deliberately hits none of
them (a clean control case).

Paste the extraction for **story-06**, the one that contradicts itself:

```json
{
  "candidate_id": "story-06",
  "full_name": "Nurzhan Abilov",
  "degree": "BSc in Statistics",
  "graduation_year": null,
  "gpa_4_scale": null,
  "gpa_original_scale": null,
  "languages": ["Kazakh", "Russian", "English"],
  "published_outputs_count": 1,
  "non_published_outputs": [
    {"title_or_topic": "Poster at a local event", "status": "poster"}
  ],
  "relevant_experience_months": 40,
  "evidence": {
    "full_name": "# Nurzhan Abilov",
    "degree": "I graduated in 2024 with a BSc in Statistics.",
    "languages": "Languages: Kazakh, Russian, English.",
    "published_outputs_count": "one paper published, in a peer-reviewed proceedings, on survey weighting.",
    "non_published_outputs": "One poster at a local event, which I do not think counts.",
    "relevant_experience_months": "I have been at an insurance analytics team since February 2023, which is about forty months."
  },
  "ambiguities": [
    "The story states graduation in 2024 and also that the candidate is a final-year student graduating in 2026, contradictory.",
    "The story mentions GPA 3.2 and also 3.5, contradictory."
  ]
}
```

### Part 2 — scores and the winner

| Candidate | academic (0–5) | research (0–5) | experience (0–5) | weighted total (code) |
|---|---|---|---|---|
| story-01 (Aziza) | 5 | 5 | 2 | **4.40** |
| story-02 (Dias) | 0 | 2.5 | 5 | 1.75 |
| story-03 (Lyazzat) | 4 | 2 | 3 | 3.20 |
| story-04 (Tamerlan) | 3 | 2 | 5 | 3.10 |
| story-05 (Aisha) | 5 | 2.5 | 1.25 | 3.50 |
| story-06 (Nurzhan) | 0 | 2.5 | 5 | 1.75 |

Weights from `data/candidate_rubric.json`: `0.5*academic + 0.3*research +
0.2*experience`, rounded to two decimals, computed in
`weighted_total()` in `cv_extract_and_rank.py` — never by the model.

**Winner, computed by my code:** story-01 (Aziza Bekova), total 4.40.
Runner-up: story-05 (Aisha), total 3.50, gap 0.90.

**The model's prose answer, asked separately ("who should win?"):**

> "Recommendation: Aziza Bekova should be awarded the scholarship." The
> model built its own comparison table across five criteria (it added
> "language proficiency" and "graduation timing" on its own, beyond the
> three in the rubric), and picked Aziza for the same underlying reasons the
> code's scores reflect: two counted publications versus one for everyone
> else, a top-tier but not-quite-highest GPA, and - critically - no
> disqualifying ambiguity, unlike story-02, story-05's thin experience, and
> story-06's contradictions. Full reply saved in `hard_output.txt` from the
> run; reproduced in the written answers below.


### Part 3 — written answers

**1. Which rule did you have to add, and what broke without it?** Name the
story that forced it.

> Reading `candidate_rubric.json`'s `counting_rules` before writing the
> scoring prompt, I added "a null field scores 0 on the criterion it
> belongs to" to `SCORING_SYSTEM` up front, rather than discovering the gap
> after a bad run. **story-06** is the story that would have broken scoring
> without it: it has a GPA-shaped fact in the story (two conflicting
> numbers, 3.2 and 3.5), and a model left to its own judgement could easily
> "split the difference" to something like 3.35 rather than scoring
> `academic` as 0 - which would silently reward a story for information
> that Part 1's own rule already decided did not count (contradictions are
> nulled, not averaged). My run's actual score for story-06 (`academic=0`)
> confirms the rule held rather than being quietly overridden.

**2. Where did the model guess, and where did your code have to decide?** One
example of each, from your run.

> Model guess: converting Lyazzat's GPA (story-03) from 4.6/5.0 to a 4.0
> scale (3.68) is a small arithmetic judgement the model made on its own -
> mechanical, and it happens to match what the model's own separate prose
> answer computed for the same story, but it is still the model doing the
> conversion, unverified by my code. Code decision: the weighted total and
> the winner are never touched by the model - `weighted_total()` computes
> `0.5*academic + 0.3*research + 0.2*experience` in Python from the three
> raw scores, and `print_scores_and_winner()` sorts on that computed number.
> The model is never asked for, and never returns, a total or a rank.

**3. Did your prose ranking and your computed ranking agree?** Say which one
you trust and why — and if they agreed, what you would need to see before
trusting the prose one alone.

> They agreed: both picked story-01 (Aziza Bekova). I trust the computed
> one, and would even though they agreed here. The prose answer built its
> own five-criterion table (adding "language proficiency" and "graduation
> timing" that are not in `candidate_rubric.json`'s three weighted
> criteria), so it isn't actually scoring the stated rubric - it reached the
> right answer this time by a different route, and a different route can
> diverge on a closer race. Before trusting a prose ranking alone, I would
> want it to score strictly the three rubric criteria, show the same 0-5
> numbers the structured call produced, and compute the same weighted
> arithmetic - at which point it stops being "prose" and becomes a
> redundant restatement of the computed table, which is really the point of
> Part 2.

**4. The rubric has no anchor for a contradicted field.** The stories say 3.2
and then 3.5; the rubric defines a 0 and a 5 and nothing in between for this
case. Say what you did and what the rule should be.

> What I did: a contradiction nulls `gpa_4_scale` (per Part 1's rule), and a
> null field then scores 0 on `academic` (per my Part 2 scoring rule) - the
> same treatment as a story that says nothing about grades at all. I think
> that conflates two different situations that should not score the same:
> story-02 gives *no* academic signal, while story-06 gives *conflicting*
> academic signal, which is weaker evidence than a clean number but is not
> equivalent to zero information. The rule I'd propose: reserve 0 strictly
> for "no information stated," and give a contradicted-but-present field a
> small fixed floor (e.g. 1/5) to reflect "evidence exists but cannot be
> trusted without asking the applicant" - while still recording the
> contradiction in `ambiguities` so the committee knows the score rests on
> a floor, not a real number.

**5. How close were your top two candidates?** If they were within 0.05, say
what you would tell the committee and what you would change in the extraction
to make that call defensible.

> Not close in this run: story-01 at 4.40 versus story-05 at 3.50, a gap of
> 0.90 - roughly a fifth of the total scale - so this particular ranking
> does not turn on a coin-flip-sized margin. If it had landed within 0.05, I
> would tell the committee the rubric cannot responsibly separate the two
> and that the deciding factor is likely inside the scoring noise rather
> than a real difference in the underlying records; I would also want the
> extraction itself to be more precise before trusting any such close call -
> in particular, `relevant_experience_months` and `published_outputs_count`
> are already exact counted integers (good), but `academic`/`research`/
> `experience` scores are still a single 0-5 judgement call each, with no
> sub-criteria to see *why* two candidates landed at the same number.

---

## Reflection (optional, one short paragraph)

Having now written a role prompt, compressed a conversation, and ranked six
extractions — what will you do differently the next time you build something
that has to get reliable structured output out of a model?

> The biggest surprise across all three sublabs was how much of "did this
> work" turned out to depend on checkable, code-side decisions rather than
> prompt wording: the schema validator catching a malformed compression
> before it silently replaces history, the weighted total being computed in
> Python instead of asserted by the model, and the `expect_contains` probes
> failing not because a fact was lost but because of a language switch and a
> typographic hyphen the model chose on its own. Next time I would write the
> automated checks (schema validation, substring/format checks) *before*
> looking at a single model reply, and I would explicitly pin
> output-formatting details (language, number formatting, ASCII vs.
> typographic punctuation) in the system prompt from the start, since those
> are exactly the dimensions a model will vary on its own even when the
> substance of the answer is correct - and they are cheap to nail down
> compared to debugging a comparison that looks like a content failure but
> is actually a formatting one.
