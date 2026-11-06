"""The verifier against hand-written submissions (no model): the brief's section 7 matrix. Correct,
incorrect, missing, consistency and verifier-caught malformed cases run through verify_task; shape
problems are refused by build_output before any verifier runs, exactly as in NanoAgent."""

import json

import pytest
from helpers import SCENARIOS, TASK, arguments, case, reference, verdict
from slimconfig import build_output

import verifier
from contract import UnAuditOutput

ORDER = [
    "reference-matches-oracle",
    "violations-unique",
    "violations-in-order",
    "compliant-matches-violations",
    "entitled-cabin-correct",
    "cabin-above-entitlement-correct",
    "route-exceeds-time-limit-correct",
    "route-not-least-costly-correct",
    "late-arrangement-correct",
    "late-request-above-economy-correct",
]
COLLECTOR = case("vienna-miles-collector")["expected"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_the_hand_written_answer_passes(scenario: str) -> None:
    result = verdict(scenario, case(scenario)["expected"])
    assert result["valid"] is True and result["score"] == 1.0, result["message"]
    assert [entry["id"] for entry in result["details"]["constraints"]] == ORDER
    assert all(entry["ok"] is True for entry in result["details"]["constraints"])


@pytest.mark.parametrize(
    ("scenario", "index"), [(scenario, index) for scenario in SCENARIOS for index in range(len(case(scenario)["broken"]))]
)
def test_each_broken_answer_fails_with_its_reason_code(scenario: str, index: int) -> None:
    broken = case(scenario)["broken"][index]
    result = verdict(scenario, {**case(scenario)["expected"], **broken["change"]})
    assert result["valid"] is False and 0.0 <= result["score"] < 1.0
    assert result["message"].split(":")[0] == broken["reason"], (broken["why"], result["message"])
    failing = [entry for entry in result["details"]["constraints"] if entry["ok"] is False]
    assert failing[0]["id"] == broken["reason"]
    assert "expected" in failing[0] and "actual" in failing[0]


def test_every_reason_code_is_exercised_by_a_case() -> None:
    reasons = {broken["reason"] for scenario in SCENARIOS for broken in case(scenario)["broken"]}
    assert reasons == set(ORDER) - {"reference-matches-oracle"}


@pytest.mark.parametrize(
    ("scenario", "change", "needles"),
    [
        ("nairobi-assembly-delegate", {"entitled_cabin": "business", "violations": [], "compliant": True}, ["539 min is not >= 540"]),
        ("vienna-ozone-workshop", {"entitled_cabin": "business", "violations": [], "compliant": True}, ["counts 650 min", "layovers [150]", "650 is not >= 660"]),
        ("mogadishu-field-mission", {"entitled_cabin": "business", "violations": [], "compliant": True}, ["parts count 360, 300 min", "over 720"]),
        ("beirut-donor-roundtable", {"violations": [], "compliant": True}, ["takes 450 min", "takes 210 min", "+240 is not < 240"]),
        ("amman-refugee-briefing", {"violations": ["ROUTE_EXCEEDS_TIME_LIMIT"], "compliant": False}, ["listed but not broken", "+239 is < 240"]),
        ("geneva-trade-forum", {"violations": [], "compliant": True}, ["15 days before departure", "15 is not >= 16"]),
        ("new-york-hlpf-panel", {"violations": [], "compliant": True}, ["request submitted 20 days", "20 is not >= 21"]),
        ("nairobi-interviewer", {"entitled_cabin": "business", "violations": [], "compliant": True}, ["a consultant travels economy"]),
        ("vienna-miles-collector", {"violations": ["CABIN_ABOVE_ENTITLEMENT", "LATE_ARRANGEMENT", "LATE_REQUEST_ABOVE_ECONOMY"]}, ["costs 112000 cents in economy", "costs 88100 cents"]),
    ],
)
def test_messages_name_the_rule_and_its_numbers(scenario: str, change: dict, needles: list) -> None:
    message = verdict(scenario, {**case(scenario)["expected"], **change})["message"]
    for needle in needles:
        assert needle in message, message


def test_a_failed_stage_leaves_later_stages_unchecked() -> None:
    result = verdict("vienna-miles-collector", {**COLLECTOR, "compliant": True})
    states = {entry["id"]: entry["ok"] for entry in result["details"]["constraints"]}
    assert states["compliant-matches-violations"] is False
    assert all(states[identifier] is None for identifier in ORDER[4:])


def test_a_message_counts_the_other_failures() -> None:
    result = verdict("vienna-miles-collector", {**COLLECTOR, "violations": [], "compliant": True})
    assert result["message"].startswith("cabin-above-entitlement-correct: CABIN_ABOVE_ENTITLEMENT missing")
    assert result["message"].endswith("(+3 more)")


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"violations": [], "compliant": False}, "compliant-matches-violations"),  # missing: nothing listed, not compliant
        ({"violations": ["LATE_ARRANGEMENT", "CABIN_ABOVE_ENTITLEMENT"]}, "violations-in-order"),
        ({"violations": ["LATE_ARRANGEMENT", "LATE_ARRANGEMENT"]}, "violations-unique"),
        ({"entitled_cabin": "business"}, "entitled-cabin-correct"),
        ({"violations": ["CABIN_ABOVE_ENTITLEMENT", "ROUTE_EXCEEDS_TIME_LIMIT", "ROUTE_NOT_LEAST_COSTLY", "LATE_ARRANGEMENT", "LATE_REQUEST_ABOVE_ECONOMY"]}, "route-exceeds-time-limit-correct"),
    ],
)
def test_incorrect_missing_and_inconsistent_answers(change: dict, reason: str) -> None:
    result = verdict("vienna-miles-collector", {**COLLECTOR, **change})
    assert result["valid"] is False and result["message"].split(":")[0] == reason, result["message"]


def test_a_wrong_answer_key_is_caught_before_the_submission() -> None:
    gold = build_output(case("kabul-mission-handover")["expected"], UnAuditOutput)
    wrong_key = build_output({**case("kabul-mission-handover")["expected"], "entitled_cabin": "economy"}, UnAuditOutput)
    result = verifier.verify_task(TASK, arguments("kabul-mission-handover"), gold, wrong_key, ".")
    assert result["valid"] is False and result["message"].startswith("reference-matches-oracle")
    assert result["score"] == 0.0 and result["details"]["score_breakdown"]["capped_by"] == ["reference-matches-oracle"]


# Partial credit: decisions right / decisions, where the decisions are the cabin, the compliant stamp and every
# code wanted or listed; a wrong cabin or an inconsistent slip caps it at 0.5. valid stays strict.
@pytest.mark.parametrize(
    ("scenario", "change", "score", "capped_by"),
    [
        # one of four flags missing: cabin, compliant and three codes right of six decisions
        ("vienna-miles-collector", {"violations": ["CABIN_ABOVE_ENTITLEMENT", "ROUTE_NOT_LEAST_COSTLY", "LATE_ARRANGEMENT"]}, 0.8333, []),
        # one flag listed in error on a one-flag trip: cabin, compliant and one code right of four
        ("nairobi-assembly-delegate", {"violations": ["CABIN_ABOVE_ENTITLEMENT", "LATE_ARRANGEMENT"]}, 0.75, []),
        # the only flag missing flips the stamp too: cabin right of three
        ("nairobi-assembly-delegate", {"violations": [], "compliant": True}, 0.3333, []),
        # a flag added to a compliant trip flips the stamp the same way: cabin right of three
        ("kabul-mission-handover", {"violations": ["LATE_ARRANGEMENT"], "compliant": False}, 0.3333, []),
        # wrong cabin, everything else right: 1/2 by count, capped at 0.5 anyway
        ("bangkok-disaster-drill", {"entitled_cabin": "economy"}, 0.5, ["entitled-cabin-correct"]),
        # wrong cabin with four flags right would count 5/6: the cap holds it at 0.5
        ("vienna-miles-collector", {"entitled_cabin": "business"}, 0.5, ["entitled-cabin-correct"]),
        # right content in the wrong order: capped at 0.5
        ("rome-food-security-summit", {"violations": ["ROUTE_NOT_LEAST_COSTLY", "ROUTE_EXCEEDS_TIME_LIMIT"]}, 0.5, ["violations-in-order"]),
        # right list, stamp disagrees: capped at 0.5
        ("vienna-miles-collector", {"compliant": True}, 0.5, ["compliant-matches-violations"]),
        # a repeat is graded as a set, then capped (a repeated list is also out of canonical order)
        ("geneva-trade-forum", {"violations": ["LATE_ARRANGEMENT", "LATE_ARRANGEMENT"]}, 0.5, ["violations-unique", "violations-in-order"]),
        # everything wrong on a business trip with a flag: 0 of three
        ("new-york-hlpf-panel", {"entitled_cabin": "economy", "violations": [], "compliant": True}, 0.0, ["entitled-cabin-correct"]),
    ],
)
def test_partial_scores(scenario: str, change: dict, score: float, capped_by: list) -> None:
    result = verdict(scenario, {**case(scenario)["expected"], **change})
    assert result["valid"] is False
    assert result["score"] == score, result["details"]["score_breakdown"]
    assert result["details"]["score_breakdown"]["capped_by"] == capped_by


def test_wrong_in_either_direction_costs_one_decision() -> None:
    # A missing flag and a flag listed in error each cost exactly one decision; when the list's emptiness changes,
    # the compliant stamp flips too, in either direction (0.3333 both ways in test_partial_scores).
    gold = case("rome-food-security-summit")["expected"]
    short = verdict("rome-food-security-summit", {**gold, "violations": ["ROUTE_EXCEEDS_TIME_LIMIT"]})
    long = verdict("rome-food-security-summit", {**gold, "violations": [*gold["violations"], "LATE_ARRANGEMENT"]})
    for result in (short, long):
        breakdown = result["details"]["score_breakdown"]
        assert breakdown["total"] - breakdown["right"] == 1 and breakdown["capped_by"] == []
    assert (short["score"], long["score"]) == (0.75, 0.8)  # 3 of 4 and 4 of 5 decisions right
    # The cabin wrong in either direction is the same cap.
    assert verdict("kabul-mission-handover", {**case("kabul-mission-handover")["expected"], "entitled_cabin": "economy"})["score"] == 0.5
    assert verdict("addis-ababa-budget-review", {**case("addis-ababa-budget-review")["expected"], "entitled_cabin": "business"})["score"] == 0.5


LAZY = [
    {"entitled_cabin": "economy", "violations": [], "compliant": True},
    {"entitled_cabin": "business", "violations": [], "compliant": True},
    {"entitled_cabin": "economy", "violations": [], "compliant": False},
    {"entitled_cabin": "economy", "violations": list(FLAGS := ["CABIN_ABOVE_ENTITLEMENT", "ROUTE_EXCEEDS_TIME_LIMIT", "ROUTE_NOT_LEAST_COSTLY", "LATE_ARRANGEMENT", "LATE_REQUEST_ABOVE_ECONOMY"]), "compliant": False},
    {"entitled_cabin": "business", "violations": FLAGS, "compliant": False},
]


def test_lazy_answers_stay_low() -> None:
    # An empty slip earns at most half anywhere it is not the gold answer (the wrong-cabin cap holds it there even
    # when the stamp is right by default); an everything-flagged slip clears half only on a trip that breaks two or
    # more rules (two of its seven decisions are then right by the flags alone); every lazy family averages under
    # 0.35 over the scenarios where it is not the gold answer.
    for lazy in LAZY:
        scores = []
        for scenario in SCENARIOS:
            gold = case(scenario)["expected"]
            if lazy == gold:
                continue
            result = verdict(scenario, lazy)
            assert result["valid"] is False, (scenario, lazy)
            if not lazy["violations"] or len(gold["violations"]) < 2:
                assert result["score"] <= 0.5, (scenario, lazy, result["score"])
            scores.append(result["score"])
        assert sum(scores) / len(scores) < 0.35, (lazy, sorted(scores))


def test_another_scenarios_answer_is_never_valid_and_scores_below_one() -> None:
    for scenario in SCENARIOS:
        for other in SCENARIOS:
            if case(other)["expected"] != case(scenario)["expected"]:
                result = verdict(scenario, case(other)["expected"])
                assert result["valid"] is False and result["score"] < 1.0


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_valid_means_every_decision_is_right(scenario: str) -> None:
    result = verdict(scenario, case(scenario)["expected"])
    breakdown = result["details"]["score_breakdown"]
    assert result["valid"] is True and result["score"] == 1.0
    assert breakdown["right"] == breakdown["total"] and breakdown["capped_by"] == []


def test_without_a_pinned_reference_the_oracle_still_decides() -> None:
    gold = case("kabul-mission-handover")["expected"]
    assert verdict("kabul-mission-handover", gold, pinned=False)["valid"] is True
    assert verdict("kabul-mission-handover", {**gold, "entitled_cabin": "economy"}, pinned=False)["valid"] is False


@pytest.mark.parametrize(
    "raw",
    [
        {**COLLECTOR, "compliant": "false"},  # a string for a bool
        {**COLLECTOR, "compliant": 0},
        {**COLLECTOR, "entitled_cabin": "Economy"},  # wrong case
        {**COLLECTOR, "entitled_cabin": "premium_economy"},  # not a cabin of this policy
        {**COLLECTOR, "violations": ["LATE_BOOKING"]},  # unknown code
        {**COLLECTOR, "violations": "LATE_ARRANGEMENT"},  # a string, not a list
        {**COLLECTOR, "violations": None},  # null for a required list
        {key: value for key, value in COLLECTOR.items() if key != "compliant"},  # missing field
        {**COLLECTOR, "rationale": "late on both dates"},  # extra free-text field
        ["economy", [], True],  # not an object
    ],
)
def test_malformed_outputs_are_refused_before_the_verifier(raw) -> None:
    with pytest.raises(ValueError):
        build_output(raw, UnAuditOutput)


def test_non_json_output_never_parses() -> None:
    with pytest.raises(json.JSONDecodeError):
        json.loads("{entitled_cabin: economy, compliant: yes}")


@pytest.mark.parametrize(
    ("arguments_value", "output_value"),
    [(None, None), ("nonsense", 7), (arguments("kabul-mission-handover"), None), (arguments("kabul-mission-handover"), {"compliant": True})],
)
def test_the_verifier_never_raises(arguments_value, output_value) -> None:
    result = verifier.verify_task(TASK, arguments_value, output_value, None, ".")
    assert result["valid"] is False and result["message"].startswith("verifier-error")


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_verdicts_are_deterministic_plain_json(scenario: str) -> None:
    broken = {**case(scenario)["expected"], **case(scenario)["broken"][0]["change"]}
    for output in (case(scenario)["expected"], broken):
        first, second = verdict(scenario, output), verdict(scenario, output)
        assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)  # no default=: plain JSON only
        assert isinstance(first["score"], float) and 0.0 <= first["score"] <= 1.0


def test_the_reference_tool_output_is_checked_against_the_oracle() -> None:
    good = verifier.verify_output("compute_audit", arguments("panama-hub-retreat"), reference("panama-hub-retreat"), ".")
    bad = verifier.verify_output("compute_audit", arguments("panama-hub-retreat"), reference("mogadishu-field-mission"), ".")
    assert good["valid"] is True and bad["valid"] is False
    assert verifier.verify_input("get_audit_case", arguments("panama-hub-retreat"))["valid"] is True


def test_an_unknown_task_or_tool_id_is_a_failed_verdict_not_an_exception() -> None:
    gold = build_output(case("kabul-mission-handover")["expected"], UnAuditOutput)
    for result in (
        verifier.verify_task("audit-trip", arguments("kabul-mission-handover"), gold, None, "."),
        verifier.verify_input("get_case", arguments("kabul-mission-handover")),
        verifier.verify_output("get_case", None, None, "."),
    ):
        assert result["valid"] is False and result["message"].startswith("verifier-error")
        json.dumps(result)


def test_an_unknown_scenario_is_a_failed_verdict_not_an_exception() -> None:
    gold = case("kabul-mission-handover")["expected"]
    result = verifier.verify_task(TASK, {"scenario": "atlantis-retreat"}, gold, None, ".")
    assert result["valid"] is False and result["message"].startswith("verifier-error")
