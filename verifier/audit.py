"""The audit-un-travel verdict, and the checks of its reference tool compute_audit.

The verifier computes the correct audit itself (rules.oracle over the bundled fixtures) and checks the
submitted one against it in stages, each a list of constraints with stable ids (the reason codes):

0. answer key: the pinned reference equals the verifier's own oracle (else the plugin is broken);
1. internal consistency: no violation repeats, the list keeps the canonical order, and compliant is
   true exactly when the list is empty (the output names no ids, so there is no referential stage);
2. policy decision against the oracle: the entitled cabin;
3. flags against the oracle: each of the five violation codes, present exactly when it should be.

A stage is checked only when every earlier stage holds. The message names the first failing constraint,
with the rule and the numbers behind it, and how many more fail. Shape problems (types, Enum values,
missing or extra fields) never get here: NanoAgent's build_output refuses them first.

valid is strict: true only when every constraint holds. The score is partial credit in [0, 1] for how much
of the slip is right (``partial_score``): it counts the slip's decisions, which are the entitled cabin, the
compliant stamp, and every violation code that is either wanted or listed, and divides the right ones by
all of them. A missing flag and a flag listed in error each cost one decision (the compliant stamp flips
with the list's emptiness in either direction), so being wrong in either direction costs the same. Two
caps, both documented in the README: a wrong entitled cabin, the audit's primary ruling, caps the score at
0.5, and so does an inconsistent slip (a repeated code, a wrong order, or a compliant stamp that disagrees
with the list; the codes are then graded as a set). A broken answer key scores 0. An empty slip on a trip
with violations earns credit only for whatever it got right by default, so lazy answers stay low.
"""

from .checks import UNEXPECTED, fixtures, plain, result
from .rules import (
    ARRANGEMENT_DAYS,
    COMBINED_MIN,
    CONNECTION_CAP,
    ECONOMY_ONLY,
    REQUEST_DAYS,
    ROUTE_EXTRA_LIMIT,
    SINGLE_LEG_MIN,
    STOPOVER_OVER,
    TRAINING,
    VIOLATIONS,
    facts,
    oracle,
)

TEXT = {
    "reference-matches-oracle": "The pinned answer key equals the verifier's own oracle",
    "violations-unique": "No violation is listed twice",
    "violations-in-order": "Violations keep the canonical order of UnViolation (C10)",
    "compliant-matches-violations": "compliant is true exactly when violations is empty (C10)",
    "entitled-cabin-correct": "The entitled cabin follows C1-C5",
    "cabin-above-entitlement-correct": "CABIN_ABOVE_ENTITLEMENT is listed exactly when C7 applies",
    "route-exceeds-time-limit-correct": "ROUTE_EXCEEDS_TIME_LIMIT is listed exactly when C6 fails the route",
    "route-not-least-costly-correct": "ROUTE_NOT_LEAST_COSTLY is listed exactly when C6 finds a cheaper allowed route",
    "late-arrangement-correct": "LATE_ARRANGEMENT is listed exactly when C8 applies",
    "late-request-above-economy-correct": "LATE_REQUEST_ABOVE_ECONOMY is listed exactly when C9 applies",
}
FLAGS = {
    "cabin-above-entitlement-correct": "CABIN_ABOVE_ENTITLEMENT",
    "route-exceeds-time-limit-correct": "ROUTE_EXCEEDS_TIME_LIMIT",
    "route-not-least-costly-correct": "ROUTE_NOT_LEAST_COSTLY",
    "late-arrangement-correct": "LATE_ARRANGEMENT",
    "late-request-above-economy-correct": "LATE_REQUEST_ABOVE_ECONOMY",
}


def verify_input(value):
    return result(True, "input is valid")  # a scenario Enum member is all the input there is


def verify_output(input_value, output_value, workspace):
    try:
        world, scenario = fixtures(plain(input_value)["scenario"])
        key = oracle(world, scenario)
    except UNEXPECTED as error:
        return result(False, f"verifier-error: {error!r}")
    if plain(output_value) != key:
        return result(False, "compute_audit differs from the verifier's oracle", expected=key)
    return result(True, "the answer key matches the verifier's oracle")


def verify_task(arguments, output, reference, workspace):
    try:
        world, scenario = fixtures(plain(arguments)["scenario"])
        key = oracle(world, scenario)
        numbers = facts(world, scenario)
        pinned = None if reference is None else plain(reference)
        return judge(key, numbers, pinned, plain(output))
    except UNEXPECTED as error:
        return result(False, f"verifier-error: {error!r}")


def judge(key, numbers, pinned, given):
    stages = [
        [("reference-matches-oracle", lambda: reference_problem(key, pinned))],
        [
            ("violations-unique", lambda: unique_problem(given["violations"])),
            ("violations-in-order", lambda: order_problem(given["violations"])),
            ("compliant-matches-violations", lambda: compliant_problem(given)),
        ],
        [("entitled-cabin-correct", lambda: cabin_problem(key, numbers, given))],
        [(identifier, flag_check(identifier, key, numbers, given)) for identifier in FLAGS],
    ]
    constraints, blocked = [], None
    for stage in stages:
        for identifier, check in stage:
            if blocked is not None:
                constraints.append(entry(identifier, None, None, None, f"not checked: {blocked} failed"))
                continue
            problem = check()
            if problem is None:
                constraints.append(entry(identifier, True, None, None, ""))
            else:
                constraints.append(entry(identifier, False, *problem))
        failed = [item for item in constraints if item["ok"] is False]
        if failed and blocked is None:
            blocked = failed[0]["id"]
    failed = [item for item in constraints if item["ok"] is False]
    score, breakdown = partial_score(key, given, {item["id"] for item in failed})
    details = {"constraints": constraints, "expected": key, "facts": numbers, "score_breakdown": breakdown}
    if not failed:
        return result(True, f"the audit is right: {summary(given)}", score=1.0, **details)
    more = f" (+{len(failed) - 1} more)" if len(failed) > 1 else ""
    return result(False, f"{failed[0]['id']}: {failed[0]['message']}{more}", score=score, **details)


CONSISTENCY = ("violations-unique", "violations-in-order", "compliant-matches-violations")
CAP = 0.5  # the most a slip with the wrong cabin, or an inconsistent one, can score


def partial_score(key, given, failed):
    """(the score in [0, 1], its breakdown): the share of the slip's decisions that are right, capped."""
    wanted, listed = set(key["violations"]), set(given["violations"])
    decisions = [
        ("entitled_cabin", given["entitled_cabin"] == key["entitled_cabin"]),
        ("compliant", given["compliant"] == key["compliant"]),
        *((code, code in wanted and code in listed) for code in VIOLATIONS if code in wanted | listed),
    ]
    right = sum(1 for _, ok in decisions if ok)
    score = right / len(decisions)
    capped_by = []
    if "reference-matches-oracle" in failed:
        score, capped_by = 0.0, ["reference-matches-oracle"]
    else:
        if given["entitled_cabin"] != key["entitled_cabin"]:
            capped_by.append("entitled-cabin-correct")
        capped_by.extend(identifier for identifier in CONSISTENCY if identifier in failed)
        if capped_by:
            score = min(score, CAP)
    if not failed:
        score = 1.0
    return round(score, 4), {
        "decisions": [{"decision": name, "right": ok} for name, ok in decisions],
        "right": right,
        "total": len(decisions),
        "capped_by": capped_by,
    }


def entry(identifier, ok, expected, actual, message):
    return {"id": identifier, "constraint": TEXT[identifier], "ok": ok, "expected": expected, "actual": actual, "message": message}


def summary(audit):
    found = ", ".join(audit["violations"]) if audit["violations"] else "no violations, compliant"
    return f"entitled {audit['entitled_cabin']}; {found}"


def reference_problem(key, pinned):
    if pinned is not None and pinned != key:
        return key, pinned, "the pinned answer key differs from the verifier's oracle, so the plugin itself is broken"
    return None


def unique_problem(items):
    repeated = sorted({item for item in items if items.count(item) > 1})
    if repeated:
        return None, repeated, f"listed more than once: {', '.join(repeated)}"
    return None


def order_problem(items):
    canonical = [code for code in VIOLATIONS if code in items]
    if items != canonical:
        return canonical, items, f"violations must follow the order {', '.join(VIOLATIONS)}; got {', '.join(items)}"
    return None


def compliant_problem(given):
    if given["compliant"] != (given["violations"] == []):
        count = len(given["violations"])
        return given["violations"] == [], given["compliant"], (
            f"compliant is {str(given['compliant']).lower()} but {count} violation{'s' * (count != 1)} listed"
        )
    return None


def entitlement_reason(numbers):
    if numbers["traveler_category"] in ECONOMY_ONLY:
        return f"a {numbers['traveler_category']} travels economy whatever the duration (C1)"
    if numbers["trip_purpose"] == TRAINING and numbers["economy_only"]:
        return (
            f"a {numbers['traveler_category']} on {TRAINING} travel attends the training, not teaches it, so travels "
            f"economy whatever the duration (C1, section 4.3 (d))"
        )
    leg, parts = numbers["longest_leg_minutes"], numbers["part_minutes"]
    leg_text = f"longest single flight {leg} min is {'' if leg >= SINGLE_LEG_MIN else 'not '}>= {SINGLE_LEG_MIN}"
    best = max(parts)
    part_text = (
        f"journey part{'s count' if len(parts) > 1 else ' counts'} {', '.join(str(part) for part in parts)} min "
        f"(layovers {numbers['layover_minutes']}, each connection counts at most {CONNECTION_CAP}, "
        f"a stopover over {STOPOVER_OVER} starts a new part), and {best} is {'' if best >= COMBINED_MIN else 'not '}"
        f">= {COMBINED_MIN}"
    )
    return f"{numbers['proposed_itinerary_id']}: {leg_text}; {part_text}"


def cabin_problem(key, numbers, given):
    if given["entitled_cabin"] == key["entitled_cabin"]:
        return None
    return key["entitled_cabin"], given["entitled_cabin"], (
        f"entitled {given['entitled_cabin']} instead of {key['entitled_cabin']}: {entitlement_reason(numbers)}"
    )


def flag_reason(code, key, numbers):
    """The rule behind one violation code, with this scenario's numbers."""
    if code == "CABIN_ABOVE_ENTITLEMENT":
        return f"proposed {numbers['proposed_cabin']}, entitled {key['entitled_cabin']}"
    if code == "ROUTE_EXCEEDS_TIME_LIMIT":
        extra = numbers["extra_minutes"]
        return (
            f"{numbers['proposed_itinerary_id']} takes {numbers['proposed_elapsed_minutes']} min and the most direct route "
            f"{numbers['direct_itinerary_id']} takes {numbers['direct_minutes']} min: +{extra} is "
            f"{'' if extra < ROUTE_EXTRA_LIMIT else 'not '}< {ROUTE_EXTRA_LIMIT}"
        )
    if code == "ROUTE_NOT_LEAST_COSTLY":
        return (
            f"{numbers['proposed_itinerary_id']} costs {numbers['proposed_fare_cents']} cents in {key['entitled_cabin']}, "
            f"and the cheapest route the time rule allows costs {numbers['least_allowed_fare_cents']} cents"
        )
    if code == "LATE_ARRANGEMENT":
        days = numbers["booking_days_ahead"]
        return f"arrangements finalized {days} days before departure, and {days} is {'' if days >= ARRANGEMENT_DAYS else 'not '}>= {ARRANGEMENT_DAYS}"
    days = numbers["request_days_ahead"]
    return (
        f"proposed {numbers['proposed_cabin']}, request submitted {days} days before departure, and {days} is "
        f"{'' if days >= REQUEST_DAYS else 'not '}>= {REQUEST_DAYS}"
    )


def flag_check(identifier, key, numbers, given):
    code = FLAGS[identifier]

    def check():
        wanted, listed = code in key["violations"], code in given["violations"]
        if wanted == listed:
            return None
        verdict = "missing" if wanted else "listed but not broken"
        return wanted, listed, f"{code} {verdict}: {flag_reason(code, key, numbers)}"

    return check
