"""Structured input and structured output: every contract field is typed and described, every policy fact
reaches the agent in a typed field (never only in prose), and nothing the verifier grades is free text."""

import dataclasses
import typing
from enum import Enum

import contract
from contract import (
    AuditCaseOutput,
    Itinerary,
    Segment,
    TravelerCategory,
    TripPurpose,
    UnAuditOutput,
    UnCabin,
    UnViolation,
)

CONTRACT_CLASSES = [
    value
    for value in vars(contract).values()
    if isinstance(value, type) and dataclasses.is_dataclass(value) and value.__module__ == contract.__name__
]


def annotated_fields(cls):
    """(name, type, description) for every field, from the class's Annotated hints."""
    hints = typing.get_type_hints(cls, include_extras=True)
    for field in dataclasses.fields(cls):
        hint = hints[field.name]
        assert typing.get_origin(hint) is typing.Annotated, f"{cls.__name__}.{field.name} is not Annotated"
        base, *metadata = typing.get_args(hint)
        yield field.name, base, metadata[0]


def test_every_field_is_annotated_with_a_description() -> None:
    assert len(CONTRACT_CLASSES) >= 6
    for cls in CONTRACT_CLASSES:
        for name, _, description in annotated_fields(cls):
            assert isinstance(description, str) and len(description.split()) >= 3, f"{cls.__name__}.{name}"


def test_every_policy_fact_reaches_the_agent_in_a_typed_field() -> None:
    case = {name: base for name, base, _ in annotated_fields(AuditCaseOutput)}
    itinerary = {name: base for name, base, _ in annotated_fields(Itinerary)}
    segment = {name: base for name, base, _ in annotated_fields(Segment)}
    assert case["traveler_category"] is TravelerCategory and case["trip_purpose"] is TripPurpose
    assert case["proposed_cabin"] is UnCabin and case["proposed_itinerary_id"] is str
    assert case["request_date"] is str and case["booking_date"] is str and case["departure_date"] is str
    assert case["itineraries"] == list[Itinerary]
    assert itinerary["layover_minutes"] == list[int] and itinerary["total_elapsed_minutes"] is int
    assert itinerary["fares_cents"] == dict[UnCabin, int]  # int cents per cabin, never a float
    assert segment["in_air_minutes"] is int


def test_the_graded_output_has_no_free_text() -> None:
    fields = {name: base for name, base, _ in annotated_fields(UnAuditOutput)}
    assert fields == {"entitled_cabin": UnCabin, "violations": list[UnViolation], "compliant": bool}
    assert [member.value for member in UnViolation] == [
        "CABIN_ABOVE_ENTITLEMENT",
        "ROUTE_EXCEEDS_TIME_LIMIT",
        "ROUTE_NOT_LEAST_COSTLY",
        "LATE_ARRANGEMENT",
        "LATE_REQUEST_ABOVE_ECONOMY",
    ]  # the canonical order the verifier and the handbook (C10) enforce


def test_enums_are_closed_and_lower_case_or_codes() -> None:
    for cls in (TravelerCategory, TripPurpose, UnCabin):
        assert all(isinstance(member.value, str) and member.value == member.value.lower() for member in cls)
    assert all(member.value == member.name for member in UnViolation)
    assert issubclass(contract.UnScenario, Enum) and len(contract.UnScenario) == 23


def test_dates_and_stamps_say_their_format_and_amounts_their_unit() -> None:
    for cls in CONTRACT_CLASSES:
        for name, base, description in annotated_fields(cls):
            if name.endswith(("_date", "_local", "_utc")):
                assert "YYYY-MM-DD" in description, f"{cls.__name__}.{name}"
            if name.endswith("_cents"):
                assert "cents" in description, f"{cls.__name__}.{name}"
            if name.endswith("_minutes"):
                assert "minutes" in description.lower(), f"{cls.__name__}.{name}"
            if typing.get_origin(base) is list:
                assert "order" in description or "sorted" in description, f"{cls.__name__}.{name} does not state its order"
            assert type(None) not in typing.get_args(base), f"{cls.__name__}.{name}: no field is nullable in this contract"
