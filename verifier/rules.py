"""ST/AI/2013/3/Rev.1 air-travel rules as this plugin's toy handbook states them (src/plugin/data/handbook.md):
the oracle that the reference tool and the verifier both run on the bundled fixtures.

Byte-identical in src/plugin/ and verifier/ (a test checks the two copies), so it keeps to the
verifier's pure-stdlib rules. Every function is a pure function of the fixtures and one scenario.
"""

from .world import days_between, itinerary_segments, search

SINGLE_LEG_MIN = 540  # C2: one flight of at least this many in-air minutes gives business
COMBINED_MIN = 660  # C3: a journey part of at least this many counted minutes gives business
CONNECTION_CAP = 120  # C3: at most this many minutes counted for each connection
STOPOVER_OVER = 720  # C4: ground time over this many minutes breaks the journey into parts
ROUTE_EXTRA_LIMIT = 240  # C6: a route is allowed while it takes fewer extra minutes than this
ARRANGEMENT_DAYS = 16  # C8: arrangements finalized at least this many days before departure
REQUEST_DAYS = 21  # C9: above-economy travel needs the request at least this many days before
ECONOMY_ONLY = ("consultant", "training_participant")  # C1: economy whatever the duration
# The canonical order of a violations list (C10), the order of contract.UnViolation.
VIOLATIONS = (
    "CABIN_ABOVE_ENTITLEMENT",
    "ROUTE_EXCEEDS_TIME_LIMIT",
    "ROUTE_NOT_LEAST_COSTLY",
    "LATE_ARRANGEMENT",
    "LATE_REQUEST_ABOVE_ECONOMY",
)


def candidates(world, scenario):
    """Every itinerary from the scenario's origin to its destination on its departure date, by id."""
    pool = search(world, [scenario["origin"]], scenario["destination"], scenario["departure_date"])
    if scenario["proposed_itinerary_id"] not in [itinerary["itinerary_id"] for itinerary in pool]:
        raise ValueError(f"scenario {scenario['scenario']}: the proposed itinerary is not among its candidates")
    return pool


def proposed(world, scenario):
    """The proposed itinerary, which must be one of the candidates."""
    candidates(world, scenario)
    return world["itineraries"][scenario["proposed_itinerary_id"]]


def journey_parts(world, itinerary):
    """The itinerary split at every stopover over STOPOVER_OVER minutes: [{"legs": [...], "connections": [...]}],
    each part's in-air minutes per flight and its ground minutes per connection."""
    segments = itinerary_segments(world, itinerary)
    parts = [{"legs": [segments[0]["in_air_minutes"]], "connections": []}]
    for layover, segment in zip(itinerary["layover_minutes"], segments[1:], strict=True):
        if layover > STOPOVER_OVER:
            parts.append({"legs": [segment["in_air_minutes"]], "connections": []})
        else:
            parts[-1]["connections"].append(layover)
            parts[-1]["legs"].append(segment["in_air_minutes"])
    return parts


def counted_minutes(part):
    """A journey part's combined travel time: its in-air minutes plus at most CONNECTION_CAP per connection."""
    return sum(part["legs"]) + sum(min(layover, CONNECTION_CAP) for layover in part["connections"])


def duration_entitles_business(world, itinerary):
    """A single flight of at least SINGLE_LEG_MIN minutes, or a journey part counting at least COMBINED_MIN."""
    parts = journey_parts(world, itinerary)
    longest = max(minutes for part in parts for minutes in part["legs"])
    return longest >= SINGLE_LEG_MIN or max(counted_minutes(part) for part in parts) >= COMBINED_MIN


def entitled_cabin(world, scenario):
    """The cabin the traveller is entitled to on the proposed itinerary."""
    if scenario["traveler_category"] in ECONOMY_ONLY:
        return "economy"
    return "business" if duration_entitles_business(world, proposed(world, scenario)) else "economy"


def direct_minutes(world, scenario):
    """The most direct route's time: the least total_elapsed_minutes among the candidates."""
    return min(itinerary["total_elapsed_minutes"] for itinerary in candidates(world, scenario))


def time_allowed(itinerary, direct):
    """The route takes fewer than ROUTE_EXTRA_LIMIT minutes more than the most direct route."""
    return itinerary["total_elapsed_minutes"] - direct < ROUTE_EXTRA_LIMIT


def least_allowed_fare(world, scenario, cabin):
    """The lowest fare in ``cabin`` among the candidates the time rule allows."""
    direct = direct_minutes(world, scenario)
    return min(item["fares_cents"][cabin] for item in candidates(world, scenario) if time_allowed(item, direct))


def violations(world, scenario):
    """Every rule the proposed trip breaks, in the canonical order."""
    entitled = entitled_cabin(world, scenario)
    itinerary = proposed(world, scenario)
    found = []
    if scenario["proposed_cabin"] == "business" and entitled == "economy":
        found.append("CABIN_ABOVE_ENTITLEMENT")
    if not time_allowed(itinerary, direct_minutes(world, scenario)):
        found.append("ROUTE_EXCEEDS_TIME_LIMIT")
    if itinerary["fares_cents"][entitled] > least_allowed_fare(world, scenario, entitled):
        found.append("ROUTE_NOT_LEAST_COSTLY")
    if days_between(scenario["booking_date"], scenario["departure_date"]) < ARRANGEMENT_DAYS:
        found.append("LATE_ARRANGEMENT")
    late_request = days_between(scenario["request_date"], scenario["departure_date"]) < REQUEST_DAYS
    if scenario["proposed_cabin"] == "business" and late_request:
        found.append("LATE_REQUEST_ABOVE_ECONOMY")
    return found


def oracle(world, scenario):
    """The one correct audit for ``scenario``, as the task output's plain JSON."""
    found = violations(world, scenario)
    return {"entitled_cabin": entitled_cabin(world, scenario), "violations": found, "compliant": not found}


def facts(world, scenario):
    """The numbers behind the audit, for the verifier's messages and details."""
    itinerary = proposed(world, scenario)
    entitled = entitled_cabin(world, scenario)
    direct = direct_minutes(world, scenario)
    pool = candidates(world, scenario)
    parts = journey_parts(world, itinerary)
    return {
        "proposed_itinerary_id": itinerary["itinerary_id"],
        "proposed_cabin": scenario["proposed_cabin"],
        "traveler_category": scenario["traveler_category"],
        "longest_leg_minutes": max(minutes for part in parts for minutes in part["legs"]),
        "part_minutes": [counted_minutes(part) for part in parts],
        "layover_minutes": list(itinerary["layover_minutes"]),
        "proposed_elapsed_minutes": itinerary["total_elapsed_minutes"],
        "direct_itinerary_id": next(item["itinerary_id"] for item in pool if item["total_elapsed_minutes"] == direct),
        "direct_minutes": direct,
        "extra_minutes": itinerary["total_elapsed_minutes"] - direct,
        "proposed_fare_cents": itinerary["fares_cents"][entitled],
        "least_allowed_fare_cents": least_allowed_fare(world, scenario, entitled),
        "booking_days_ahead": days_between(scenario["booking_date"], scenario["departure_date"]),
        "request_days_ahead": days_between(scenario["request_date"], scenario["departure_date"]),
    }


def audit_case(world, scenario):
    """The case get_audit_case shows: the scenario's facts, its traveller and every candidate itinerary."""
    carriers = world["carriers"]
    return {
        "scenario": scenario["scenario"],
        "request_text": scenario["request_text"],
        "traveler": {
            "traveler_id": scenario["traveler_id"],
            "name": world["travelers"][scenario["traveler_id"]]["name"],
            "department": world["travelers"][scenario["traveler_id"]]["department"],
            "duty_station": world["travelers"][scenario["traveler_id"]]["base_point"],
        },
        "traveler_category": scenario["traveler_category"],
        "trip_purpose": scenario["trip_purpose"],
        "origin": scenario["origin"],
        "destination": scenario["destination"],
        "departure_date": scenario["departure_date"],
        "request_date": scenario["request_date"],
        "booking_date": scenario["booking_date"],
        "proposed_itinerary_id": scenario["proposed_itinerary_id"],
        "proposed_cabin": scenario["proposed_cabin"],
        "itineraries": [
            {
                "itinerary_id": itinerary["itinerary_id"],
                "segments": [
                    {
                        "flight": segment["flight"],
                        "carrier": carriers[segment["marketing_carrier"]]["name"],
                        "origin": segment["origin"],
                        "destination": segment["destination"],
                        "depart_local": segment["depart_local"],
                        "arrive_local": segment["arrive_local"],
                        "in_air_minutes": segment["in_air_minutes"],
                    }
                    for segment in itinerary_segments(world, itinerary)
                ],
                "layover_minutes": list(itinerary["layover_minutes"]),
                "total_elapsed_minutes": itinerary["total_elapsed_minutes"],
                "fares_cents": {cabin: itinerary["fares_cents"][cabin] for cabin in ("economy", "business")},
            }
            for itinerary in candidates(world, scenario)
        ],
    }
