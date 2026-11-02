from .checks import UNEXPECTED, compared, fixtures, plain, result
from .rules import audit_case


def verify_input(value):
    return result(True, "input is valid")  # a scenario Enum member is all the input there is


def verify_output(input_value, output_value, workspace):
    try:
        world, scenario = fixtures(plain(input_value)["scenario"])
        return compared("get_audit_case", plain(output_value), audit_case(world, scenario))
    except UNEXPECTED as error:
        return result(False, f"verifier-error: {error!r}")
