from slimconfig import build_output

from contract import AuditCaseOutput, ScenarioInput
from plugin.fixtures import scenario, world
from plugin.rules import audit_case


def get_audit_case(given: ScenarioInput) -> AuditCaseOutput:
    """The scenario's audit case: the request, the traveller, the dates, the proposal and every candidate
    itinerary. Facts only, never an answer."""
    return build_output(audit_case(world(), scenario(given.scenario.value)), AuditCaseOutput)
