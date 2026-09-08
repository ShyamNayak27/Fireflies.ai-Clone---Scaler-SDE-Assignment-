"""Fictional seed meeting — see meeting_01 module docstring."""

MEETING = {
    "title": "Sprint Retro — Detection & Retrofit Track",
    "started_at": "2026-09-05T18:00:00+00:00",
    "source": "seed",
    "participants": [
        {"name": "Maya Ferreira", "email": "maya@solsticeanalytics.dev", "is_host": True},
        {"name": "Owen Kessler", "email": "owen@solsticeanalytics.dev"},
        {"name": "Devon Ashworth", "email": "devon@solsticeanalytics.dev"},
        {"name": "Priya Raman", "email": "priya@solsticeanalytics.dev"},
        {"name": "Marcus Webb", "email": "marcus@solsticeanalytics.dev"},
    ],
    "tags": ["retro", "engineering"],
    "dialogue": [
        (
            "Maya Ferreira",
            "Let's do the usual format, what went well, what didn't, one thing to change. I'll start us off, what went well this sprint?",
        ),
        (
            "Priya Raman",
            "The dashboard performance fix went really smoothly, cold start's under two seconds now and it hasn't regressed.",
        ),
        (
            "Devon Ashworth",
            "The relabeling pass on the crack dataset actually turned out to be quick once Priya jumped in, recall's back up without losing precision.",
        ),
        (
            "Marcus Webb",
            "For me, first two weeks, getting the event-triggered sampling working on the sensor pod felt good, we're already seeing better battery numbers in early bench tests.",
        ),
        ("Owen Kessler", "Good sprint overall I'd say. What didn't go well?"),
        (
            "Devon Ashworth",
            "I'll be honest, I lost about a day chasing what I thought was a model bug that turned out to be a labeling inconsistency. Should have checked the data before the model.",
        ),
        ("Maya Ferreira", "That's a fair lesson, not a blocker exactly but worth noting."),
        (
            "Priya Raman",
            "For me, the satellite imagery rate limit thing is still unresolved, it's not blocking anything today but it's been sitting for over two weeks now without a response from the vendor.",
        ),
        ("Owen Kessler", "Do we have an escalation path with them or are we just waiting?"),
        ("Priya Raman", "Just waiting on a support ticket right now, I haven't tried escalating."),
        (
            "Maya Ferreira",
            "Let's escalate this week, even if it's not urgent, two weeks of silence isn't a good sign for when we actually need them responsive.",
        ),
        (
            "Marcus Webb",
            "Nothing major from me on the didn't-go-well side, though I'll say the firmware repo could use a README, took me longer than it should have to find the build instructions.",
        ),
        (
            "Devon Ashworth",
            "Yeah that's fair, I'll write one up, it's been on my list for a while.",
        ),
        (
            "Maya Ferreira",
            "Good, let's make that this week's small thing. Okay, one change for next sprint, what's everyone got?",
        ),
        (
            "Devon Ashworth",
            "Check the data before assuming it's a model problem, going to hold myself to that.",
        ),
        ("Priya Raman", "I'll escalate the vendor issue by Wednesday instead of letting it sit."),
        (
            "Owen Kessler",
            "I want us to get better at flagging integration asks from customers earlier, the Meridian ticketing thing sat for a bit before anyone scoped it.",
        ),
        (
            "Marcus Webb",
            "I'll add basic docs to anything I touch going forward, starting with the firmware README.",
        ),
        (
            "Maya Ferreira",
            "Good round. I'll take the vendor escalation topic and make sure it's not just Priya carrying it alone. Thanks everyone, good sprint.",
        ),
    ],
    "chapters": [
        {
            "title": "What Went Well",
            "segment_range": (0, 3),
            "notes": [
                {
                    "text": "Dashboard cold-start fix shipped cleanly, holding under 2 seconds with no regression.",
                    "segment_idx": 1,
                },
                {
                    "text": "Crack-dataset relabeling resolved the recall drop without hurting precision.",
                    "segment_idx": 2,
                },
                {
                    "text": "Event-triggered sampling on the sensor pod already shows improved bench battery numbers.",
                    "segment_idx": 3,
                },
            ],
        },
        {
            "title": "What Didn't Go Well",
            "segment_range": (4, 12),
            "notes": [
                {
                    "text": "A day was lost chasing a suspected model bug that was actually a labeling issue.",
                    "segment_idx": 5,
                },
                {
                    "text": "Satellite imagery vendor rate-limit ticket has been open two weeks with no response.",
                    "segment_idx": 7,
                },
                {"text": "Firmware repo lacks a README, slowing onboarding.", "segment_idx": 11},
            ],
        },
        {
            "title": "Changes for Next Sprint",
            "segment_range": (13, 18),
            "notes": [
                {"text": "Check data quality before assuming a model bug.", "segment_idx": 14},
                {"text": "Escalate the vendor rate-limit ticket by Wednesday.", "segment_idx": 15},
                {
                    "text": "Flag customer integration requests earlier for scoping.",
                    "segment_idx": 16,
                },
            ],
        },
    ],
    "summary_overview": (
        "The team's retro highlighted three clean wins: the dashboard performance fix, the crack-detection "
        "relabeling pass, and early battery-life improvements from event-triggered sampling on the sensor "
        "pod. On the friction side, a day was lost misdiagnosing a labeling issue as a model bug, a "
        "satellite imagery vendor's rate-limit ticket has sat unanswered for two weeks, and the firmware "
        "repo's missing README slowed onboarding. Going into next sprint, the team committed to checking "
        "data quality before assuming model issues, escalating the vendor ticket, and flagging customer "
        "integration requests earlier."
    ),
    "action_items": [
        {
            "text": "Escalate the satellite imagery vendor's rate-limit support ticket.",
            "assignee": "Priya Raman",
            "due_date": "2026-09-09",
            "source_segment_idx": 15,
        },
        {
            "text": "Write a README for the firmware repository covering build instructions.",
            "assignee": "Devon Ashworth",
            "due_date": "2026-09-08",
            "source_segment_idx": 12,
        },
        {
            "text": "Ensure the vendor escalation isn't carried by one person alone.",
            "assignee": "Maya Ferreira",
            "due_date": None,
            "source_segment_idx": 18,
        },
    ],
}
