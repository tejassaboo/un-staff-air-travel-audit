"""The tools: what they return, how big their outputs are, and the real MCP server."""

import json
import sys

import anyio
import pytest
from helpers import ROOT, SCENARIOS
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from slimconfig import build_output, plain_output

import verifier
from contract import AuditCaseOutput, ScenarioInput
from plugin import get_audit_case

MAX_OUTPUT_CHARS = 4000  # about 1k tokens: the transcript stays far from the hosted 65,536-token budget


def case_of(scenario):
    return get_audit_case(build_output({"scenario": scenario}, ScenarioInput))


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_tool_output_matches_the_fixtures_and_stays_small(scenario: str) -> None:
    given = build_output({"scenario": scenario}, ScenarioInput)
    shown = case_of(scenario)
    assert verifier.verify_output("get_audit_case", given, shown, ".")["valid"] is True
    assert len(json.dumps(plain_output(shown))) <= MAX_OUTPUT_CHARS
    assert [item.itinerary_id for item in shown.itineraries] == sorted(item.itinerary_id for item in shown.itineraries)


def test_the_tool_shows_no_answer() -> None:
    text = json.dumps(plain_output(case_of("vienna-miles-collector")))
    for leak in ("entitled", "violation", "compliant", "CABIN_ABOVE", "LATE_"):
        assert leak not in text


def test_a_changed_tool_output_is_caught() -> None:
    given = build_output({"scenario": "kabul-mission-handover"}, ScenarioInput)
    changed = build_output({**plain_output(case_of("kabul-mission-handover")), "request_date": "2027-04-01"}, AuditCaseOutput)
    result = verifier.verify_output("get_audit_case", given, changed, ".")
    assert result["valid"] is False and "request_date" in result["message"]


def test_the_mcp_server_serves_every_tool() -> None:
    async def session():
        server = StdioServerParameters(command=sys.executable, args=["-m", "plugin"], cwd=str(ROOT))
        async with stdio_client(server) as (read, write), ClientSession(read, write) as client:
            await client.initialize()
            names = sorted(tool.name for tool in (await client.list_tools()).tools)
            answer = await client.call_tool("get_audit_case", {"scenario": "panama-hub-retreat"})
            refused = await client.call_tool("get_audit_case", {"scenario": "atlantis-retreat"})
            return names, answer, refused

    names, answer, refused = anyio.run(session)
    assert names == ["compute_audit", "get_audit_case"]
    assert answer.isError is False and answer.structuredContent["traveler_category"] == "staff_below_asg"
    assert len(answer.structuredContent["itineraries"]) == 3
    assert refused.isError is True
