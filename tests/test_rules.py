"""The oracle's rules at every threshold, exactly at the limit and one unit past it, on small synthetic
worlds, plus the brief's section 11 cross-policy row for the UN."""

import pytest

from plugin.rules import (
    counted_minutes,
    duration_entitles_business,
    entitled_cabin,
    journey_parts,
    oracle,
    violations,
)
from plugin.tools_dev.worldgen import itinerary, segment
from plugin.world import days_between

AIRPORTS = {
    code: {"code": code, "timezone": "UTC"} for code in ("GVA", "IST", "DOH", "NBO", "BKK")
}
CARRIERS = {"K2": {"code": "K2", "name": "Kestrel Airways", "us_flag_carrier": False}}
START = 8 * 60  # every synthetic journey leaves at 08:00 UTC on 2027-01-10


def stamp(minutes):
    day, rest = divmod(minutes, 1440)
    return f"2027-01-{10 + day:02d}T{rest // 60:02d}:{rest % 60:02d}"


def world_of(*specs):
    """A world with the given itineraries, each (id, [in-air minutes...], [layover minutes...], economy,
    business), all GVA -> ... -> BKK on 2027-01-10."""
    segments, itineraries = {}, {}
    stops = ["GVA", "IST", "DOH", "NBO", "BKK"]
    for itinerary_id, legs, layovers, economy, business in specs:
        clock, records = START, []
        route = [stops[0], *stops[1 : len(legs)], stops[-1]]
        for index, minutes in enumerate(legs):
            if index:
                clock += layovers[index - 1]
            record = segment(AIRPORTS, f"S{len(segments) + 1}", f"K2 {len(segments) + 1}", "K2", "K2", route[index], route[index + 1], stamp(clock), minutes)
            segments[record["segment_id"]] = record
            records.append(record)
            clock += minutes
        fares = {"economy": economy, "premium_economy": None, "business": business, "first": None}
        itineraries[itinerary_id] = itinerary(itinerary_id, records, fares)
    return {"airports": AIRPORTS, "carriers": CARRIERS, "segments": segments, "itineraries": itineraries, "travelers": {}}


def scenario(**facts):
    base = {
        "scenario": "synthetic",
        "request_text": "",
        "request_date": "2026-12-01",
        "booking_date": "2026-12-10",
        "traveler_id": "T0",
        "traveler_category": "staff_below_asg",
        "trip_purpose": "official_business",
        "origin": "GVA",
        "destination": "BKK",
        "departure_date": "2027-01-10",
        "proposed_itinerary_id": "X1",
        "proposed_cabin": "business",
    }
    return {**base, **facts}


def entitled(legs, layovers=(), category="staff_below_asg"):
    world = world_of(("X1", list(legs), list(layovers), 50000, 200000))
    return entitled_cabin(world, scenario(traveler_category=category))


@pytest.mark.parametrize(("minutes", "cabin"), [(539, "economy"), (540, "business"), (541, "business")])
def test_single_leg_539_vs_540(minutes: int, cabin: str) -> None:
    assert entitled([minutes]) == cabin


@pytest.mark.parametrize(("second", "cabin"), [(259, "economy"), (260, "business")])
def test_combined_659_vs_660(second: int, cabin: str) -> None:
    # 300 + min(100, 120) + second
    assert entitled([300, second], [100]) == cabin


def test_a_150_minute_layover_counts_as_120() -> None:
    world = world_of(("X1", [300, 230], [150], 50000, 200000))
    [part] = journey_parts(world, world["itineraries"]["X1"])
    assert counted_minutes(part) == 650 and world["itineraries"]["X1"]["total_elapsed_minutes"] == 680
    assert entitled([300, 230], [150]) == "economy"
    assert entitled([300, 240], [150]) == "business"  # 300 + 120 + 240 = 660


def test_the_cap_applies_to_each_connection() -> None:
    # 210 + 110 + 190 + 110 + 80 = 700; a single 2-hour cap for all connections would give 600.
    assert entitled([210, 190, 80], [110, 110]) == "business"


@pytest.mark.parametrize(("stopover", "parts", "cabin"), [(720, [690], "business"), (721, [330, 240], "economy")])
def test_stopover_720_vs_721(stopover: int, parts: list, cabin: str) -> None:
    world = world_of(("X1", [330, 240], [stopover], 50000, 200000))
    assert [counted_minutes(part) for part in journey_parts(world, world["itineraries"]["X1"])] == parts
    assert entitled([330, 240], [stopover]) == cabin


def test_a_qualifying_part_after_a_stopover_still_counts() -> None:
    assert entitled([200, 545], [800]) == "business"
    assert entitled([200, 330, 240], [800, 100]) == "business"  # second part 330 + 100 + 240 = 670


@pytest.mark.parametrize(
    ("category", "cabin"),
    [("staff_below_asg", "business"), ("instructor", "business"), ("consultant", "economy"), ("training_participant", "economy")],
)
def test_categories_on_a_14_hour_flight(category: str, cabin: str) -> None:
    assert entitled([840], category=category) == cabin


@pytest.mark.parametrize(("extra", "flagged"), [(239, False), (240, True)])
def test_route_239_vs_240(extra: int, flagged: bool) -> None:
    # X2 is the direct nonstop (300 min); X1 connects with 100 + layover + 100 = 300 + extra.
    world = world_of(("X1", [100, 100], [100 + extra], 40000, 150000), ("X2", [300], [], 60000, 220000))
    found = violations(world, scenario(proposed_cabin="economy"))
    assert ("ROUTE_EXCEEDS_TIME_LIMIT" in found) is flagged
    assert "ROUTE_NOT_LEAST_COSTLY" not in found  # the proposal is the cheapest of all


def test_a_cheaper_route_that_fails_the_time_rule_never_counts() -> None:
    world = world_of(("X1", [300], [], 60000, 220000), ("X2", [100, 100], [340], 40000, 150000))
    assert violations(world, scenario(proposed_cabin="economy")) == []
    world = world_of(("X1", [300], [], 60000, 220000), ("X2", [100, 100], [339], 40000, 150000))
    assert violations(world, scenario(proposed_cabin="economy")) == ["ROUTE_NOT_LEAST_COSTLY"]


def test_cost_is_compared_in_the_entitled_cabin() -> None:
    # Entitled business (600-min nonstop): the proposal's business fare is the higher one.
    world = world_of(("X1", [600], [], 50000, 260000), ("X2", [610], [], 55000, 240000))
    assert violations(world, scenario(proposed_cabin="business")) == ["ROUTE_NOT_LEAST_COSTLY"]


@pytest.mark.parametrize(("booking", "late"), [("2026-12-25", False), ("2026-12-26", True)])
def test_booking_16_vs_15_days(booking: str, late: bool) -> None:
    assert days_between(booking, "2027-01-10") == 16 - late
    world = world_of(("X1", [300], [], 50000, 200000))
    assert ("LATE_ARRANGEMENT" in violations(world, scenario(booking_date=booking, proposed_cabin="economy"))) is late


@pytest.mark.parametrize(
    ("submitted", "cabin", "flagged"),
    [("2026-12-20", "business", False), ("2026-12-21", "business", True), ("2026-12-21", "economy", False)],
)
def test_request_21_vs_20_days(submitted: str, cabin: str, flagged: bool) -> None:
    world = world_of(("X1", [600], [], 50000, 200000))
    facts = scenario(request_date=submitted, booking_date="2026-12-22", proposed_cabin=cabin)
    assert ("LATE_REQUEST_ABOVE_ECONOMY" in violations(world, facts)) is flagged
    assert entitled_cabin(world, facts) == "business"  # a late request never lowers the entitlement


def test_business_without_entitlement_and_a_late_request_gets_both_flags() -> None:
    world = world_of(("X1", [400], [], 50000, 200000))
    facts = scenario(request_date="2026-12-25", booking_date="2026-12-25", proposed_cabin="business")
    assert oracle(world, facts) == {
        "entitled_cabin": "economy",
        "violations": ["CABIN_ABOVE_ENTITLEMENT", "LATE_REQUEST_ABOVE_ECONOMY"],
        "compliant": False,
    }


def test_cross_policy_sanity_row_un() -> None:
    # Brief section 11: leg 1 = 360 in air, layover 90, leg 2 = 420 in air (elapsed 870): the UN gives business.
    world = world_of(("X1", [360, 420], [90], 90000, 310000))
    record = world["itineraries"]["X1"]
    assert (record["layover_minutes"], record["total_elapsed_minutes"]) == ([90], 870)
    assert duration_entitles_business(world, record)
    assert oracle(world, scenario()) == {"entitled_cabin": "business", "violations": [], "compliant": True}


def test_the_proposed_itinerary_must_be_a_candidate() -> None:
    with pytest.raises(ValueError, match="not among its candidates"):
        oracle(world_of(("X1", [300], [], 1, 2)), scenario(proposed_itinerary_id="X9"))
