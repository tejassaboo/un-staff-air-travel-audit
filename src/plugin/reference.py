from slimconfig import build_output

from contract import ScenarioInput, UnAuditOutput
from plugin.fixtures import scenario, world
from plugin.rules import oracle


def compute_audit(given: ScenarioInput) -> UnAuditOutput:
    """The answer key: the one correct audit, from the handbook's rules over the bundled fixtures."""
    return build_output(oracle(world(), scenario(given.scenario.value)), UnAuditOutput)
