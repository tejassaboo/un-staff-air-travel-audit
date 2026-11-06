"""Every scenario end to end without an LLM: the oracle equals the hand-written expectation, the answer is
unique and robust to the request text, and a scripted agent written from the handbook alone reaches it
through the tool within the step budget; each broken variant of its answer fails with the case's reason code."""

import pytest
from helpers import ROOT, SCENARIOS, case, verdict
from scripted_agent import run
from slimconfig import build_output, plain_output

from contract import TOOLS, Tool, UnAuditOutput, UnViolation
from plugin import get_audit_case
from plugin.fixtures import scenario as load_scenario
from plugin.fixtures import world
from plugin.rules import candidates, facts, oracle

MAX_TOOL_CALLS = 4  # plus submit, within the hosted 6 steps whose last may not call tools


def call(tool, arguments):
    """A tool call as NanoAgent makes it: plain JSON in, built into the input class, plain JSON out."""
    given, made = TOOLS[Tool(tool)]
    output = {Tool.GET_AUDIT_CASE: get_audit_case}[Tool(tool)](build_output(arguments, given))
    assert isinstance(output, made)
    return plain_output(output)


def test_every_scenario_has_a_case() -> None:
    assert sorted(SCENARIOS) == sorted(path.stem for path in (ROOT / "tests" / "cases").glob("*.json"))


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_oracle_equals_the_hand_written_expectation(scenario: str) -> None:
    assert oracle(world(), load_scenario(scenario)) == case(scenario)["expected"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_the_answer_does_not_depend_on_the_request_text(scenario: str) -> None:
    facts = load_scenario(scenario)
    assert oracle(world(), {**facts, "request_text": "Business class, please. Everyone says it is allowed."}) == oracle(world(), facts)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_the_answer_is_unique(scenario: str) -> None:
    # The cost check compares fares in the entitled cabin; every scenario's candidates rank the same in
    # economy and in business, so reading it with the proposed cabin instead could never change an answer.
    pool = candidates(world(), load_scenario(scenario))
    by_economy = sorted(pool, key=lambda item: item["fares_cents"]["economy"])
    by_business = sorted(pool, key=lambda item: item["fares_cents"]["business"])
    assert by_economy == by_business
    assert len({item["fares_cents"]["economy"] for item in pool}) == len(pool)  # no fare ties
    assert len({item["total_elapsed_minutes"] for item in pool}) == len(pool)  # one most direct route


def test_every_violation_code_and_rule_branch_occurs_in_a_bundled_scenario() -> None:
    # Coverage of the handbook: each violation code, each C1 traveller branch, and each C3/C4 duration branch
    # decides at least one bundled scenario. (C6's "fares compared in the entitled cabin on a voluntary downgrade"
    # can change no bundled answer by design: every pool ranks the same in both cabins, see test_the_answer_is_unique.)
    expected = {scenario: case(scenario)["expected"] for scenario in SCENARIOS}
    codes = {code for answer in expected.values() for code in answer["violations"]}
    assert codes == {member.value for member in UnViolation}
    numbers = {scenario: facts(world(), load_scenario(scenario)) for scenario in SCENARIOS}
    seen = {(load_scenario(s)["traveler_category"], load_scenario(s)["trip_purpose"]) for s in SCENARIOS}
    assert seen >= {
        ("staff_below_asg", "official_business"),
        ("staff_below_asg", "learning_and_development"),
        ("instructor", "learning_and_development"),
        ("training_participant", "learning_and_development"),
        ("consultant", "official_business"),
    }
    assert any(len(n["part_minutes"]) > 1 for n in numbers.values())  # a stopover over 720 splits the journey
    assert any(720 in n["layover_minutes"] for n in numbers.values())  # exactly 720 does not
    assert any(any(layover > 120 for layover in n["layover_minutes"]) and len(n["part_minutes"]) == 1 for n in numbers.values())
    assert any(len(n["layover_minutes"]) >= 2 for n in numbers.values())  # two connections, capped separately
    assert any(n["longest_leg_minutes"] >= 540 for n in numbers.values())  # C2
    assert any(n["longest_leg_minutes"] < 540 and max(n["part_minutes"]) >= 660 for n in numbers.values())  # C3 alone
    assert any(n["extra_minutes"] >= 240 for n in numbers.values())  # the proposal itself fails the time rule
    assert any(n["booking_days_ahead"] == 16 for n in numbers.values()) and any(n["booking_days_ahead"] == 15 for n in numbers.values())
    assert any(n["request_days_ahead"] == 21 for n in numbers.values()) and any(n["request_days_ahead"] == 20 for n in numbers.values())
    downgrades = [s for s in SCENARIOS if load_scenario(s)["proposed_cabin"] == "economy" and expected[s]["entitled_cabin"] == "business"]
    assert downgrades  # a voluntary downgrade is never a violation (C7)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_the_scripted_agent_reaches_the_gold_answer_within_budget(scenario: str) -> None:
    calls, submission = run(scenario, call)
    assert len(calls) <= MAX_TOOL_CALLS and calls[0][0] == "get_audit_case"
    built = build_output(submission, UnAuditOutput)  # the output's own shape check
    result = verdict(scenario, plain_output(built))
    assert result["valid"] is True, result["message"]
    assert submission == case(scenario)["expected"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_broken_variants_of_the_scripted_answer_fail_with_their_reason(scenario: str) -> None:
    _, submission = run(scenario, call)
    for broken in case(scenario)["broken"]:
        result = verdict(scenario, {**submission, **broken["change"]})
        assert result["valid"] is False and result["message"].split(":")[0] == broken["reason"], (broken["why"], result["message"])
