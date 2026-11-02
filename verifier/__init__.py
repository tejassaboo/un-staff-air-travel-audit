"""The deterministic verifier: each tool's checks live in its own module, on contract instances."""

from contract import Task, Tool

from . import audit, case
from .checks import result

TOOLS = {Tool.GET_AUDIT_CASE: case, Tool.COMPUTE_AUDIT: audit}
# task -> its output's check, verify_task(arguments, output, reference, workspace)
TASKS = {Task.AUDIT_UN_TRAVEL: audit.verify_task}


# An id that is no contract member is a failed verdict, never an exception: a verifier that raises
# leaves the run with no verdict at all.
def verify_input(tool, value):
    try:
        module = TOOLS[Tool(tool)]
    except ValueError as error:
        return result(False, f"verifier-error: {error}")
    return module.verify_input(value)


def verify_output(tool, input_value, output_value, workspace):
    try:
        module = TOOLS[Tool(tool)]
    except ValueError as error:
        return result(False, f"verifier-error: {error}")
    return module.verify_output(input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    try:
        check = TASKS[Task(task)]
    except ValueError as error:
        return result(False, f"verifier-error: {error}")
    return check(arguments, output, reference, workspace)
