"""Shared core of the travel-policy fixture generators (development only, never run by a tool or the
verifier): builds segment and itinerary records with their UTC times and minute totals precomputed,
so nothing at evaluation time does timezone arithmetic. Vendored byte-identical into every plugin."""

import json
from datetime import datetime, timedelta
from itertools import pairwise
from zoneinfo import ZoneInfo

from plugin.world import CABINS

LOCAL_FORMAT = "%Y-%m-%dT%H:%M"
UTC_FORMAT = "%Y-%m-%dT%H:%MZ"


def segment(airports, segment_id, flight, marketing, operating, origin, destination, depart_local, in_air_minutes):
    """A segment record: it departs ``depart_local`` (origin's local time) and lands ``in_air_minutes``
    later; both local times, both UTC times and the in-air minutes are stored."""
    depart = datetime.strptime(depart_local, LOCAL_FORMAT).replace(tzinfo=ZoneInfo(airports[origin]["timezone"]))
    arrive = depart + timedelta(minutes=in_air_minutes)
    return {
        "segment_id": segment_id,
        "flight": flight,
        "marketing_carrier": marketing,
        "operating_carrier": operating,
        "origin": origin,
        "destination": destination,
        "depart_local": depart_local,
        "arrive_local": arrive.astimezone(ZoneInfo(airports[destination]["timezone"])).strftime(LOCAL_FORMAT),
        "depart_utc": depart.astimezone(ZoneInfo("UTC")).strftime(UTC_FORMAT),
        "arrive_utc": arrive.astimezone(ZoneInfo("UTC")).strftime(UTC_FORMAT),
        "in_air_minutes": in_air_minutes,
    }


def utc(stamp):
    return datetime.strptime(stamp, UTC_FORMAT)


def itinerary(itinerary_id, segments, fares_cents):
    """An itinerary record over ``segments`` (in flying order) with its connection and minute totals."""
    for before, after in pairwise(segments):
        if before["destination"] != after["origin"] or utc(after["depart_utc"]) <= utc(before["arrive_utc"]):
            raise ValueError(f"itinerary {itinerary_id}: {after['segment_id']} does not connect from {before['segment_id']}")
    layovers = [
        int((utc(after["depart_utc"]) - utc(before["arrive_utc"])).total_seconds() // 60)
        for before, after in pairwise(segments)
    ]
    if set(fares_cents) != set(CABINS):
        raise ValueError(f"itinerary {itinerary_id}: fares must name every cabin of {CABINS}")
    return {
        "itinerary_id": itinerary_id,
        "segment_ids": [record["segment_id"] for record in segments],
        "connections": len(segments) - 1,
        "layover_minutes": layovers,
        "total_elapsed_minutes": int((utc(segments[-1]["arrive_utc"]) - utc(segments[0]["depart_utc"])).total_seconds() // 60),
        "total_in_air_minutes": sum(record["in_air_minutes"] for record in segments),
        "longest_segment_minutes": max(record["in_air_minutes"] for record in segments),
        "fares_cents": {cabin: fares_cents[cabin] for cabin in CABINS},
    }


def json_text(value):
    """The committed form of a fixture file: stable, readable, newline-terminated."""
    return json.dumps(value, indent=1, ensure_ascii=False) + "\n"
