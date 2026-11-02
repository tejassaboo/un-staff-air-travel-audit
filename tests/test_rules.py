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


def test_a_consultant_proposing_business_late_breaks_three_rules() -> None:
    # C1 gives economy whatever the duration; C7 and C9 both apply because business was proposed (C9 extends
    # 3.3 (c) to every business proposal); C8 because the ticket is late too.
    world = world_of(("X1", [840], [], 50000, 200000))
    facts = scenario(traveler_category="consultant", request_date="2027-01-01", booking_date="2027-01-01")
    assert oracle(world, facts) == {
        "entitled_cabin": "economy",
        "violations": ["CABIN_ABOVE_ENTITLEMENT", "LATE_ARRANGEMENT", "LATE_REQUEST_ABOVE_ECONOMY"],
        "compliant": False,
    }


def test_an_entitled_late_request_in_economy_is_clean_but_in_business_is_flagged() -> None:
    world = world_of(("X1", [840], [], 50000, 200000))
    late = {"request_date": "2027-01-01", "booking_date": "2026-12-01"}
    assert violations(world, scenario(traveler_category="instructor", **late)) == ["LATE_REQUEST_ABOVE_ECONOMY"]
    assert violations(world, scenario(traveler_category="instructor", proposed_cabin="economy", **late)) == []


def test_two_stopovers_leave_three_parts_and_the_middle_one_can_qualify() -> None:
    world = world_of(("X1", [100, 330, 240, 100], [800, 100, 900], 50000, 200000))
    assert [counted_minutes(part) for part in journey_parts(world, world["itineraries"]["X1"])] == [100, 670, 100]
    assert entitled_cabin(world, scenario()) == "business"


def test_a_121_minute_connection_counts_as_120_and_no_wait_outside_the_flights_counts() -> None:
    world = world_of(("X1", [300, 240], [121], 50000, 200000))
    assert counted_minutes(journey_parts(world, world["itineraries"]["X1"])[0]) == 660
    assert entitled_cabin(world, scenario()) == "business"


def test_a_voluntary_downgrade_still_compares_fares_in_the_entitled_cabin() -> None:
    # Entitled business, economy proposed: X1 is the cheapest in economy but not in business (C6, section 4.4).
    world = world_of(("X1", [600], [], 50000, 260000), ("X2", [610], [], 55000, 240000))
    assert oracle(world, scenario(proposed_cabin="economy")) == {
        "entitled_cabin": "business",
        "violations": ["ROUTE_NOT_LEAST_COSTLY"],
        "compliant": False,
    }


def test_the_only_allowed_route_is_least_costly_whatever_a_disallowed_route_costs() -> None:
    world = world_of(("X1", [100, 100], [340], 40000, 150000), ("X2", [300], [], 60000, 220000))
    assert violations(world, scenario(proposed_itinerary_id="X2", proposed_cabin="economy")) == []
    assert violations(world, scenario(proposed_itinerary_id="X1", proposed_cabin="economy")) == ["ROUTE_EXCEEDS_TIME_LIMIT"]


@pytest.mark.parametrize(
    ("booking", "departure", "days"),
    [
        ("2027-02-13", "2027-03-01", 16),  # across a month end in a common year
        ("2028-02-13", "2028-02-29", 16),  # up to a leap day
        ("2028-02-14", "2028-03-01", 16),  # across a leap day
        ("2026-12-26", "2027-01-11", 16),  # across a year end
        ("2100-02-13", "2100-03-01", 16),  # 2100 is not a leap year
        ("2027-02-14", "2027-03-01", 15),
        ("2027-01-11", "2027-01-10", -1),  # a ticket issued after departure
    ],
)
def test_calendar_days_across_month_year_and_leap_boundaries(booking: str, departure: str, days: int) -> None:
    assert days_between(booking, departure) == days


def test_the_day_count_ignores_the_itinerary_clock() -> None:
    # Only the calendar dates matter: a 16-day gap across the year end is on time, 15 is late.
    world = world_of(("X1", [300], [], 50000, 200000))
    assert violations(world, scenario(booking_date="2026-12-25", proposed_cabin="economy")) == []
    assert violations(world, scenario(booking_date="2026-12-26", proposed_cabin="economy")) == ["LATE_ARRANGEMENT"]
