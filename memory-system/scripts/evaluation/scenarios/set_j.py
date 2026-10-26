"""SET J: validation of note consolidation. 26 questions.

Status: BLIND. Written before any consolidation code exists. Run once on the current system
(notes only, consolidation not built), then once after consolidation is built. Never tuned on.
Predictions and the proposed design: docs/predictions/set_J.md.

Each user tells 10 to 20 episode messages, most of them older than 30 days, so that old notes
pile up and can be merged into digests. The questions ask for the details a digest may drop
(a price, a name, a cause), the final state of a plan or choice that changed, who did what
when several people appear, and typed facts that a digest must not pollute. `j_recent` is a
control: every message is under 30 days old, so nothing should be consolidated there.
All people, places and topics are new; none appear in sets A to I.
"""

from .common import ABSTAIN, assert_no_leaks, spread

J_FILLER = [
    "How do tides work?",
    "What's the difference between weather and climate?",
    "Can you explain what a prime number is?",
    "How do I write a good cover letter?",
    "Why do leaves change colour in autumn?",
    "What's a healthy amount of water to drink a day?",
    "How do noise-cancelling headphones work?",
    "What's the speed of sound?",
]

SCENARIOS = [
    {
        # one long story with a changed choice, a cause, a price that changed, a person;
        # plus two recent messages that must stay as plain notes
        "id": "j_renovation",
        "kind": "story",
        "messages": [
            (200, "We finally started renovating the kitchen in our old farmhouse."),
            (192, "The contractor, a guy named Tobias, quoted us 18,000 euros for the kitchen."),
            (184, "We picked dark green cabinets for the kitchen."),
            (176, "The old floor tiles turned out to contain asbestos, so the work stopped for two weeks."),
            (168, "Tobias's crew finished tearing out the old kitchen walls."),
            (160, "We changed our minds and went with oak cabinets instead of the green ones."),
            (150, "The new oven arrived with a big dent, so we sent it back."),
            (142, "The replacement oven was installed without any problems."),
            (130, "The kitchen countertop is a slab of grey granite."),
            (120, "The final bill for the kitchen came to 21,500 euros, more than the quote."),
            (110, "We hosted our first dinner in the new kitchen for eight friends."),
            (95, "My brother-in-law Henrik helped me fix the leaking roof over the barn."),
            (85, "Henrik fell off the ladder while fixing the roof but only sprained his ankle."),
            (70, "We painted the barn doors red after the roof was done."),
            (12, "Last week I planted tomatoes in the vegetable patch behind the farmhouse."),
            (5, "A hedgehog has started sleeping under our woodpile."),
        ]
        + spread(J_FILLER[:4], 20, 180),
        "questions": [
            {
                "q": "What are my kitchen cabinets made of?",
                "expect": [["oak"]],
                "needs": ["oak"],
            },
            {
                "q": "Why did the kitchen work stop?",
                "expect": [["asbestos"]],
                "needs": ["asbestos"],
            },
            {
                "q": "How much did the kitchen cost in the end?",
                "expect": [["21,500", "21500", "21 500", "21.500"]],
                "needs": ["500"],
                "stale": ["18,000", "18000", "18 000"],
            },
            {
                "q": "Who hurt himself fixing the barn roof?",
                "expect": [["henrik"]],
                "needs": ["henrik"],
            },
            {
                "q": "What did I plant last week?",
                "expect": [["tomato"]],
                "needs": ["tomato"],
            },
        ],
    },
    {
        # several trips in one year: a digest must not mix details across trips;
        # one plan changes date in a recent message, after the old notes are digested
        "id": "j_travels",
        "kind": "episodes",
        "messages": [
            (300, "In January I spent a week in Reykjavik with my friend Sunniva and we soaked in the hot springs."),
            (296, "Our flight to Reykjavik was delayed by nine hours because of a snowstorm."),
            (250, "In March I travelled to Marrakech on my own and took a cooking class."),
            (246, "At the cooking class in Marrakech I learned to make a lamb tagine."),
            (200, "In May I took the night train to Vienna with my partner Joel."),
            (196, "In Vienna we went to a string quartet concert and the tickets were 140 euros each."),
            (150, "In July I went camping in the Dolomites and we got caught in a hailstorm."),
            (146, "My camera got soaked and broke in the hailstorm in the Dolomites."),
            (120, "I bought a replacement camera, a used Fujifilm, for 600 euros."),
            (60, "I'm planning a trip to Hanoi with Joel at the end of the year."),
            (52, "I booked the Hanoi flights, we fly out on December 12."),
            (14, "We moved the Hanoi trip to February because Joel has a project deadline in December."),
        ]
        + spread(J_FILLER[2:6], 20, 280),
        "questions": [
            {
                "q": "Who did I go to Reykjavik with?",
                "expect": [["sunniva"]],
                "needs": ["sunniva"],
                "avoid": ["joel"],
            },
            {
                "q": "What did I learn to cook in Marrakech?",
                "expect": [["tagine"]],
                "needs": ["tagine"],
            },
            {
                "q": "Why was my flight to Reykjavik delayed?",
                "expect": [["snow"]],
                "needs": ["snow"],
            },
            {
                "q": "What happened to my camera?",
                "expect": [["hail", "soak", "wet", "broke"]],
                "needs": ["hail"],
            },
            {
                "q": "How much did I pay for my new camera?",
                "expect": [["600"]],
                "needs": ["600"],
            },
            {
                "q": "When am I going to Hanoi?",
                "expect": [["february"]],
                "needs": ["february"],
                "stale": ["december 12", "12 december"],
            },
        ],
    },
    {
        # a band story with other people: who did what must survive a merge
        "id": "j_band",
        "kind": "story",
        "messages": [
            (240, "I joined a small folk band as the fiddle player."),
            (232, "Our singer, Margit, writes most of the band's songs."),
            (224, "We played our first gig at a pub called The Copper Kettle."),
            (220, "Only twelve people came to the first gig, but they loved it."),
            (200, "Margit's brother Ansel joined the band on accordion."),
            (180, "We recorded a five-song EP in Ansel's garage."),
            (172, "We called the band's EP Low Tide."),
            (150, "Margit quit the band to move to Canada."),
            (140, "Since Margit left, I sing lead as well as playing the fiddle."),
            (115, "We played the Harbourfest festival and about four hundred people watched us."),
            (108, "Ansel snapped his accordion strap in the middle of the Harbourfest set."),
            (40, "The band is taking a break over the winter."),
        ]
        + spread(J_FILLER[4:8], 20, 220),
        "questions": [
            {
                "q": "What instrument do I play in the band?",
                "expect": [["fiddle", "violin"]],
                "needs": ["fiddle"],
            },
            {
                "q": "Who moved to Canada?",
                "expect": [["margit"]],
                "needs": ["margit", "canada"],
            },
            {
                "q": "What is our EP called?",
                "expect": [["low tide"]],
                "needs": ["low tide"],
            },
            {
                "q": "Where did we play our first gig?",
                "expect": [["copper kettle"]],
                "needs": ["copper"],
            },
            {
                "q": "How many people watched us at Harbourfest?",
                "expect": [["400", "four hundred"]],
                "needs": ["hundred"],
            },
        ],
    },
    {
        # typed facts mixed with episodes: digests must not pollute facts or bring back
        # a replaced city; details of small episodes must survive
        "id": "j_control_mix",
        "kind": "control",
        "messages": [
            (260, "My name is Oskar and I live in Aarhus."),
            (255, "I work as an archivist at the city library."),
            (250, "I'm allergic to kiwi."),
            (235, "I volunteered at a book fair and sold boxes of old maps."),
            (210, "I adopted two chickens called Hilde and Rosa."),
            (200, "Rosa escaped into the neighbour's garden and ate his lettuce."),
            (180, "I repainted my bicycle bright yellow."),
            (150, "I moved to Bergen last week, and the movers scratched my piano."),
            (140, "The removal company paid for a technician to repair the piano scratch."),
            (120, "I started restoring an old wooden rowing boat."),
            (105, "The rowing boat needs new oarlocks before it can go in the water."),
            (90, "I found brass oarlocks for the rowing boat at a flea market for 45 euros."),
            (75, "The rowing boat went in the water for the first time and didn't leak."),
        ]
        + spread(J_FILLER[:4], 20, 240),
        "questions": [
            {
                "q": "Which city do I live in?",
                "expect": [["bergen"]],
                "needs": ["bergen"],
                "stale": ["aarhus"],
            },
            {
                "q": "What am I allergic to?",
                "expect": [["kiwi"]],
                "needs": ["kiwi"],
            },
            {
                "q": "What did the movers damage?",
                "expect": [["piano"]],
                "needs": ["piano"],
            },
            {
                "q": "What are my chickens called?",
                "expect": [["hilde"], ["rosa"]],
                "needs": ["hilde", "rosa"],
            },
            {
                "q": "How much did I pay for the oarlocks?",
                "expect": [["45"]],
                "needs": ["45"],
            },
            {
                "q": "What colour is my bicycle?",
                "expect": [["yellow"]],
                "needs": ["yellow"],
            },
            {
                "q": "What did I name my cat?",
                "expect": [ABSTAIN],
                "avoid": ["hilde", "rosa"],
            },
        ],
    },
    {
        # control: every episode is under 30 days old, so nothing here should be digested
        "id": "j_recent",
        "kind": "control",
        "messages": [
            (26, "My daughter Lotte lost her first tooth."),
            (24, "We went to a planetarium show about black holes."),
            (22, "I fixed the washing machine myself by following an online video."),
            (20, "My car failed its inspection because the brakes were worn out."),
            (18, "The garage replaced the brakes for 320 euros."),
            (15, "Lotte came second in the school spelling contest."),
            (12, "We had a picnic by the lake and a swan stole our sandwiches."),
            (9, "I signed Lotte up for swimming lessons on Thursdays."),
            (6, "The swimming lessons got moved to Tuesdays."),
            (3, "Lotte swam her first full length of the pool."),
        ]
        + spread(J_FILLER[4:8], 2, 25),
        "questions": [
            {
                "q": "Why did my car fail its inspection?",
                "expect": [["brake"]],
                "needs": ["brake"],
            },
            {
                "q": "What day are Lotte's swimming lessons?",
                "expect": [["tuesday"]],
                "needs": ["tuesday"],
                "stale": ["thursday"],
            },
            {
                "q": "What place did Lotte get in the spelling contest?",
                "expect": [["second", "2nd"]],
                "needs": ["second"],
            },
        ],
    },
]

assert_no_leaks("J", J_FILLER, SCENARIOS)
