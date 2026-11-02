"""The seeded generator of this plugin's fixtures (development only): `uv run python -m plugin.tools_dev.generate`
rewrites src/plugin/data/ (except handbook.md). The committed files are the source of truth; a test checks
this generator still reproduces them byte for byte.

Each scenario's flights are written out by hand, because each one sets a trap from the brief (TRAVEL_POLICY_
TASKS_CONTEXT.md section 4, T3, with the Rev.1 decisions); the seed only scatters the itinerary ids, so the
proposed itinerary is never simply the first or lowest id. Airlines, flight numbers, schedules and fares are
fictional. Expected answers are not written here: they live in tests/cases/.
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
    ("BEY", "Beirut", "LB", False, False, "Asia/Beirut"),
    ("BKK", "Bangkok", "TH", False, False, "Asia/Bangkok"),
    ("BOG", "Bogota", "CO", False, False, "America/Bogota"),
    ("CAI", "Cairo", "EG", False, False, "Africa/Cairo"),
    ("DOH", "Doha", "QA", False, False, "Asia/Qatar"),
    ("DXB", "Dubai", "AE", False, False, "Asia/Dubai"),
    ("FCO", "Rome Fiumicino", "IT", False, False, "Europe/Rome"),
    ("GVA", "Geneva", "CH", False, False, "Europe/Zurich"),
    ("IST", "Istanbul", "TR", False, False, "Europe/Istanbul"),
    ("JFK", "New York JFK", "US", True, True, "America/New_York"),
    ("KBL", "Kabul", "AF", False, False, "Asia/Kabul"),
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
    ("C3", "Cedar Crescent", False, []),
    ("D5", "Dune Pearl Airways", False, []),
    ("H3", "Highland Rift Airways", False, []),
    ("K2", "Kestrel Airways", False, []),
    ("L2", "Lumen Levant", False, []),
    ("L9", "Lotus Sky", False, []),
    ("M8", "Meridian Gulf", False, []),
    ("N7", "Nilegate Air", False, []),
    ("P5", "Pacific Condor", False, []),
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
]


def route(first_depart_local, *legs, fares):
    """An itinerary spec: its first flight leaves at ``first_depart_local``; each leg is
    (flight, carrier, origin, destination, in-air minutes, minutes on the ground before it)."""
    return {"first": first_depart_local, "legs": legs, "fares": fares}


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
]


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
    count = sum(len(scenario["routes"]) for scenario in SCENARIOS)
    numbers = random.Random(SEED).sample(range(100, 1000), count)
    segments, itineraries, files = {}, [], {}
    for scenario in SCENARIOS:
        facts = dict(scenario["facts"])
        for index, spec in enumerate(scenario["routes"]):
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
