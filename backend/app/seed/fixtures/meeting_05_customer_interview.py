"""Fictional seed meeting — see meeting_01 module docstring."""

MEETING = {
    "title": "Customer Interview — Meridian Grid Facilities",
    "started_at": "2026-08-28T17:00:00+00:00",
    "source": "seed",
    "participants": [
        {"name": "Owen Kessler", "email": "owen@solsticeanalytics.dev", "is_host": True},
        {"name": "Lina Osei", "email": "lina@solsticeanalytics.dev"},
        {"name": "Sam Whitfield", "email": "s.whitfield@meridiangrid.example"},
    ],
    "tags": ["customer", "research", "interview"],
    "dialogue": [
        ("Owen Kessler", "Thanks for hopping on, Sam. We're trying to understand how the pilot's actually fitting into your day-to-day, not just whether the numbers look right."),
        ("Sam Whitfield", "Happy to talk through it. Overall it's been positive. The alerts are catching things our manual quarterly inspections would've missed for months."),
        ("Lina Osei", "Can you walk us through what happens when you get an alert, from your side?"),
        ("Sam Whitfield", "Sure. I get a dashboard notification and an email. I click through to the specific pod location, see the vibration trend and the linked camera snapshot if there is one, and then I decide whether it needs a physical inspection or can wait."),
        ("Owen Kessler", "How often are you finding yourself needing to log into the dashboard versus just acting off the email?"),
        ("Sam Whitfield", "Mostly the dashboard, honestly, the email doesn't have enough context to act on by itself. I usually have to click through anyway."),
        ("Lina Osei", "That's useful, we've been debating whether to put more detail directly in the email. Sounds like yes."),
        ("Sam Whitfield", "I'd say so. Even just the severity level and a thumbnail would save me a click most of the time."),
        ("Owen Kessler", "Noted. What about the ticketing integration we talked about, is that still something you'd use?"),
        ("Sam Whitfield", "Definitely, that's actually the main gap right now. Right now someone on my team manually creates a ticket in our system whenever your dashboard flags something serious. It works but it's an extra step that could get missed."),
        ("Owen Kessler", "Understood, that's actively being scoped on our side. Can I ask, when a ticket does get missed, what usually causes that?"),
        ("Sam Whitfield", "Mostly just volume. If three alerts come in on a Friday afternoon, sometimes one gets deprioritized until Monday."),
        ("Lina Osei", "Do you think a severity ranking would help with that, so the most urgent one is visually distinct?"),
        ("Sam Whitfield", "Yes, right now everything looks the same weight in the inbox. If something was clearly marked as higher severity I think it would get triaged faster."),
        ("Owen Kessler", "That's a good, cheap change we can make before the ticketing integration is even done."),
        ("Lina Osei", "Agreed, I'll mock something up this week."),
        ("Owen Kessler", "One more thing, has anyone else on your team started using the dashboard, or is it mostly you?"),
        ("Sam Whitfield", "Mostly me right now. I've shown it to two colleagues but they haven't logged in themselves yet."),
        ("Owen Kessler", "Would it help to have a quick onboarding walkthrough for them?"),
        ("Sam Whitfield", "Probably, yeah. A five minute video would probably do it, nobody wants to sit through a full call for this."),
        ("Owen Kessler", "That's easy enough, we'll put one together."),
        ("Lina Osei", "Last thing from me, on a scale of one to ten, how likely are you to recommend this to another facilities manager?"),
        ("Sam Whitfield", "Right now, honestly, an eight. It'd be a nine or ten once the ticketing integration is in and I'm not the only one who knows how to use it."),
        ("Owen Kessler", "That's really helpful, thank you for being direct about it."),
        ("Sam Whitfield", "Of course, appreciate you actually asking instead of just sending a survey."),
    ],
    "chapters": [
        {
            "title": "Alert Workflow Today",
            "segment_range": (0, 7),
            "notes": [
                {"text": "Alerts are catching issues that quarterly manual inspections were missing.", "segment_idx": 1},
                {"text": "Current flow: dashboard notification + email, but email lacks enough context to act on directly.", "segment_idx": 5},
                {"text": "Requested: severity level and a thumbnail in the email itself.", "segment_idx": 7},
            ],
        },
        {
            "title": "Ticketing Integration Gap",
            "segment_range": (8, 15),
            "notes": [
                {"text": "Tickets are currently created manually when the dashboard flags something serious.", "segment_idx": 9},
                {"text": "Missed tickets are mostly a volume problem — alerts on a Friday can slip to Monday.", "segment_idx": 11},
                {"text": "A visible severity ranking was proposed as a cheap interim fix before full integration.", "segment_idx": 13},
            ],
        },
        {
            "title": "Team Adoption",
            "segment_range": (16, 24),
            "notes": [
                {"text": "Dashboard use is currently limited to Sam; two colleagues have seen it but not logged in.", "segment_idx": 17},
                {"text": "A short onboarding video was proposed over a full walkthrough call.", "segment_idx": 19},
                {"text": "Current recommendation likelihood: 8/10, expected to rise once ticketing integration ships and adoption broadens.", "segment_idx": 22},
            ],
        },
    ],
    "summary_overview": (
        "Sam Whitfield at Meridian Grid gave positive feedback on the pilot, noting the alerts have caught "
        "issues that quarterly manual inspections missed. The main friction point is that alert emails lack "
        "enough context to act on without clicking into the dashboard, and tickets in Meridian's own system "
        "are still created manually, which occasionally causes alerts to be deprioritized under volume. A "
        "severity ranking was proposed as a quick interim improvement ahead of the full ticketing "
        "integration. Dashboard adoption within Meridian's team is currently limited to Sam alone, and a "
        "short onboarding video was proposed to bring in two other colleagues. Sam rated likelihood to "
        "recommend at 8 out of 10, expected to rise once integration and team adoption improve."
    ),
    "action_items": [
        {"text": "Add severity level and a thumbnail image to alert emails.", "assignee": "Lina Osei", "due_date": None, "source_segment_idx": 7},
        {"text": "Mock up a visual severity ranking for the alert inbox.", "assignee": "Lina Osei", "due_date": "2026-09-04", "source_segment_idx": 15},
        {"text": "Produce a short onboarding video for new dashboard users.", "assignee": "Owen Kessler", "due_date": None, "source_segment_idx": 19},
        {"text": "Continue scoping the ticketing system integration for Meridian Grid.", "assignee": "Owen Kessler", "due_date": None, "source_segment_idx": 10},
    ],
}
