"""The seeded generator of this plugin's fixtures (development only): `uv run python -m plugin.tools_dev.generate`
rewrites src/plugin/data/ (except handbook.md). The committed files are the source of truth; a test checks
this generator still reproduces them byte for byte.

Each scenario's flights are written out by hand, because each one sets a trap from the brief (TRAVEL_POLICY_
TASKS_CONTEXT.md section 4, T3, with the Rev.1 decisions); the seed only scatters the itinerary ids, so the
proposed itinerary is never simply the first or lowest id. Airlines, flight numbers, schedules and fares are
fictional. Expected answers are not written here: they live in tests/cases/.

Each scenario also carries filler routes (FILLERS), so that 6 to 8 candidates compete and the route rule is a
real search. A filler can never change a hand-computed answer, and check_fillers() proves it by arithmetic
alone: every filler is slower than the hand routes' most direct one, so the time rule judges the proposal the
same, and a filler that itself passes the time rule costs more, in both cabins, than the cheapest hand route
that passes it, so the least allowed fare is unchanged. Fillers that fail the time rule may be cheap: they
are the decoys the handbook's C6 warns about.
"""

import random
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from plugin.tools_dev.worldgen import UTC_FORMAT, itinerary, json_text, segment

SEED = 20240530  # ST/AI/2013/3/Rev.1 is dated 30 May 2024
DATA = Path(__file__).resolve().parents[1] / "data"

AIRPORTS = [
    # code, city, country, continental US, US 50 states + DC, IANA timezone
    ("ADD", "Addis Ababa", "ET", False, False, "Africa/Addis_Ababa"),
    ("AMM", "Amman", "JO", False, False, "Asia/Amman"),
    ("AMS", "Amsterdam", "NL", False, False, "Europe/Amsterdam"),
    ("BEY", "Beirut", "LB", False, False, "Asia/Beirut"),
    ("BKK", "Bangkok", "TH", False, False, "Asia/Bangkok"),
    ("BOG", "Bogota", "CO", False, False, "America/Bogota"),
    ("CAI", "Cairo", "EG", False, False, "Africa/Cairo"),
    ("CDG", "Paris Charles de Gaulle", "FR", False, False, "Europe/Paris"),
    ("DEL", "Delhi", "IN", False, False, "Asia/Kolkata"),
    ("DOH", "Doha", "QA", False, False, "Asia/Qatar"),
    ("DXB", "Dubai", "AE", False, False, "Asia/Dubai"),
    ("FCO", "Rome Fiumicino", "IT", False, False, "Europe/Rome"),
    ("FRA", "Frankfurt", "DE", False, False, "Europe/Berlin"),
    ("GVA", "Geneva", "CH", False, False, "Europe/Zurich"),
    ("IST", "Istanbul", "TR", False, False, "Europe/Istanbul"),
    ("JFK", "New York JFK", "US", True, True, "America/New_York"),
    ("JNB", "Johannesburg", "ZA", False, False, "Africa/Johannesburg"),
    ("KBL", "Kabul", "AF", False, False, "Asia/Kabul"),
    ("LHR", "London Heathrow", "GB", False, False, "Europe/London"),
    ("LIM", "Lima", "PE", False, False, "America/Lima"),
    ("MGQ", "Mogadishu", "SO", False, False, "Africa/Mogadishu"),
    ("MIA", "Miami", "US", True, True, "America/New_York"),
    ("NBO", "Nairobi", "KE", False, False, "Africa/Nairobi"),
    ("PTY", "Panama City", "PA", False, False, "America/Panama"),
    ("SCL", "Santiago", "CL", False, False, "America/Santiago"),
    ("VIE", "Vienna", "AT", False, False, "Europe/Vienna"),
]

CARRIERS = [
    # code, fictional name, US flag carrier, code-share partners (unused by this policy)
    ("A4", "Aurora Atlantic", True, []),
    ("B7", "Boreal Wings", False, []),
    ("C3", "Cedar Crescent", False, []),
    ("D5", "Dune Pearl Airways", False, []),
    ("E9", "Elbe Express", False, []),
    ("H3", "Highland Rift Airways", False, []),
    ("K2", "Kestrel Airways", False, []),
    ("L2", "Lumen Levant", False, []),
    ("L9", "Lotus Sky", False, []),
    ("M8", "Meridian Gulf", False, []),
    ("N7", "Nilegate Air", False, []),
    ("P5", "Pacific Condor", False, []),
    ("S2", "Savanna Air", False, []),
    ("T6", "Taurus Anatolia", False, []),
    ("V4", "Andes Vista", False, []),
]

TRAVELERS = [
    # traveler id, name, UN entity and unit, duty station (the shared schema's base_point)
    ("T301", "Wanjiru Kamau", "UNEP, Law Division", "Nairobi"),
    ("T302", "Lukas Brenner", "OHCHR, Rule of Law Section", "Geneva"),
    ("T303", "Hanna Tesfaye", "ECA, African Centre for Statistics", "Addis Ababa"),
    ("T304", "Somchai Prasert", "ESCAP, Programme Management Division", "Bangkok"),
    ("T305", "Amina Odhiambo", "UNEP, Ozone Secretariat", "Nairobi"),
    ("T306", "Camila Rojas", "ECLAC, Social Development Division", "Santiago"),
    ("T307", "Pierre Lambert", "DPPA, Horn of Africa Team", "Geneva"),
    ("T308", "Grace Mwangi", "OHCHR, Field Operations Service", "Nairobi"),
    ("T309", "Ingrid Solberg", "UNHCR, Division of International Protection", "Geneva"),
    ("T310", "Marco Bianchi", "UNIDO, Partnerships Division", "Vienna"),
    ("T311", "Elena Vasquez", "OIOS, Inspection and Evaluation Division (consultant)", "New York"),
    ("T312", "Kofi Mensah", "UNODC, New York Liaison Office", "New York"),
    ("T313", "Priya Raman", "UNCTAD, New York Office", "New York"),
    ("T314", "Tomas Herrera", "UNOOSA, UN-SPIDER Programme", "Vienna"),
    ("T315", "Aisha Bello", "UN-Habitat, Urban Practices Branch", "Nairobi"),
    ("T316", "Naledi Dlamini", "DOS, Supply Chain Training Unit", "New York"),
    ("T317", "Felix Wagner", "UNECE, Water Convention Secretariat", "Geneva"),
    ("T318", "Daniel Okoro", "DOS, Logistics Division", "Nairobi"),
    ("T319", "Rafael Costa", "DESA, Division for Sustainable Development Goals", "New York"),
    ("T320", "Yusuf Abdallah", "UNON, Results-Based Management Unit", "Nairobi"),
    ("T321", "Beatrix Hoffmann", "UNIDO, Procurement Services (instructor)", "Vienna"),
    ("T322", "Mekdes Alemu", "ECA, Statistics Division", "Addis Ababa"),
    ("T323", "Jonas Pichler", "UNOV, Logistics Section", "Vienna"),
]


def route(first_depart_local, *legs, fares):
    """An itinerary spec: its first flight leaves at ``first_depart_local``; each leg is
    (flight, carrier, origin, destination, in-air minutes, minutes on the ground before it)."""
    return {"first": first_depart_local, "legs": legs, "fares": fares}


def filler(first_depart_local, *legs, fares):
    """A filler route, as route() but with each leg (carrier, origin, destination, in-air minutes, minutes on the
    ground before it): build() numbers its flights and check_fillers() proves it cannot change the answer."""
    return {"first": first_depart_local, "legs": tuple((None, *leg) for leg in legs), "fares": fares, "filler": True}


def elapsed(spec):
    """A route spec's total elapsed minutes: its in-air minutes plus its layovers."""
    return sum(leg[4] + leg[5] for leg in spec["legs"])


def check_fillers(scenario_id, hand, fillers):
    """Raise unless every filler leaves the hand-computed answer alone (see the module docstring), and the whole
    pool keeps one most direct route, no fare ties, and the same fare order in both cabins."""
    direct = min(elapsed(spec) for spec in hand)
    allowed = [spec for spec in hand if elapsed(spec) - direct < 240]
    least = tuple(min(spec["fares"][cabin] for spec in allowed) for cabin in (0, 1))
    for spec in fillers:
        extra = elapsed(spec) - direct
        if extra <= 0:
            raise ValueError(f"{scenario_id}: a filler ({elapsed(spec)} min) is as direct as the hand routes ({direct})")
        if extra < 240 and not (spec["fares"][0] > least[0] and spec["fares"][1] > least[1]):
            raise ValueError(f"{scenario_id}: an allowed filler {spec['fares']} undercuts the least allowed hand fare {least}")
    pool = [*hand, *fillers]
    if len({elapsed(spec) for spec in pool}) != len(pool):
        raise ValueError(f"{scenario_id}: two candidates take the same time")
    for cabin in (0, 1):
        if len({spec["fares"][cabin] for spec in pool}) != len(pool):
            raise ValueError(f"{scenario_id}: a fare tie in cabin {cabin}")
    if sorted(pool, key=lambda spec: spec["fares"][0]) != sorted(pool, key=lambda spec: spec["fares"][1]):
        raise ValueError(f"{scenario_id}: candidates rank differently in economy and in business")


def trip(scenario, traveler, category, purpose, origin, destination, departure, request_days, booking_days, cabin, text):
    """A scenario's facts; its request and booking dates lie the given number of days before departure.
    The proposed itinerary is the scenario's first route (its id is filled in once ids are drawn)."""
    day = date.fromisoformat(departure)
    return {
        "scenario": scenario,
        "request_text": text,
        "request_date": (day - timedelta(days=request_days)).isoformat(),
        "booking_date": (day - timedelta(days=booking_days)).isoformat(),
        "traveler_id": traveler,
        "traveler_category": category,
        "trip_purpose": purpose,
        "origin": origin,
        "destination": destination,
        "departure_date": departure,
        "proposed_itinerary_id": None,
        "proposed_cabin": cabin,
    }


STAFF, CONSULTANT, PARTICIPANT, INSTRUCTOR = "staff_below_asg", "consultant", "training_participant", "instructor"
BUSINESS, TRAINING = "official_business", "learning_and_development"

# Per scenario: its facts and its routes, the proposed one first. Fares are (economy, business) USD cents.
SCENARIOS = [
    {
        "facts": trip(
            "geneva-council-session", "T301", STAFF, BUSINESS, "NBO", "GVA", "2027-02-22", 34, 27, "business",
            "Hello travel unit! I'm speaking at a Human Rights Council side event on environmental defenders on 23 "
            "February. Please confirm business on the Kestrel nonstop, which is nine hours on the dot. I spotted a much "
            "cheaper routing through Addis and Istanbul, but it lands in the middle of the night and takes forever.",
        ),
        "routes": [
            route("2027-02-22T08:15", ("K2 101", "K2", "NBO", "GVA", 540, 0), fares=(98400, 361000)),
            route(
                "2027-02-22T08:40",
                ("N7 330", "N7", "NBO", "CAI", 300, 0),
                ("N7 761", "N7", "CAI", "GVA", 245, 95),
                fares=(104500, 389000),
            ),
            route(
                "2027-02-22T06:00",
                ("H3 308", "H3", "NBO", "ADD", 115, 0),
                ("H3 714", "H3", "ADD", "IST", 400, 245),
                ("T6 1917", "T6", "IST", "GVA", 215, 145),
                fares=(79900, 298000),
            ),
        ],
    },
    {
        "facts": trip(
            "nairobi-assembly-delegate", "T302", STAFF, BUSINESS, "GVA", "NBO", "2027-02-26", 30, 22, "business",
            "I'm advising a delegation at the UN Environment Assembly. My colleague always flies business on this "
            "route, and the Kestrel nonstop is 8 hours 59 minutes, which is nine hours for any practical purpose. "
            "Business, please, and add the lounge pass.",
        ),
        "routes": [
            route("2027-02-26T10:05", ("K2 102", "K2", "GVA", "NBO", 539, 0), fares=(97300, 352000)),
            route(
                "2027-02-26T09:30",
                ("H3 721", "H3", "GVA", "ADD", 400, 0),
                ("H3 306", "H3", "ADD", "NBO", 115, 80),
                fares=(101800, 371500),
            ),
        ],
    },
    {
        "facts": trip(
            "bangkok-statistics-keynote", "T303", STAFF, BUSINESS, "ADD", "BKK", "2027-03-08", 40, 30, "business",
            "I'm giving the keynote at the ESCAP Committee on Statistics. Neither flight is long on its own, I know, "
            "but with the Dubai connection it's a long night, so I've asked for business. Is that within the rules?",
        ),
        "routes": [
            route(
                "2027-03-08T01:10",
                ("M8 512", "M8", "ADD", "DXB", 220, 0),
                ("M8 372", "M8", "DXB", "BKK", 360, 80),
                fares=(84600, 298000),
            ),
            route(
                "2027-03-08T00:40",
                ("D5 1408", "D5", "ADD", "DOH", 230, 0),
                ("D5 832", "D5", "DOH", "BKK", 370, 150),
                fares=(91200, 322000),
            ),
        ],
    },
    {
        "facts": trip(
            "addis-ababa-budget-review", "T304", STAFF, BUSINESS, "BKK", "ADD", "2027-03-15", 35, 25, "economy",
            "Joint budget review with ECA in Addis. Door to door it's well over eleven hours once you add the drive to "
            "Suvarnabhumi and check-in, so I assume I'm entitled to business, but I booked economy to be safe. Please "
            "confirm my entitlement for the file.",
        ),
        "routes": [
            route(
                "2027-03-15T00:30",
                ("M8 373", "M8", "BKK", "DXB", 360, 0),
                ("M8 513", "M8", "DXB", "ADD", 219, 80),
                fares=(83900, 296500),
            ),
            route(
                "2027-03-15T01:15",
                ("D5 833", "D5", "BKK", "DOH", 375, 0),
                ("D5 1409", "D5", "DOH", "ADD", 230, 125),
                fares=(88700, 309000),
            ),
        ],
    },
    {
        "facts": trip(
            "vienna-ozone-workshop", "T305", STAFF, BUSINESS, "NBO", "VIE", "2027-04-12", 31, 24, "business",
            "I'm facilitating a Montreal Protocol compliance workshop in Vienna. It's eleven hours and twenty minutes "
            "from wheels-up in Nairobi to landing in Vienna, the Cairo wait included, so business applies, right? "
            "Please also add a paid seat with extra legroom.",
        ),
        "routes": [
            route(
                "2027-04-12T02:00",
                ("N7 332", "N7", "NBO", "CAI", 300, 0),
                ("N7 783", "N7", "CAI", "VIE", 230, 150),
                fares=(88100, 301000),
            ),
            route(
                "2027-04-12T01:30",
                ("T6 608", "T6", "NBO", "IST", 400, 0),
                ("T6 1885", "T6", "IST", "VIE", 135, 100),
                fares=(92400, 318000),
            ),
        ],
    },
    {
        "facts": trip(
            "panama-hub-retreat", "T306", STAFF, BUSINESS, "SCL", "PTY", "2027-04-19", 45, 33, "business",
            "I'm leading a session at the UNDP regional hub retreat in Panama. The Pacific Condor routing stops in Lima "
            "and Bogota, just under two hours each time. There's a cheaper option via Miami too, but it eats most of the "
            "day. I'd like business on the Condor routing if I qualify.",
        ),
        "routes": [
            route(
                "2027-04-19T06:00",
                ("P5 211", "P5", "SCL", "LIM", 210, 0),
                ("P5 418", "P5", "LIM", "BOG", 190, 110),
                ("P5 690", "P5", "BOG", "PTY", 80, 110),
                fares=(61800, 214000),
            ),
            route(
                "2027-04-19T07:30",
                ("V4 905", "V4", "SCL", "BOG", 330, 0),
                ("V4 377", "V4", "BOG", "PTY", 80, 200),
                fares=(66400, 229000),
            ),
            route(
                "2027-04-19T05:10",
                ("A4 940", "A4", "SCL", "MIA", 510, 0),
                ("A4 1288", "A4", "MIA", "PTY", 165, 240),
                fares=(54900, 189000),
            ),
        ],
    },
    {
        "facts": trip(
            "mogadishu-field-mission", "T307", STAFF, BUSINESS, "GVA", "MGQ", "2027-05-03", 29, 21, "business",
            "I'm joining a political mission assessment in Mogadishu. Counting the night in Doha it's a 23-hour journey, "
            "which is twice the eleven hours in the rules, so business all the way, please. The transit hotel is the "
            "Corniche Pearl.",
        ),
        "routes": [
            route(
                "2027-05-03T15:10",
                ("D5 96", "D5", "GVA", "DOH", 360, 0),
                ("D5 1271", "D5", "DOH", "MGQ", 300, 721),
                fares=(112300, 402000),
            ),
            route(
                "2027-05-03T14:00",
                ("M8 88", "M8", "GVA", "DXB", 375, 0),
                ("M8 1734", "M8", "DXB", "MGQ", 290, 790),
                fares=(118900, 426000),
            ),
        ],
    },
    {
        "facts": trip(
            "kabul-mission-handover", "T308", STAFF, BUSINESS, "NBO", "KBL", "2027-05-10", 26, 19, "business",
            "I'm handing over a human rights monitoring portfolio in Kabul. There's a long overnight in Doha, I know. "
            "My section chief says any overnight stop resets the clock and I should fly economy, but I'd like you to "
            "check: I've proposed business.",
        ),
        "routes": [
            route(
                "2027-05-10T09:00",
                ("D5 1320", "D5", "NBO", "DOH", 330, 0),
                ("D5 1155", "D5", "DOH", "KBL", 240, 720),
                fares=(104700, 377000),
            ),
            route(
                "2027-05-10T08:20",
                ("M8 726", "M8", "NBO", "DXB", 300, 0),
                ("M8 1460", "M8", "DXB", "KBL", 200, 840),
                fares=(109900, 391000),
            ),
        ],
    },
    {
        "facts": trip(
            "amman-refugee-briefing", "T309", STAFF, BUSINESS, "GVA", "AMM", "2027-05-24", 30, 20, "economy",
            "I'm briefing partners on the regional refugee response plan in Amman. I picked the cheaper Istanbul "
            "connection. Our office manager says a connection that adds 'about four hours' is never allowed, so do I "
            "have to switch to the nonstop?",
        ),
        "routes": [
            route(
                "2027-05-24T07:10",
                ("T6 1922", "T6", "GVA", "IST", 190, 0),
                ("T6 812", "T6", "IST", "AMM", 180, 139),
                fares=(44800, 142000),
            ),
            route("2027-05-24T09:00", ("L2 404", "L2", "GVA", "AMM", 270, 0), fares=(61200, 188000)),
        ],
    },
    {
        "facts": trip(
            "beirut-donor-roundtable", "T310", STAFF, BUSINESS, "VIE", "BEY", "2027-06-07", 28, 20, "economy",
            "I'm presenting at a donor roundtable on Lebanon's industrial recovery. The Istanbul connection saves almost "
            "190 dollars against the nonstop, so it is surely the 'most economical route'. Economy is fine, and please "
            "add travel insurance.",
        ),
        "routes": [
            route(
                "2027-06-07T06:30",
                ("T6 1886", "T6", "VIE", "IST", 140, 0),
                ("T6 826", "T6", "IST", "BEY", 120, 190),
                fares=(39600, 119000),
            ),
            route("2027-06-07T11:00", ("C3 212", "C3", "VIE", "BEY", 210, 0), fares=(58300, 171000)),
        ],
    },
    {
        "facts": trip(
            "nairobi-interviewer", "T311", CONSULTANT, BUSINESS, "JFK", "NBO", "2027-06-14", 33, 25, "business",
            "I'm leading field interviews for an OIOS programme evaluation in Nairobi. It's a fourteen-hour nonstop, way "
            "past the nine-hour line, and staff on the same evaluation team fly business. Please book business and the "
            "lounge pass.",
        ),
        "routes": [
            route("2027-06-14T11:15", ("A4 51", "A4", "JFK", "NBO", 840, 0), fares=(142000, 498000)),
            route(
                "2027-06-14T10:30",
                ("H3 503", "H3", "JFK", "ADD", 780, 0),
                ("H3 306", "H3", "ADD", "NBO", 115, 90),
                fares=(148500, 521000),
            ),
        ],
    },
    {
        "facts": trip(
            "vienna-narcotics-commission", "T312", STAFF, BUSINESS, "JFK", "VIE", "2027-03-01", 25, 16, "economy",
            "I'm supporting the Commission on Narcotic Drugs intersessional in Vienna. Sorry this is a bit last minute: "
            "the ticket only went out today. Economy on the Aurora nonstop.",
        ),
        "routes": [
            route("2027-03-01T17:40", ("A4 88", "A4", "JFK", "VIE", 525, 0), fares=(76400, 284000)),
            route(
                "2027-03-01T16:20",
                ("T6 4", "T6", "JFK", "IST", 590, 0),
                ("T6 1883", "T6", "IST", "VIE", 135, 100),
                fares=(81200, 301000),
            ),
        ],
    },
    {
        "facts": trip(
            "geneva-trade-forum", "T313", STAFF, BUSINESS, "JFK", "GVA", "2027-03-22", 24, 15, "economy",
            "I'm moderating a panel at the UNCTAD trade and development forum. It's the cheapest ticket on the route and "
            "I'm in economy, so being a day past the advance-purchase date shouldn't matter, should it?",
        ),
        "routes": [
            route("2027-03-22T18:30", ("A4 72", "A4", "JFK", "GVA", 465, 0), fares=(69800, 259000)),
            route(
                "2027-03-22T17:40",
                ("A4 88", "A4", "JFK", "VIE", 525, 0),
                ("A4 2061", "A4", "VIE", "GVA", 90, 95),
                fares=(74300, 276000),
            ),
        ],
    },
    {
        "facts": trip(
            "bangkok-disaster-drill", "T314", STAFF, BUSINESS, "VIE", "BKK", "2027-04-05", 21, 18, "business",
            "I'm running a satellite-data exercise at the regional disaster drill in Bangkok. I submitted the request "
            "exactly three weeks out, and the Lotus Sky nonstop is ten hours. Business, please.",
        ),
        "routes": [
            route("2027-04-05T13:20", ("L9 936", "L9", "VIE", "BKK", 600, 0), fares=(79900, 305000)),
            route(
                "2027-04-05T09:45",
                ("M8 128", "M8", "VIE", "DXB", 330, 0),
                ("M8 384", "M8", "DXB", "BKK", 360, 105),
                fares=(86200, 327000),
            ),
        ],
    },
    {
        "facts": trip(
            "new-york-hlpf-panel", "T315", STAFF, BUSINESS, "NBO", "JFK", "2027-07-12", 20, 17, "business",
            "I'm speaking on a High-level Political Forum panel in New York. The ticket is being issued 17 days out, well "
            "within the 16-day rule, and the nonstop is over fifteen hours, so business is clearly fine.",
        ),
        "routes": [
            route("2027-07-12T23:30", ("A4 52", "A4", "NBO", "JFK", 940, 0), fares=(151000, 534000)),
            route(
                "2027-07-12T21:15",
                ("H3 307", "H3", "NBO", "ADD", 115, 0),
                ("H3 504", "H3", "ADD", "JFK", 900, 105),
                fares=(158400, 556000),
            ),
        ],
    },
    {
        "facts": trip(
            "santiago-logistician", "T316", INSTRUCTOR, TRAINING, "JFK", "SCL", "2027-08-02", 38, 28, "business",
            "I'm teaching the supply-chain course for regional staff in Santiago. I know training travel is economy, "
            "but I'm on the faculty, not in the classroom. I've proposed business on the Pacific Condor nonstop.",
        ),
        "routes": [
            route("2027-08-02T21:00", ("P5 531", "P5", "JFK", "SCL", 645, 0), fares=(98700, 366000)),
            route(
                "2027-08-02T19:10",
                ("A4 1301", "A4", "JFK", "PTY", 330, 0),
                ("P5 619", "P5", "PTY", "SCL", 400, 110),
                fares=(104300, 381000),
            ),
        ],
    },
    {
        "facts": trip(
            "bangkok-water-dialogue", "T317", STAFF, BUSINESS, "GVA", "BKK", "2027-08-16", 19, 17, "economy",
            "I'm presenting at the Asia-Pacific water dialogue. Sorry the request went in late! To keep the budget down "
            "I'm happy to fly economy on the Lotus Sky nonstop rather than business.",
        ),
        "routes": [
            route("2027-08-16T12:00", ("L9 912", "L9", "GVA", "BKK", 620, 0), fares=(78800, 301000)),
            route(
                "2027-08-16T08:30",
                ("D5 92", "D5", "GVA", "DOH", 360, 0),
                ("D5 838", "D5", "DOH", "BKK", 370, 120),
                fares=(84100, 318000),
            ),
        ],
    },
    {
        "facts": trip(
            "vienna-miles-collector", "T318", PARTICIPANT, TRAINING, "NBO", "VIE", "2027-09-06", 18, 12, "business",
            "I'm attending the three-week procurement certification course in Vienna. A colleague on the same course "
            "flies business via Dubai, and I'd like to collect Meridian miles, so please book me the same. Add the "
            "lounge pass too.",
        ),
        "routes": [
            route(
                "2027-09-06T02:10",
                ("M8 720", "M8", "NBO", "DXB", 300, 0),
                ("M8 129", "M8", "DXB", "VIE", 360, 100),
                fares=(112000, 389000),
            ),
            route(
                "2027-09-06T02:00",
                ("N7 332", "N7", "NBO", "CAI", 300, 0),
                ("N7 783", "N7", "CAI", "VIE", 230, 150),
                fares=(88100, 301000),
            ),
            route(
                "2027-09-06T01:30",
                ("T6 608", "T6", "NBO", "IST", 400, 0),
                ("T6 1887", "T6", "IST", "VIE", 135, 400),
                fares=(79000, 279000),
            ),
        ],
    },
    {
        "facts": trip(
            "rome-food-security-summit", "T319", STAFF, BUSINESS, "JFK", "FCO", "2027-10-11", 32, 23, "business",
            "I'm presenting DESA's food-systems outlook at a summit hosted by FAO in Rome. I'd like to route via Istanbul "
            "to keep my Taurus status. A colleague said any route is fine as long as the cabin is right.",
        ),
        "routes": [
            route(
                "2027-10-11T15:40",
                ("T6 2", "T6", "JFK", "IST", 590, 0),
                ("T6 1361", "T6", "IST", "FCO", 165, 110),
                fares=(95000, 342000),
            ),
            route("2027-10-11T17:00", ("A4 140", "A4", "JFK", "FCO", 550, 0), fares=(82000, 310000)),
            route(
                "2027-10-11T18:30",
                ("A4 72", "A4", "JFK", "GVA", 465, 0),
                ("C3 1702", "C3", "GVA", "FCO", 95, 90),
                fares=(89000, 325000),
            ),
        ],
    },
    {
        "facts": trip(
            "bangkok-results-programme", "T320", STAFF, TRAINING, "NBO", "BKK", "2027-09-20", 30, 22, "business",
            "I've been nominated for the two-week results-based management programme at the ESCAP campus in Bangkok. "
            "The Lotus Sky nonstop is nine hours twenty, comfortably over the nine-hour line, and I'm a regular staff "
            "member, not a consultant, so business should be automatic. Please confirm.",
        ),
        "routes": [
            route("2027-09-20T23:40", ("L9 977", "L9", "NBO", "BKK", 560, 0), fares=(84200, 318000)),
            route(
                "2027-09-20T20:10",
                ("M8 722", "M8", "NBO", "DXB", 300, 0),
                ("M8 376", "M8", "DXB", "BKK", 360, 110),
                fares=(89600, 337000),
            ),
        ],
    },
    {
        "facts": trip(
            "nairobi-procurement-clinic", "T321", INSTRUCTOR, TRAINING, "VIE", "NBO", "2027-10-04", 35, 25, "business",
            "I'm delivering the procurement certification clinic at the Nairobi campus. Flying through Dubai is a "
            "twelve-hour-plus day, so business, and I prefer Meridian Gulf for the lie-flat seat. The Doha routing is a "
            "bit cheaper, but it's twenty minutes shorter, so same difference, surely.",
        ),
        "routes": [
            route(
                "2027-10-04T10:30",
                ("M8 130", "M8", "VIE", "DXB", 330, 0),
                ("M8 727", "M8", "DXB", "NBO", 300, 130),
                fares=(91400, 312000),
            ),
            route(
                "2027-10-04T11:15",
                ("D5 48", "D5", "VIE", "DOH", 320, 0),
                ("D5 1321", "D5", "DOH", "NBO", 310, 110),
                fares=(85700, 289000),
            ),
            route(
                "2027-10-04T12:00",
                ("T6 1888", "T6", "VIE", "IST", 140, 0),
                ("T6 609", "T6", "IST", "NBO", 390, 95),
                fares=(88300, 298000),
            ),
        ],
    },
    {
        "facts": trip(
            "geneva-statistics-briefing", "T322", STAFF, BUSINESS, "ADD", "GVA", "2027-11-08", 28, 20, "business",
            "I'm briefing the Statistical Commission's bureau in Geneva on the African census round. Addis to Istanbul "
            "is just under five hours, the connection is two hours and a minute, then four hours to Geneva: that adds up "
            "to eleven hours of travel, so I've proposed business on Taurus Anatolia.",
        ),
        "routes": [
            route(
                "2027-11-08T01:30",
                ("T6 702", "T6", "ADD", "IST", 299, 0),
                ("T6 1919", "T6", "IST", "GVA", 240, 121),
                fares=(71500, 262000),
            ),
            route(
                "2027-11-08T02:15",
                ("N7 870", "N7", "ADD", "CAI", 240, 0),
                ("N7 765", "N7", "CAI", "GVA", 245, 150),
                fares=(76800, 281000),
            ),
        ],
    },
    {
        "facts": trip(
            "mogadishu-logistics-survey", "T323", STAFF, BUSINESS, "VIE", "MGQ", "2028-03-10", 21, 16, "business",
            "I'm surveying warehouse capacity for the support office in Mogadishu. Vienna to Dubai, on to Nairobi, an "
            "overnight there and the morning hop to Mogadishu. I filed the request on 18 February and the ticket was "
            "issued on the 23rd, so with the leap day I make that three weeks and sixteen days exactly. Business, please.",
        ),
        "routes": [
            route(
                "2028-03-10T09:50",
                ("M8 132", "M8", "VIE", "DXB", 330, 0),
                ("M8 729", "M8", "DXB", "NBO", 300, 100),
                ("K2 455", "K2", "NBO", "MGQ", 100, 780),
                fares=(124800, 438000),
            ),
            route(
                "2028-03-10T10:20",
                ("D5 50", "D5", "VIE", "DOH", 320, 0),
                ("D5 1273", "D5", "DOH", "MGQ", 300, 1000),
                fares=(131500, 461000),
            ),
            route(
                "2028-03-10T07:05",
                ("N7 605", "N7", "VIE", "CAI", 200, 0),
                ("N7 917", "N7", "CAI", "MGQ", 320, 1200),
                fares=(128900, 452000),
            ),
        ],
    },
]

# Filler candidates per scenario, each leg (carrier, origin, destination, in-air minutes, minutes on the ground
# before it); check_fillers() proves none can change the hand-computed answer. Fares are (economy, business) cents.
FILLERS = {
    "geneva-council-session": [
        filler("2027-02-22T07:30", ("H3", "NBO", "ADD", 115, 0), ("H3", "ADD", "GVA", 410, 95), fares=(101900, 374000)),
        filler("2027-02-22T23:00", ("E9", "NBO", "FRA", 530, 0), ("E9", "FRA", "GVA", 60, 90), fares=(108800, 402000)),
        filler("2027-02-22T04:30", ("T6", "NBO", "IST", 400, 0), ("T6", "IST", "GVA", 215, 110), fares=(112600, 418000)),
        filler("2027-02-22T16:45", ("M8", "NBO", "DXB", 300, 0), ("M8", "DXB", "GVA", 410, 130), fares=(84900, 312000)),
        filler("2027-02-22T18:20", ("D5", "NBO", "DOH", 310, 0), ("D5", "DOH", "GVA", 390, 120), fares=(76200, 285000)),
    ],
    "nairobi-assembly-delegate": [
        filler("2027-02-26T07:20", ("T6", "GVA", "IST", 190, 0), ("T6", "IST", "NBO", 390, 100), fares=(105400, 384000)),
        filler("2027-02-26T14:50", ("D5", "GVA", "DOH", 360, 0), ("D5", "DOH", "NBO", 310, 110), fares=(88900, 322000)),
        filler("2027-02-26T13:30", ("M8", "GVA", "DXB", 375, 0), ("M8", "DXB", "NBO", 290, 120), fares=(92600, 338000)),
        filler("2027-02-26T08:10", ("E9", "GVA", "FRA", 60, 0), ("E9", "FRA", "NBO", 500, 95), fares=(99800, 361000)),
        filler("2027-02-26T06:45", ("B7", "GVA", "LHR", 100, 0), ("B7", "LHR", "NBO", 520, 120), fares=(110200, 399000)),
    ],
    "bangkok-statistics-keynote": [
        filler("2027-03-08T03:20", ("T6", "ADD", "IST", 300, 0), ("T6", "IST", "BKK", 560, 95), fares=(78300, 276000)),
        filler("2027-03-08T07:30", ("H3", "ADD", "NBO", 115, 0), ("H3", "NBO", "BKK", 560, 100), fares=(88700, 311000)),
        filler("2027-03-08T22:10", ("S2", "ADD", "DEL", 330, 0), ("S2", "DEL", "BKK", 250, 110), fares=(96400, 339000)),
        filler("2027-03-08T04:00", ("N7", "ADD", "CAI", 240, 0), ("N7", "CAI", "BKK", 600, 130), fares=(81500, 287000)),
        filler("2027-03-08T10:15", ("D5", "ADD", "DOH", 230, 0), ("D5", "DOH", "BKK", 370, 240), fares=(93800, 331000)),
    ],
    "addis-ababa-budget-review": [
        filler("2027-03-15T09:40", ("S2", "BKK", "DEL", 250, 0), ("S2", "DEL", "ADD", 330, 100), fares=(86100, 302000)),
        filler("2027-03-15T02:05", ("H3", "BKK", "NBO", 560, 0), ("H3", "NBO", "ADD", 115, 110), fares=(90900, 318000)),
        filler("2027-03-15T23:10", ("T6", "BKK", "IST", 560, 0), ("T6", "IST", "ADD", 300, 150), fares=(77800, 274000)),
        filler("2027-03-15T08:50", ("N7", "BKK", "CAI", 600, 0), ("N7", "CAI", "ADD", 240, 120), fares=(80600, 285000)),
        filler("2027-03-15T20:30", ("M8", "BKK", "DXB", 360, 0), ("M8", "DXB", "ADD", 219, 200), fares=(94200, 329000)),
    ],
    "vienna-ozone-workshop": [
        filler("2027-04-12T09:15", ("M8", "NBO", "DXB", 300, 0), ("M8", "DXB", "VIE", 360, 100), fares=(95800, 331000)),
        filler("2027-04-12T10:40", ("D5", "NBO", "DOH", 310, 0), ("D5", "DOH", "VIE", 350, 130), fares=(99100, 342000)),
        filler("2027-04-12T06:20", ("H3", "NBO", "ADD", 115, 0), ("H3", "ADD", "VIE", 400, 140), fares=(90200, 309000)),
        filler("2027-04-12T23:50", ("E9", "NBO", "FRA", 530, 0), ("E9", "FRA", "VIE", 80, 90), fares=(104300, 359000)),
        filler("2027-04-12T08:00", ("B7", "NBO", "LHR", 525, 0), ("B7", "LHR", "VIE", 130, 400), fares=(79800, 272000)),
    ],
    "panama-hub-retreat": [
        filler("2027-04-19T08:40", ("P5", "SCL", "LIM", 210, 0), ("P5", "LIM", "PTY", 230, 220), fares=(64100, 221000)),
        filler("2027-04-19T04:30", ("V4", "SCL", "BOG", 330, 0), ("V4", "BOG", "PTY", 80, 330), fares=(69700, 241000)),
        filler("2027-04-19T07:00", ("S2", "SCL", "LIM", 210, 0), ("S2", "LIM", "BOG", 190, 300), ("S2", "BOG", "PTY", 80, 150), fares=(52300, 181000)),
        filler("2027-04-19T01:20", ("A4", "SCL", "MIA", 510, 0), ("A4", "MIA", "PTY", 165, 420), fares=(58200, 199000)),
    ],
    "mogadishu-field-mission": [
        filler("2027-05-03T11:30", ("T6", "GVA", "IST", 190, 0), ("T6", "IST", "MGQ", 350, 900), fares=(115600, 414000)),
        filler("2027-05-03T21:40", ("H3", "GVA", "ADD", 400, 0), ("H3", "ADD", "MGQ", 120, 1000), fares=(121400, 437000)),
        filler("2027-05-03T10:05", ("K2", "GVA", "NBO", 540, 0), ("K2", "NBO", "MGQ", 100, 1100), fares=(104800, 376000)),
        filler("2027-05-03T12:50", ("N7", "GVA", "CAI", 245, 0), ("N7", "CAI", "MGQ", 320, 1300), fares=(99500, 358000)),
    ],
    "kabul-mission-handover": [
        filler("2027-05-10T04:30", ("T6", "NBO", "IST", 400, 0), ("T6", "IST", "KBL", 300, 900), fares=(97200, 349000)),
        filler("2027-05-10T15:20", ("S2", "NBO", "DEL", 400, 0), ("S2", "DEL", "KBL", 120, 1000), fares=(113800, 405000)),
        filler("2027-05-10T22:05", ("M8", "NBO", "DXB", 300, 0), ("M8", "DXB", "KBL", 200, 1120), fares=(92600, 334000)),
        filler("2027-05-10T18:40", ("D5", "NBO", "DOH", 330, 0), ("D5", "DOH", "KBL", 240, 980), fares=(100900, 362000)),
    ],
    "amman-refugee-briefing": [
        filler("2027-05-24T06:30", ("C3", "GVA", "FCO", 95, 0), ("C3", "FCO", "AMM", 215, 120), fares=(52600, 163000)),
        filler("2027-05-24T10:15", ("B7", "GVA", "VIE", 95, 0), ("B7", "VIE", "AMM", 220, 150), fares=(56900, 175000)),
        filler("2027-05-24T12:40", ("N7", "GVA", "CAI", 245, 0), ("N7", "CAI", "AMM", 90, 200), fares=(41300, 131000)),
        filler("2027-05-24T08:05", ("E9", "GVA", "FRA", 60, 0), ("E9", "FRA", "AMM", 250, 110), fares=(58400, 181000)),
        filler("2027-05-24T14:30", ("D5", "GVA", "DOH", 360, 0), ("D5", "DOH", "AMM", 180, 180), fares=(38900, 124000)),
    ],
    "beirut-donor-roundtable": [
        filler("2027-06-07T07:45", ("C3", "VIE", "FCO", 100, 0), ("C3", "FCO", "BEY", 200, 110), fares=(61700, 182000)),
        filler("2027-06-07T09:20", ("L2", "VIE", "AMM", 220, 0), ("L2", "AMM", "BEY", 60, 120), fares=(64900, 191000)),
        filler("2027-06-07T12:10", ("N7", "VIE", "CAI", 200, 0), ("N7", "CAI", "BEY", 75, 300), fares=(42800, 128000)),
        filler("2027-06-07T05:50", ("E9", "VIE", "FRA", 80, 0), ("E9", "FRA", "BEY", 240, 140), fares=(47100, 141000)),
        filler("2027-06-07T14:35", ("D5", "VIE", "DOH", 320, 0), ("D5", "DOH", "BEY", 200, 180), fares=(36200, 109000)),
    ],
    "nairobi-interviewer": [
        filler("2027-06-14T18:30", ("B7", "JFK", "LHR", 420, 0), ("B7", "LHR", "NBO", 520, 120), fares=(151900, 533000)),
        filler("2027-06-14T17:15", ("E9", "JFK", "CDG", 430, 0), ("E9", "CDG", "NBO", 510, 150), fares=(129800, 456000)),
        filler("2027-06-14T22:40", ("M8", "JFK", "DXB", 760, 0), ("M8", "DXB", "NBO", 290, 180), fares=(124600, 439000)),
        filler("2027-06-14T19:05", ("B7", "JFK", "AMS", 430, 0), ("B7", "AMS", "NBO", 505, 95), fares=(145300, 509000)),
        filler("2027-06-14T21:50", ("D5", "JFK", "DOH", 740, 0), ("D5", "DOH", "NBO", 310, 200), fares=(133700, 471000)),
    ],
    "vienna-narcotics-commission": [
        filler("2027-03-01T18:10", ("E9", "JFK", "FRA", 450, 0), ("E9", "FRA", "VIE", 80, 90), fares=(79100, 293000)),
        filler("2027-03-01T19:25", ("B7", "JFK", "AMS", 430, 0), ("B7", "AMS", "VIE", 110, 110), fares=(83600, 309000)),
        filler("2027-03-01T21:00", ("B7", "JFK", "LHR", 420, 0), ("B7", "LHR", "VIE", 130, 150), fares=(86900, 321000)),
        filler("2027-03-01T15:35", ("E9", "JFK", "CDG", 430, 0), ("E9", "CDG", "VIE", 120, 300), fares=(69800, 258000)),
        filler("2027-03-01T22:15", ("C3", "JFK", "FCO", 550, 0), ("C3", "FCO", "VIE", 95, 250), fares=(72500, 269000)),
    ],
    "geneva-trade-forum": [
        filler("2027-03-22T18:00", ("E9", "JFK", "FRA", 450, 0), ("E9", "FRA", "GVA", 60, 80), fares=(72100, 268000)),
        filler("2027-03-22T20:40", ("B7", "JFK", "LHR", 420, 0), ("B7", "LHR", "GVA", 100, 120), fares=(77600, 288000)),
        filler("2027-03-22T19:15", ("E9", "JFK", "CDG", 430, 0), ("E9", "CDG", "GVA", 70, 100), fares=(80900, 299000)),
        filler("2027-03-22T16:50", ("B7", "JFK", "AMS", 430, 0), ("B7", "AMS", "GVA", 100, 280), fares=(63400, 236000)),
        filler("2027-03-22T21:30", ("C3", "JFK", "FCO", 550, 0), ("C3", "FCO", "GVA", 95, 200), fares=(66200, 247000)),
    ],
    "bangkok-disaster-drill": [
        filler("2027-04-05T10:30", ("D5", "VIE", "DOH", 320, 0), ("D5", "DOH", "BKK", 370, 120), fares=(89800, 341000)),
        filler("2027-04-05T12:15", ("T6", "VIE", "IST", 140, 0), ("T6", "IST", "BKK", 560, 150), fares=(71400, 272000)),
        filler("2027-04-05T11:05", ("S2", "VIE", "DEL", 440, 0), ("S2", "DEL", "BKK", 250, 130), fares=(83100, 316000)),
        filler("2027-04-05T07:50", ("E9", "VIE", "FRA", 80, 0), ("E9", "FRA", "BKK", 650, 200), fares=(75600, 288000)),
        filler("2027-04-05T06:20", ("M8", "VIE", "DXB", 330, 0), ("M8", "DXB", "BKK", 360, 400), fares=(68200, 259000)),
    ],
    "new-york-hlpf-panel": [
        filler("2027-07-12T08:30", ("B7", "NBO", "LHR", 525, 0), ("B7", "LHR", "JFK", 480, 130), fares=(162900, 571000)),
        filler("2027-07-12T07:45", ("E9", "NBO", "CDG", 520, 0), ("E9", "CDG", "JFK", 500, 200), fares=(139700, 494000)),
        filler("2027-07-12T04:10", ("M8", "NBO", "DXB", 300, 0), ("M8", "DXB", "JFK", 850, 180), fares=(134200, 476000)),
        filler("2027-07-12T09:20", ("B7", "NBO", "AMS", 520, 0), ("B7", "AMS", "JFK", 490, 140), fares=(154800, 545000)),
        filler("2027-07-12T06:00", ("E9", "NBO", "FRA", 530, 0), ("E9", "FRA", "JFK", 510, 300), fares=(144600, 511000)),
    ],
    "santiago-logistician": [
        filler("2027-08-02T17:30", ("V4", "JFK", "LIM", 480, 0), ("V4", "LIM", "SCL", 210, 120), fares=(101600, 373000)),
        filler("2027-08-02T16:10", ("V4", "JFK", "BOG", 340, 0), ("V4", "BOG", "SCL", 370, 150), fares=(107900, 395000)),
        filler("2027-08-02T14:45", ("A4", "JFK", "MIA", 190, 0), ("A4", "MIA", "SCL", 510, 240), fares=(89400, 332000)),
        filler("2027-08-02T12:20", ("A4", "JFK", "PTY", 330, 0), ("A4", "PTY", "SCL", 400, 300), fares=(93800, 349000)),
    ],
    "bangkok-water-dialogue": [
        filler("2027-08-16T10:20", ("M8", "GVA", "DXB", 375, 0), ("M8", "DXB", "BKK", 360, 100), fares=(81500, 309000)),
        filler("2027-08-16T07:35", ("T6", "GVA", "IST", 190, 0), ("T6", "IST", "BKK", 560, 110), fares=(72600, 277000)),
        filler("2027-08-16T06:50", ("E9", "GVA", "FRA", 60, 0), ("E9", "FRA", "BKK", 650, 160), fares=(75900, 289000)),
        filler("2027-08-16T13:05", ("S2", "GVA", "DEL", 450, 0), ("S2", "DEL", "BKK", 250, 130), fares=(87300, 330000)),
        filler("2027-08-16T15:40", ("D5", "GVA", "DOH", 360, 0), ("D5", "DOH", "BKK", 370, 400), fares=(69100, 263000)),
    ],
    "vienna-miles-collector": [
        filler("2027-09-06T03:30", ("D5", "NBO", "DOH", 310, 0), ("D5", "DOH", "VIE", 350, 130), fares=(96500, 334000)),
        filler("2027-09-06T06:10", ("H3", "NBO", "ADD", 115, 0), ("H3", "ADD", "VIE", 400, 170), fares=(103400, 362000)),
        filler("2027-09-06T23:20", ("E9", "NBO", "FRA", 530, 0), ("E9", "FRA", "VIE", 80, 90), fares=(118700, 411000)),
        filler("2027-09-06T08:45", ("B7", "NBO", "LHR", 525, 0), ("B7", "LHR", "VIE", 130, 420), fares=(74200, 262000)),
        filler("2027-09-06T07:00", ("S2", "NBO", "JNB", 250, 0), ("S2", "JNB", "VIE", 650, 300), fares=(83600, 290000)),
    ],
    "rome-food-security-summit": [
        filler("2027-10-11T18:50", ("E9", "JFK", "CDG", 430, 0), ("E9", "CDG", "FCO", 125, 100), fares=(85600, 317000)),
        filler("2027-10-11T19:40", ("B7", "JFK", "LHR", 420, 0), ("B7", "LHR", "FCO", 150, 130), fares=(91800, 333000)),
        filler("2027-10-11T16:30", ("E9", "JFK", "FRA", 450, 0), ("E9", "FRA", "FCO", 105, 110), fares=(98900, 356000)),
        filler("2027-10-11T20:15", ("B7", "JFK", "AMS", 430, 0), ("B7", "AMS", "FCO", 130, 350), fares=(76300, 288000)),
        filler("2027-10-11T21:05", ("A4", "JFK", "VIE", 525, 0), ("A4", "VIE", "FCO", 95, 300), fares=(79400, 299000)),
    ],
    "bangkok-results-programme": [
        filler("2027-09-20T22:30", ("D5", "NBO", "DOH", 310, 0), ("D5", "DOH", "BKK", 370, 150), fares=(77300, 294000)),
        filler("2027-09-20T04:15", ("T6", "NBO", "IST", 400, 0), ("T6", "IST", "BKK", 560, 120), fares=(72800, 276000)),
        filler("2027-09-20T07:30", ("H3", "NBO", "ADD", 115, 0), ("H3", "ADD", "BKK", 520, 130), fares=(93100, 351000)),
        filler("2027-09-20T09:45", ("S2", "NBO", "JNB", 250, 0), ("S2", "JNB", "BKK", 690, 200), fares=(69500, 262000)),
    ],
    "nairobi-procurement-clinic": [
        filler("2027-10-04T07:20", ("E9", "VIE", "FRA", 80, 0), ("E9", "FRA", "NBO", 500, 120), fares=(96800, 331000)),
        filler("2027-10-04T08:05", ("B7", "VIE", "LHR", 130, 0), ("B7", "LHR", "NBO", 520, 150), fares=(101500, 347000)),
        filler("2027-10-04T13:40", ("N7", "VIE", "CAI", 230, 0), ("N7", "CAI", "NBO", 300, 400), fares=(79900, 268000)),
        filler("2027-10-04T21:10", ("S2", "VIE", "ADD", 400, 0), ("S2", "ADD", "NBO", 115, 300), fares=(105200, 362000)),
    ],
    "geneva-statistics-briefing": [
        filler("2027-11-08T00:40", ("H3", "ADD", "FRA", 440, 0), ("H3", "FRA", "GVA", 60, 140), fares=(80400, 294000)),
        filler("2027-11-08T03:50", ("M8", "ADD", "DXB", 220, 0), ("M8", "DXB", "GVA", 410, 130), fares=(84900, 309000)),
        filler("2027-11-08T06:15", ("D5", "ADD", "DOH", 230, 0), ("D5", "DOH", "GVA", 390, 400), fares=(64200, 236000)),
        filler("2027-11-08T08:30", ("K2", "ADD", "NBO", 115, 0), ("K2", "NBO", "GVA", 540, 300), fares=(67900, 249000)),
        filler("2027-11-08T23:55", ("B7", "ADD", "LHR", 470, 0), ("B7", "LHR", "GVA", 100, 110), fares=(89300, 326000)),
    ],
    "mogadishu-logistics-survey": [
        filler("2028-03-10T11:30", ("T6", "VIE", "IST", 140, 0), ("T6", "IST", "ADD", 300, 150), ("T6", "ADD", "MGQ", 120, 920), fares=(136200, 477000)),
        filler("2028-03-10T06:40", ("M8", "VIE", "DXB", 330, 0), ("M8", "DXB", "MGQ", 290, 1300), fares=(109600, 384000)),
        filler("2028-03-10T08:15", ("H3", "VIE", "ADD", 400, 0), ("H3", "ADD", "MGQ", 120, 1420), fares=(115300, 404000)),
    ],
}


def chain(airports, spec):
    """The segment specs of a route, each (flight, marketing, operating, origin, destination, local departure,
    in-air minutes) as worldgen.segment takes them: each flight leaves its layover's minutes after the last landed."""
    specs, landed = [], None
    for flight, carrier, origin, destination, minutes, layover in spec["legs"]:
        if landed is None:
            depart_local = spec["first"]
        else:
            departs = landed + timedelta(minutes=layover)
            depart_local = departs.astimezone(ZoneInfo(airports[origin]["timezone"])).strftime("%Y-%m-%dT%H:%M")
        specs.append((flight, carrier, carrier, origin, destination, depart_local, minutes))
        record = segment(airports, "probe", *specs[-1])
        landed = datetime.strptime(record["arrive_utc"], UTC_FORMAT).replace(tzinfo=ZoneInfo("UTC"))
    return specs


def build():
    """Every fixture file this generator writes: {path relative to data/: its text}."""
    airports = {
        code: {"code": code, "city": city, "country": country, "continental_us": continental, "us_50_states_dc": us, "timezone": tz}
        for code, city, country, continental, us, tz in AIRPORTS
    }
    carriers = [
        {"code": code, "name": name, "us_flag_carrier": us_flag, "codeshare_partners": partners}
        for code, name, us_flag, partners in CARRIERS
    ]
    travelers = [
        {"traveler_id": traveler_id, "name": name, "department": department, "base_point": base}
        for traveler_id, name, department, base in TRAVELERS
    ]
    if sorted(FILLERS) != sorted(scenario["facts"]["scenario"] for scenario in SCENARIOS):
        raise ValueError("FILLERS must name every scenario once")
    pools = []
    for scenario in SCENARIOS:
        fillers = FILLERS[scenario["facts"]["scenario"]]
        check_fillers(scenario["facts"]["scenario"], scenario["routes"], fillers)
        pools.append([*scenario["routes"], *fillers])
    count = sum(len(pool) for pool in pools)
    numbers = random.Random(SEED).sample(range(100, 1000), count)
    segments, itineraries, files, numbered = {}, [], {}, 0
    for scenario, pool in zip(SCENARIOS, pools, strict=True):
        facts = dict(scenario["facts"])
        for index, spec in enumerate(pool):
            if spec.get("filler"):
                legs = []
                for leg in spec["legs"]:
                    numbered += 1
                    legs.append((f"{leg[1]} {3000 + numbered}", *leg[1:]))  # fillers fly numbers 3001 and up
                spec = {**spec, "legs": tuple(legs)}
            records = []
            for flight in chain(airports, spec):
                if flight not in segments:
                    segments[flight] = segment(airports, f"S{len(segments) + 1:03d}", *flight)
                records.append(segments[flight])
            economy, business = spec["fares"]
            fares = {"economy": economy, "premium_economy": None, "business": business, "first": None}
            itineraries.append(itinerary(f"I{numbers[len(itineraries)]}", records, fares))
            if index == 0:
                facts["proposed_itinerary_id"] = itineraries[-1]["itinerary_id"]
        files[f"scenarios/{facts['scenario']}.json"] = json_text(facts)
    files["airports.json"] = json_text(list(airports.values()))
    files["carriers.json"] = json_text(carriers)
    files["segments.json"] = json_text(list(segments.values()))
    files["itineraries.json"] = json_text(sorted(itineraries, key=lambda record: record["itinerary_id"]))
    files["travelers.json"] = json_text(travelers)
    return files


def main():
    for relative, text in build().items():
        (DATA / relative).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
