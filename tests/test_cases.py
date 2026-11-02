"""Every scenario end to end without an LLM: the oracle equals the hand-written expectation, the answer is
unique and robust to the request text, and a scripted agent written from the handbook alone reaches it
through the tool within the step budget; each broken variant of its answer fails with the case's reason code."""

import pytest
from helpers import ROOT, SCENARIOS, case, verdict
from scripted_agent import run
from slimconfig import build_output, plain_output

from contract import TOOLS, Tool, UnAuditOutput
from plugin import get_audit_case
from plugin.fixtures import scenario as load_scenario
from plugin.fixtures import world
from plugin.rules import candidates, oracle

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
