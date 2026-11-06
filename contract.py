"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    GET_AUDIT_CASE = "get_audit_case"
    COMPUTE_AUDIT = "compute_audit"


class Task(Enum):
    AUDIT_UN_TRAVEL = "audit-un-travel"


class UnScenario(Enum):
    """One proposed trip per member; its facts are bundled with the plugin."""

    GENEVA_COUNCIL_SESSION = "geneva-council-session"
    NAIROBI_ASSEMBLY_DELEGATE = "nairobi-assembly-delegate"
    BANGKOK_STATISTICS_KEYNOTE = "bangkok-statistics-keynote"
    ADDIS_ABABA_BUDGET_REVIEW = "addis-ababa-budget-review"
    VIENNA_OZONE_WORKSHOP = "vienna-ozone-workshop"
    PANAMA_HUB_RETREAT = "panama-hub-retreat"
    MOGADISHU_FIELD_MISSION = "mogadishu-field-mission"
    KABUL_MISSION_HANDOVER = "kabul-mission-handover"
    AMMAN_REFUGEE_BRIEFING = "amman-refugee-briefing"
    BEIRUT_DONOR_ROUNDTABLE = "beirut-donor-roundtable"
    NAIROBI_INTERVIEWER = "nairobi-interviewer"
    VIENNA_NARCOTICS_COMMISSION = "vienna-narcotics-commission"
    GENEVA_TRADE_FORUM = "geneva-trade-forum"
    BANGKOK_DISASTER_DRILL = "bangkok-disaster-drill"
    NEW_YORK_HLPF_PANEL = "new-york-hlpf-panel"
    SANTIAGO_LOGISTICIAN = "santiago-logistician"
    BANGKOK_WATER_DIALOGUE = "bangkok-water-dialogue"
    VIENNA_MILES_COLLECTOR = "vienna-miles-collector"
    ROME_FOOD_SECURITY_SUMMIT = "rome-food-security-summit"
    BANGKOK_RESULTS_PROGRAMME = "bangkok-results-programme"
    NAIROBI_PROCUREMENT_CLINIC = "nairobi-procurement-clinic"
    GENEVA_STATISTICS_BRIEFING = "geneva-statistics-briefing"
    MOGADISHU_LOGISTICS_SURVEY = "mogadishu-logistics-survey"


class TravelerCategory(Enum):
    """The traveller's status on this trip, which sets the cabin rule that applies."""

    STAFF_BELOW_ASG = "staff_below_asg"
    CONSULTANT = "consultant"
    TRAINING_PARTICIPANT = "training_participant"
    INSTRUCTOR = "instructor"


class TripPurpose(Enum):
    """Why the trip is made: learning and development (training) travel has its own cabin rule."""

    OFFICIAL_BUSINESS = "official_business"
    LEARNING_AND_DEVELOPMENT = "learning_and_development"


class UnCabin(Enum):
    ECONOMY = "economy"
    BUSINESS = "business"


class UnViolation(Enum):
    """The audit's findings, in their canonical order: a violations list keeps this order."""

    CABIN_ABOVE_ENTITLEMENT = "CABIN_ABOVE_ENTITLEMENT"
    ROUTE_EXCEEDS_TIME_LIMIT = "ROUTE_EXCEEDS_TIME_LIMIT"
    ROUTE_NOT_LEAST_COSTLY = "ROUTE_NOT_LEAST_COSTLY"
    LATE_ARRANGEMENT = "LATE_ARRANGEMENT"
    LATE_REQUEST_ABOVE_ECONOMY = "LATE_REQUEST_ABOVE_ECONOMY"


@dataclass
class ScenarioInput(Output):
    scenario: Annotated[UnScenario, "Which proposed trip to audit, e.g. geneva-council-session"]


@dataclass
class Traveler(Output):
    traveler_id: Annotated[str, "Traveller id, e.g. T301"]
    name: Annotated[str, "The traveller's full name"]
    department: Annotated[str, "UN entity and unit"]
    duty_station: Annotated[str, "The traveller's duty station or home base"]


@dataclass
class Segment(Output):
    flight: Annotated[str, "Flight number, e.g. K2 101"]
    carrier: Annotated[str, "The (fictional) airline that flies it"]
    origin: Annotated[str, "Origin airport IATA code"]
    destination: Annotated[str, "Destination airport IATA code"]
    depart_local: Annotated[str, "YYYY-MM-DDTHH:MM, origin local time"]
    arrive_local: Annotated[str, "YYYY-MM-DDTHH:MM, destination local time"]
    in_air_minutes: Annotated[int, "This one flight's takeoff-to-landing minutes"]


@dataclass
class Itinerary(Output):
    itinerary_id: Annotated[str, "Itinerary id, e.g. I457"]
    segments: Annotated[list[Segment], "Flights in flying order"]
    layover_minutes: Annotated[
        list[int], "Ground minutes between consecutive flights, in flying order; empty for a nonstop"
    ]
    total_elapsed_minutes: Annotated[int, "Minutes from first takeoff to last landing, layovers included"]
    fares_cents: Annotated[dict[UnCabin, int], "Ticket price per cabin, USD cents; economy and business are always both offered"]


@dataclass
class AuditCaseOutput(Output):
    scenario: Annotated[UnScenario, "The scenario this case belongs to"]
    request_text: Annotated[str, "The traveller's own words; they may argue for things policy does not allow"]
    traveler: Annotated[Traveler, "The traveller on this trip"]
    traveler_category: Annotated[
        TravelerCategory, "staff_below_asg, consultant (incl. individual contractors), training_participant or instructor"
    ]
    trip_purpose: Annotated[TripPurpose, "official_business, or learning_and_development for a training course"]
    origin: Annotated[str, "IATA code the journey starts from"]
    destination: Annotated[str, "IATA code of the official destination"]
    departure_date: Annotated[str, "Day the journey starts, YYYY-MM-DD, origin local"]
    request_date: Annotated[str, "Day the travel request was submitted, YYYY-MM-DD"]
    booking_date: Annotated[str, "Day the travel arrangements were finalized (ticket issued), YYYY-MM-DD"]
    proposed_itinerary_id: Annotated[str, "The itinerary proposed for this trip; one of itineraries"]
    proposed_cabin: Annotated[UnCabin, "The cabin proposed for this trip"]
    itineraries: Annotated[
        list[Itinerary], "Every itinerary from origin to destination leaving on departure_date (origin local), sorted by id"
    ]


@dataclass
class UnAuditOutput(Output):
    entitled_cabin: Annotated[UnCabin, "The cabin the traveller is entitled to on the proposed itinerary"]
    violations: Annotated[
        list[UnViolation],
        "Every rule the proposed trip breaks, each once, in UnViolation's declaration order (handbook C10); "
        "empty when it complies",
    ]
    compliant: Annotated[bool, "true exactly when violations is empty"]


TOOLS = {
    Tool.GET_AUDIT_CASE: (ScenarioInput, AuditCaseOutput),
    Tool.COMPUTE_AUDIT: (ScenarioInput, UnAuditOutput),
}
TASKS = {Task.AUDIT_UN_TRAVEL: (ScenarioInput, UnAuditOutput)}
