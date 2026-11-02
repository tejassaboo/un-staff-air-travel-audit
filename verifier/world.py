"""Shared core of the travel-policy plugins: the toy world's fixture schema and loader, the cabin ladder,
date and minute arithmetic, and the itinerary search the tools and the verifier both run.

Pure standard library (json, re, pathlib) and no clock, so the sandboxed verifier can run it too. It is
vendored byte-identical into src/plugin/ and verifier/ of every plugin (a test checks the two copies).
Times are compared as precomputed UTC stamps: nothing here does timezone arithmetic.
"""

import json
import re
from pathlib import Path

# The cabin ladder, lowest first.
CABINS = ("economy", "premium_economy", "business", "first")
DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
UTC_STAMP = re.compile(r"(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})Z")
IATA = re.compile(r"[A-Z]{3}")
MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

# Each fixture table: its file's records' keys, the first one the record's id.
SCHEMA = {
    "airports": ("code", "city", "country", "continental_us", "us_50_states_dc", "timezone"),
    "carriers": ("code", "name", "us_flag_carrier", "codeshare_partners"),
    "segments": (
        "segment_id",
        "flight",
        "marketing_carrier",
        "operating_carrier",
        "origin",
        "destination",
        "depart_local",
        "arrive_local",
        "depart_utc",
        "arrive_utc",
        "in_air_minutes",
    ),
    "itineraries": (
        "itinerary_id",
        "segment_ids",
        "connections",
        "layover_minutes",
        "total_elapsed_minutes",
        "total_in_air_minutes",
        "longest_segment_minutes",
        "fares_cents",
    ),
    "travelers": ("traveler_id", "name", "department", "base_point"),
}


def cabin_rank(cabin):
    """The cabin's place on the ladder: economy 0 ... first 3."""
    return CABINS.index(cabin)


def lower_cabin(first, second):
    """The lower of two cabins on the ladder."""
    return first if cabin_rank(first) <= cabin_rank(second) else second


def day_number(text):
    """Days from 1970-01-01 to the date YYYY-MM-DD; ValueError for anything but a real calendar date."""
    match = DATE.fullmatch(text)
    if match is None:
        raise ValueError(f"{text!r} is not a YYYY-MM-DD date")
    year, month, day = (int(part) for part in match.groups())
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    if not 1 <= month <= 12 or not 1 <= day <= MONTH_DAYS[month - 1] + (month == 2 and leap):
        raise ValueError(f"{text!r} is not a calendar date")
    shifted = year - (month <= 2)  # Howard Hinnant's days_from_civil
    era = shifted // 400
    year_of_era = shifted - era * 400
    day_of_year = (153 * ((month + 9) % 12) + 2) // 5 + day - 1
    return era * 146097 + year_of_era * 365 + year_of_era // 4 - year_of_era // 100 + day_of_year - 719468


def days_between(start, end):
    """Calendar days from date ``start`` to date ``end`` (negative when end is earlier)."""
    return day_number(end) - day_number(start)


def utc_minutes(text):
    """Minutes since 1970-01-01T00:00Z of a UTC stamp YYYY-MM-DDTHH:MMZ."""
    match = UTC_STAMP.fullmatch(text)
    if match is None:
        raise ValueError(f"{text!r} is not a UTC stamp YYYY-MM-DDTHH:MMZ")
    date, hour, minute = match.groups()
    if int(hour) > 23 or int(minute) > 59:
        raise ValueError(f"{text!r} is not a time of day")
    return day_number(date) * 1440 + int(hour) * 60 + int(minute)


def load_world(data_dir):
    """Every fixture table under ``data_dir``, each a dict from record id to record."""
    world = {}
    for table, keys in SCHEMA.items():
        records = json.loads((Path(data_dir) / f"{table}.json").read_text(encoding="utf-8"))
        world[table] = {record[keys[0]]: record for record in records}
    return world


def load_scenario(data_dir, scenario_id):
    """One scenario's facts (never its expected answer), from scenarios/<id>.json under ``data_dir``."""
    return json.loads((Path(data_dir) / "scenarios" / f"{scenario_id}.json").read_text(encoding="utf-8"))


def schema_problems(world):
    """Every way the loaded fixtures break SCHEMA or point at a record that does not exist."""
    problems = []
    for table, keys in SCHEMA.items():
        for record_id, record in world[table].items():
            if tuple(record) != keys:
                problems.append(f"{table} {record_id}: keys {list(record)} are not {list(keys)}")
    for segment in world["segments"].values():
        for key in ("marketing_carrier", "operating_carrier"):
            if segment[key] not in world["carriers"]:
                problems.append(f"segment {segment['segment_id']}: unknown carrier {segment[key]}")
        for key in ("origin", "destination"):
            if segment[key] not in world["airports"]:
                problems.append(f"segment {segment['segment_id']}: unknown airport {segment[key]}")
    for itinerary in world["itineraries"].values():
        for segment_id in itinerary["segment_ids"]:
            if segment_id not in world["segments"]:
                problems.append(f"itinerary {itinerary['itinerary_id']}: unknown segment {segment_id}")
        if tuple(itinerary["fares_cents"]) != CABINS:
            problems.append(f"itinerary {itinerary['itinerary_id']}: fares are not keyed by {list(CABINS)}")
    return problems


def itinerary_segments(world, itinerary):
    """The itinerary's segment records, in flying order."""
    return [world["segments"][segment_id] for segment_id in itinerary["segment_ids"]]


def search(world, origins, destination, date):
    """Every itinerary whose first segment leaves one of ``origins`` on local date ``date`` and whose last
    segment lands at ``destination``, by itinerary id."""
    found = []
    for itinerary_id in sorted(world["itineraries"]):
        itinerary = world["itineraries"][itinerary_id]
        segments = itinerary_segments(world, itinerary)
        first, last = segments[0], segments[-1]
        if first["origin"] in origins and last["destination"] == destination and first["depart_local"][:10] == date:
            found.append(itinerary)
    return found


def itinerary_view(world, itinerary):
    """The itinerary as a search shows it: each segment's flight facts, the final arrival in UTC, the fares."""
    segments = itinerary_segments(world, itinerary)
    return {
        "itinerary_id": itinerary["itinerary_id"],
        "segments": [
            {
                key: segment[key]
                for key in (
                    "flight",
                    "marketing_carrier",
                    "operating_carrier",
                    "origin",
                    "destination",
                    "depart_local",
                    "arrive_local",
                    "in_air_minutes",
                )
            }
            for segment in segments
        ],
        "arrive_utc": segments[-1]["arrive_utc"],
        "fares_cents": dict(itinerary["fares_cents"]),
    }


def carrier_view(world, itineraries):
    """Each carrier that markets or operates a segment of ``itineraries``: code, name, US flag, by code."""
    codes = sorted(
        {
            segment[key]
            for itinerary in itineraries
            for segment in itinerary_segments(world, itinerary)
            for key in ("marketing_carrier", "operating_carrier")
        }
    )
    return [
        {"code": code, "name": world["carriers"][code]["name"], "us_flag_carrier": world["carriers"][code]["us_flag_carrier"]}
        for code in codes
    ]
