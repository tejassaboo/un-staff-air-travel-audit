# UN Staff Air Travel Audit

A `nanoagent.plugin/v0001` plugin. A model audits one proposed United Nations official trip under a toy
handbook paraphrased from administrative instruction ST/AI/2013/3/Rev.1, "Official travel" (30 May 2024,
in force 1 July 2024). It rules on the traveller's entitled cabin, lists every rule the proposal breaks,
and says whether it complies. A deterministic Python verifier, with no LLM, checks the audit against an
oracle that it computes itself.

## Task

- **Input:** `ScenarioInput` with a single field, `scenario`, which names one of nineteen bundled
  proposed trips, for example `{"scenario": "kabul-mission-handover"}`.
- **Runner:** `agent`. The agent calls `get_audit_case`, then `submit`: two of the hosted six steps.
  The output is entirely Enum/bool, so a `decide` runner was the first design; it passes `inspect` and a
  scripted decide run (4 requests), but with the hosted 2,048-token reply cap the model's one answer
  batch, which must hold the whole audit, was cut off in both paid trials, so the task uses `agent`.
- **Output:** `UnAuditOutput`, all closed types:
  - `entitled_cabin`: `economy` or `business`;
  - `violations`: a list of `UnViolation` codes, each once, in the canonical order
    `CABIN_ABOVE_ENTITLEMENT`, `ROUTE_EXCEEDS_TIME_LIMIT`, `ROUTE_NOT_LEAST_COSTLY`, `LATE_ARRANGEMENT`,
    `LATE_REQUEST_ABOVE_ECONOMY`;
  - `compliant`: true exactly when `violations` is empty.
- **Success:** the audit equals the one audit the handbook's rules give.

The handbook is `src/plugin/data/handbook.md`. It is also the task's `instructions` in `nanoagent.yaml`, and a test keeps the two identical. It has the paraphrased in-scope rules, the "Clarifications (toy rules)" C1–C11, the rules not in scope, and the step plan.

Every fact the audit depends on is a typed field of `get_audit_case`'s output: the traveller category
and trip purpose (Enums), the request, booking and departure dates, the proposed itinerary and cabin, and
every candidate itinerary with its in-air, layover and elapsed minutes and its fares in integer cents.
`request_text` is the traveller's own voice, with distractors such as "my colleague always flies business
on this route". The answer never depends on it.

Each scenario sets one trap. Expected answers are hand-written in `tests/cases/`:

| Scenario | Trap | Entitled | Violations |
|---|---|---|---|
| `geneva-council-session` | Nonstop of exactly 540 min; a cheaper route fails the time rule | business | none |
| `nairobi-assembly-delegate` | Nonstop of 539 min, business proposed | economy | `CABIN_ABOVE_ENTITLEMENT` |
| `bangkok-statistics-keynote` | 220 + 80 + 360 = 660 combined | business | none |
| `addis-ababa-budget-review` | 360 + 80 + 219 = 659 combined, economy proposed | economy | none |
| `vienna-ozone-workshop` | A 150-min layover counts as 120: 300 + 120 + 230 = 650 | economy | `CABIN_ABOVE_ENTITLEMENT` |
| `panama-hub-retreat` | Two 110-min connections, capped per connection: 700 | business | none |
| `mogadishu-field-mission` | A 721-min stopover splits 360 and 300 | economy | `CABIN_ABOVE_ENTITLEMENT` |
| `kabul-mission-handover` | A 720-min stopover stays one part: 330 + 120 + 240 = 690 | business | none |
| `amman-refugee-briefing` | Cheaper connection +239 min over the nonstop | economy | none |
| `beirut-donor-roundtable` | Cheaper connection +240 min over the nonstop | economy | `ROUTE_EXCEEDS_TIME_LIMIT` |
| `nairobi-evaluation-consultant` | Consultant on an 840-min nonstop | economy | `CABIN_ABOVE_ENTITLEMENT` |
| `vienna-narcotics-commission` | Ticket issued exactly 16 days ahead | economy | none |
| `geneva-trade-forum` | Ticket issued 15 days ahead | economy | `LATE_ARRANGEMENT` |
| `bangkok-disaster-drill` | Business request submitted exactly 21 days ahead | business | none |
| `new-york-hlpf-panel` | Business request submitted 20 days ahead | business | `LATE_REQUEST_ABOVE_ECONOMY` |
| `santiago-training-faculty` | Training trip, but the traveller is the instructor | business | none |
| `bangkok-water-dialogue` | Late request, but economy proposed (voluntary downgrade) | business | none |
| `vienna-training-cohort` | Training participant, business via a pricier route, late on both dates | economy | `CABIN_ABOVE_ENTITLEMENT`, `ROUTE_NOT_LEAST_COSTLY`, `LATE_ARRANGEMENT`, `LATE_REQUEST_ABOVE_ECONOMY` |
| `rome-food-security-summit` | Loyalty routing via Istanbul, +315 min and pricier | business | `ROUTE_EXCEEDS_TIME_LIMIT`, `ROUTE_NOT_LEAST_COSTLY` |

## Tools

| Tool | Does | Code |
|---|---|---|
| `get_audit_case` | Returns a scenario's audit case: the traveller's words, the traveller, category and purpose, the request, booking and departure dates, the proposed itinerary and cabin, and every itinerary from origin to destination that day with segments, minutes and fares. It applies no policy | `src/plugin/audit.py` |
| `compute_audit` | The answer key: the oracle (`rules.oracle`) over the bundled fixtures. It is the task's `reference`, never shown to the model | `src/plugin/reference.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `audit-un-travel` | Audits a proposed UN official trip against the toy ST/AI/2013/3/Rev.1 air-travel handbook | `agent`, with `get_audit_case`; reference `compute_audit` |

## Environment

- Offline and self-contained. It uses `hosts: []`, an empty `.env`, and `write: []`, and has no clock. Every date is a scenario field.
- Fixtures are in `src/plugin/data/`: `airports.json`, `carriers.json` (fictional airlines), `segments.json` (local times, UTC times and `in_air_minutes` precomputed), `itineraries.json` (layover and elapsed minutes precomputed), `travelers.json`, and `scenarios/<id>.json`, which holds facts only and never an answer.
- Fixtures come from the seeded generator `src/plugin/tools_dev/generate.py`, which builds on `tools_dev/worldgen.py`. A test checks that the generator still reproduces the committed files byte for byte. The seed only scatters the itinerary ids.
- The shared core `src/plugin/world.py` (fixture schema and loader, date arithmetic, the search) is vendored byte-identical into `verifier/world.py`. The oracle `rules.py` is likewise byte-identical in `src/plugin/` and `verifier/`.
- Python 3.12 or later, with dependencies pinned by `uv.lock`.

## Verifier

`verifier/audit.py` reads the fixtures through `Path(__file__)`, computes the oracle with the shared `rules.py`, and checks the submission in four ordered stages. Each check has a stable reason code. The message names the first failing check with the rule and its numbers, for example `route-exceeds-time-limit-correct: ROUTE_EXCEEDS_TIME_LIMIT missing: I367 takes 450 min and the most direct route I905 takes 210 min: +240 is not < 240`. Later stages are skipped.

1. **Answer key:** `reference-matches-oracle`.
2. **Internal consistency:** `violations-unique`, `violations-in-order`, `compliant-matches-violations`. The output names no ids, so there is no referential-integrity stage.
3. **Decision against the oracle:** `entitled-cabin-correct`.
4. **Flags against the oracle**, one per code: `cabin-above-entitlement-correct`, `route-exceeds-time-limit-correct`, `route-not-least-costly-correct`, `late-arrangement-correct`, `late-request-above-economy-correct`.

How it scores:

- `violations` must follow the canonical order (the declaration order of `UnViolation`). Handbook C10, the field's description and the Enum all state it, so there is exactly one correct list; a wrong order fails `violations-in-order` and names the expected order.
- The score is 1.0 when the audit is right and 0.0 otherwise. `details` holds every constraint with expected and actual values, the expected audit, and the facts behind it, as plain JSON.
- Shape errors never reach the verifier, because NanoAgent's `build_output` refuses them first: a wrong type, an unknown Enum value, a missing or extra field, `null` for a required field.
- The verifier is pure stdlib and never raises, not even on an unknown task or tool id. An unexpected value becomes a `verifier-error` verdict.
- Tool outputs are also checked against the fixtures (`verify_output`).

## Validation

`tests/` covers the brief's test matrix:

- correct, incorrect, missing and malformed outputs, with malformed cases as `build_output` rejections;
- boundaries at 539/540 and 659/660 minutes, a 150-min layover, 720/721-min stopovers, +239/+240 min, 15/16 and 20/21 days, each on the oracle's own functions and as a scenario;
- consistency (`compliant` against `violations`, repeats, order) and uniqueness;
- oracle == the hand-written `tests/cases/<scenario>.json` for every scenario;
- the `rules.py` and `world.py` identity checks, handbook == `instructions`, generator reproducibility, fixture integrity (UTC times recomputed with `zoneinfo`);
- every policy fact is a typed field, and the answer does not change when `request_text` does;
- the brief's §11 cross-policy row for the UN, where 360 + 90 + 420 = 870 ≥ 660 gives business;
- a real MCP server round trip, tool-output size, and no answer leaking into the tool output;
- a scripted, no-LLM agent per scenario (`tests/scripted_agent.py`), written from the handbook alone: it follows the step plan within budget, its gold answer passes, and broken answers fail with the expected reason code.

## Layout

```text
.
├── nanoagent.yaml   # manifest: id, runtime, permissions, tools, the audit-un-travel task and its handbook instructions
├── contract.py      # typed inputs and outputs of every tool and the task (Enums, int minutes and cents)
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # empty: the plugin needs no environment variables
├── src/plugin/      # MCP server (__main__.py), tools, world.py (shared core), rules.py (oracle), fixtures
│   ├── data/        # handbook.md, the fixture JSON files and scenarios/
│   └── tools_dev/   # the seeded fixture generator (development only)
├── tests/           # verifier matrix, oracle cases, scripted agent, tools, fixtures
├── ui/              # renderers.js and renderers.css: the audit drawn as an approval slip
├── product/         # product.yaml and icon.svg
└── verifier/        # deterministic verifier: audit.py (task), case.py, rules.py, world.py
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run python -m plugin.tools_dev.generate   # rewrite the fixtures; the tests then check them
```

To run the agent, use `nanoagent plugin agent config=agent.yaml home=<run folder>` with `arguments` set to a JSON file such as `{"scenario": "kabul-mission-handover"}`. It needs `OPENROUTER_API_KEY` in the environment, not in this repo.
