"""The environment: the vendored copies stay identical, the handbook is the task's instructions, the
generator reproduces the committed fixtures, the fixtures hold their invariants (recomputed here with
zoneinfo, which the plugin itself never uses at evaluation time), and every policy fact is structured."""

import json
from datetime import date, datetime
from itertools import pairwise
from zoneinfo import ZoneInfo

import pytest
from helpers import DATA, ROOT, SCENARIOS

from plugin.fixtures import scenario as load_scenario
from plugin.fixtures import world
from plugin.rules import audit_case, candidates
from plugin.tools_dev.generate import build
from plugin.world import schema_problems

SCENARIO_KEYS = [
    "scenario",
    "request_text",
    "request_date",
    "booking_date",
    "traveler_id",
    "traveler_category",
    "trip_purpose",
    "origin",
    "destination",
    "departure_date",
    "proposed_itinerary_id",
    "proposed_cabin",
]


@pytest.mark.parametrize("module", ["rules.py", "world.py"])
def test_the_verifier_runs_the_same_code(module: str) -> None:
    assert (ROOT / "verifier" / module).read_bytes() == (ROOT / "src" / "plugin" / module).read_bytes()


def test_the_shared_core_is_vendored_unchanged() -> None:
    shared = ROOT.parent / "_shared_core"
    if not shared.is_dir():
        pytest.skip("the shared core lives next to the plugin only in the development workspace")
    assert (ROOT / "src" / "plugin" / "world.py").read_bytes() == (shared / "world.py").read_bytes()
    assert (ROOT / "src" / "plugin" / "tools_dev" / "worldgen.py").read_bytes() == (shared / "worldgen.py").read_bytes()


def instructions(manifest_text):
    """The audit-un-travel task's instructions: the `|-` block scalar under it, unindented."""
    lines = manifest_text.split("\n")
    start = lines.index("    instructions: |-") + 1
    block = []
    for line in lines[start:]:
        if line and not line.startswith("      "):
            break
        block.append(line[6:])
    return "\n".join(block).rstrip("\n")


def test_the_handbook_is_the_task_instructions() -> None:
    handbook = (DATA / "handbook.md").read_text(encoding="utf-8")
    assert instructions((ROOT / "nanoagent.yaml").read_text(encoding="utf-8")) == handbook.rstrip("\n")
    assert len(handbook.split()) <= 1500


def test_the_handbook_pins_its_source_and_states_the_toy_rules() -> None:
    handbook = (DATA / "handbook.md").read_text(encoding="utf-8")
    for needle in (
        "ST/AI/2013/3/Rev.1",
        "30 May 2024",
        "1 July 2024",
        "https://undocs.org/en/ST/AI/2013/3/Rev.1",
        "## Clarifications (toy rules)",
        "## Rules not in scope",
        "## Step plan",
        "section 5.5",
        '"should"',
        "≥ 540",
        "≥ 660",
        "over 720",
        "less than 240",
        "16 days",
        "21 days",
    ):
        assert needle in handbook, needle


def test_the_generator_reproduces_the_committed_fixtures() -> None:
    files = build()
    assert sorted(files) == sorted(path.relative_to(DATA).as_posix() for path in DATA.rglob("*.json"))
    for relative, text in files.items():
        assert (DATA / relative).read_text(encoding="utf-8") == text, relative


def test_the_fixtures_follow_the_schema() -> None:
    assert schema_problems(world()) == []


def local(stamp, timezone):
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M").replace(tzinfo=ZoneInfo(timezone))


def utc(stamp):
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%MZ").replace(tzinfo=ZoneInfo("UTC"))


def test_segment_times_are_consistent() -> None:
    airports = world()["airports"]
    for segment in world()["segments"].values():
        depart = local(segment["depart_local"], airports[segment["origin"]]["timezone"])
        arrive = local(segment["arrive_local"], airports[segment["destination"]]["timezone"])
        assert depart == utc(segment["depart_utc"]) and arrive == utc(segment["arrive_utc"]), segment["segment_id"]
        assert (arrive - depart).total_seconds() == segment["in_air_minutes"] * 60


def test_itinerary_totals_and_fares() -> None:
    data = world()
    for record in data["itineraries"].values():
        segments = [data["segments"][segment_id] for segment_id in record["segment_ids"]]
        layovers = [int((utc(b["depart_utc"]) - utc(a["arrive_utc"])).total_seconds() // 60) for a, b in pairwise(segments)]
        assert record["layover_minutes"] == layovers and record["connections"] == len(segments) - 1
        assert record["total_elapsed_minutes"] == sum(segment["in_air_minutes"] for segment in segments) + sum(layovers)
        fares = record["fares_cents"]
        assert fares["premium_economy"] is None and fares["first"] is None  # Rev.1 audits economy and business only
        assert isinstance(fares["economy"], int) and isinstance(fares["business"], int) and 0 < fares["economy"] < fares["business"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_scenario_files_hold_facts_only(scenario: str) -> None:
    facts = json.loads((DATA / "scenarios" / f"{scenario}.json").read_text(encoding="utf-8"))
    assert list(facts) == SCENARIO_KEYS and facts["scenario"] == scenario  # no expected answer anywhere
    assert facts["traveler_id"] in world()["travelers"]
    request, booking, departure = (date.fromisoformat(facts[key]) for key in ("request_date", "booking_date", "departure_date"))
    assert request <= booking < departure
    if facts["traveler_category"] in ("training_participant", "instructor"):
        assert facts["trip_purpose"] == "learning_and_development"  # a staff member may attend training too (C1)
    pool = candidates(world(), facts)
    assert 6 <= len(pool) <= 8 and facts["proposed_itinerary_id"] in [item["itinerary_id"] for item in pool]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_the_route_rule_is_a_real_search(scenario: str) -> None:
    # Several candidates pass the time rule, so the least costly one must be found among them, and at least one
    # fails it, so a cheaper route that never counts is on offer (C6).
    pool = candidates(world(), load_scenario(scenario))
    direct = min(item["total_elapsed_minutes"] for item in pool)
    allowed = [item for item in pool if item["total_elapsed_minutes"] - direct < 240]
    assert len(allowed) >= 3 and len(allowed) < len(pool)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_every_policy_fact_is_a_structured_field(scenario: str) -> None:
    # Everything the oracle reads from a scenario reaches the model as a typed field of get_audit_case:
    # request_text is flavour only (test_cases also checks the answer ignores it).
    facts, shown = load_scenario(scenario), audit_case(world(), load_scenario(scenario))
    for key in SCENARIO_KEYS:
        if key == "traveler_id":
            assert shown["traveler"]["traveler_id"] == facts[key]
        else:
            assert shown[key] == facts[key], key
    for item in shown["itineraries"]:
        record = world()["itineraries"][item["itinerary_id"]]
        assert item["layover_minutes"] == record["layover_minutes"]
        assert item["total_elapsed_minutes"] == record["total_elapsed_minutes"]
        assert [segment["in_air_minutes"] for segment in item["segments"]] == [
            world()["segments"][segment_id]["in_air_minutes"] for segment_id in record["segment_ids"]
        ]


def test_scenarios_never_share_a_search() -> None:
    searches = [(load_scenario(s)["origin"], load_scenario(s)["destination"], load_scenario(s)["departure_date"]) for s in SCENARIOS]
    assert len(set(searches)) == len(searches)


def test_gitignore_keeps_the_bundled_data() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").split()
    assert not any(pattern in ("*.json", "*.md", "data/", "src/") for pattern in ignored)


def test_the_handbook_labels_its_departures_from_the_source() -> None:
    handbook = (DATA / "handbook.md").read_text(encoding="utf-8")
    for needle in (
        "by analogy",  # the per-connection 2-hour cap borrows section 5.5, which governs rest periods
        "Section 4.3 (c) itself does not say so",
        "extends it to every business proposal",  # C9 reaches beyond 3.3 (c)'s "entitled" wording
        "origin local time",  # which day a candidate leaves on
        "every candidate offers both cabins",
        "section 4.4",  # fares compared in the entitled cabin even on a voluntary downgrade
    ):
        assert needle in handbook, needle
