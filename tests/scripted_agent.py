"""A scripted agent with no LLM, written from the handbook (src/plugin/data/handbook.md) alone: it imports
nothing of the plugin's rules. It follows the step plan through a ``call(tool, arguments)`` function and
returns the submission it would make, so the tests and the evidence script can run each scenario end to end."""

from datetime import date


def days(start, end):
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def business_by_duration(itinerary):
    """C2-C4: a flight of >= 540 min, or a journey part counting >= 660 (each connection at most 120, a
    layover over 720 starts a new part)."""
    legs = [segment["in_air_minutes"] for segment in itinerary["segments"]]
    if max(legs) >= 540:
        return True
    part = legs[0]
    for layover, leg in zip(itinerary["layover_minutes"], legs[1:]):
        if part >= 660:
            return True
        part = leg if layover > 720 else part + min(layover, 120) + leg
    return part >= 660


def audit(case):
    """The audit the handbook gives for one get_audit_case output."""
    pool = {item["itinerary_id"]: item for item in case["itineraries"]}
    proposal = pool[case["proposed_itinerary_id"]]
    economy_only = case["traveler_category"] in ("consultant", "training_participant")
    entitled = "business" if not economy_only and business_by_duration(proposal) else "economy"
    direct = min(item["total_elapsed_minutes"] for item in pool.values())
    allowed = [item for item in pool.values() if item["total_elapsed_minutes"] - direct < 240]
    found = []
    if case["proposed_cabin"] == "business" and entitled == "economy":
        found.append("CABIN_ABOVE_ENTITLEMENT")
    if proposal not in allowed:
        found.append("ROUTE_EXCEEDS_TIME_LIMIT")
    if proposal["fares_cents"][entitled] > min(item["fares_cents"][entitled] for item in allowed):
        found.append("ROUTE_NOT_LEAST_COSTLY")
    if days(case["booking_date"], case["departure_date"]) < 16:
        found.append("LATE_ARRANGEMENT")
    if case["proposed_cabin"] == "business" and days(case["request_date"], case["departure_date"]) < 21:
        found.append("LATE_REQUEST_ABOVE_ECONOMY")
    return {"entitled_cabin": entitled, "violations": found, "compliant": not found}


def run(scenario, call):
    """(the tool calls made, in order, as (tool, arguments); the submission)."""
    calls = [("get_audit_case", {"scenario": scenario})]
    return calls, audit(call(*calls[-1]))
