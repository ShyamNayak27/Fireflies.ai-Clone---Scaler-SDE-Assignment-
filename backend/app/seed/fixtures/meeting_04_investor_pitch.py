"""Fictional seed meeting — see meeting_01 module docstring. Company, investor,
financials and traction figures below are entirely invented for this assignment."""

MEETING = {
    "title": "Investor Call — Solstice Analytics x Bluecrest Ventures",
    "started_at": "2026-08-14T15:00:00+00:00",
    "source": "seed",
    "participants": [
        {"name": "Maya Ferreira", "email": "maya@solsticeanalytics.dev", "is_host": True},
        {"name": "Owen Kessler", "email": "owen@solsticeanalytics.dev"},
        {"name": "Elena Cho", "email": "elena.cho@bluecrestvc.example"},
    ],
    "tags": ["pitch", "fundraising", "investor"],
    "dialogue": [
        ("Elena Cho", "Thanks for making time. Why don't you start with a quick overview of what Solstice does, for anyone new listening back to the recording."),
        ("Maya Ferreira", "Sure. Solstice builds a retrofit sensor and AI layer for structural monitoring, bridges, parking structures, industrial facilities. Instead of waiting for a full instrumentation project, our pods clip onto existing structures and start feeding vibration and vision data into an anomaly detection pipeline within a day."),
        ("Owen Kessler", "The core insight is that most structural monitoring today only exists on new builds, because retrofitting legacy structures with wired sensors is expensive and slow. We skip that by going wireless and battery powered with a long duty cycle."),
        ("Elena Cho", "What does 'long duty cycle' mean concretely, how long does a pod last on a charge?"),
        ("Owen Kessler", "We're targeting ninety days on the current hardware revision, we were closer to five days on the first prototype before we moved to event-triggered sampling instead of continuous."),
        ("Elena Cho", "That's a big jump. What's driving the detection side, is that computer vision, the sensor data, or both?"),
        ("Maya Ferreira", "Both, fused together. Vision alone gives you surface-level cracking, vibration data catches things that aren't visible yet, like a shift in resonant frequency that precedes a structural issue."),
        ("Elena Cho", "Where are you today on customers or pilots?"),
        ("Maya Ferreira", "We have three paid pilots running, the largest is with Meridian Grid on two of their parking structures. We're in commercial conversations with two additional facilities operators."),
        ("Elena Cho", "And pricing, how are you charging for this?"),
        ("Owen Kessler", "Per-pod annual subscription that includes the hardware, plus a per-site dashboard fee. It's a fairly standard SaaS-plus-hardware model."),
        ("Elena Cho", "What's the raise, and what's it funding?"),
        ("Maya Ferreira", "We're raising four hundred thousand as a pre-seed extension. About half goes to a second hardware revision to get unit costs down for volume manufacturing, the other half is split between a hire in embedded systems, which we just made, and extending pilot runway with two more facilities operators."),
        ("Elena Cho", "You said you just made the hardware hire, is that filled already?"),
        ("Owen Kessler", "Yes, started this week actually, background in industrial sensor arrays, exactly what we needed for the retrofit pod work."),
        ("Elena Cho", "Good. What do you see as the biggest risk to this business over the next twelve months?"),
        ("Maya Ferreira", "Honestly, sales cycle length. Facilities operators move slowly, procurement and liability review takes time, even when the technical pilot goes well. We're trying to counter that by pricing the first year low enough that it's an easy yes rather than a big budget decision."),
        ("Elena Cho", "That's a reasonable read. I'll take this back to the team and we'll get you a response within two weeks. Can you send over the pilot performance data from Meridian Grid specifically?"),
        ("Maya Ferreira", "Yes, I'll have that over to you by end of week."),
        ("Elena Cho", "Great, talk soon."),
    ],
    "chapters": [
        {
            "title": "Company Overview",
            "segment_range": (0, 6),
            "notes": [
                {"text": "Solstice builds retrofit sensor + AI monitoring for structures without requiring new instrumentation.", "segment_idx": 1},
                {"text": "Battery life improved from 5 days to a 90-day target via event-triggered sampling.", "segment_idx": 4},
                {"text": "Detection fuses vision (surface cracking) with vibration data (pre-visible resonant frequency shifts).", "segment_idx": 6},
            ],
        },
        {
            "title": "Traction & Business Model",
            "segment_range": (7, 10),
            "notes": [
                {"text": "Three paid pilots running; largest is two parking structures with Meridian Grid.", "segment_idx": 8},
                {"text": "Pricing: per-pod annual subscription plus a per-site dashboard fee.", "segment_idx": 10},
            ],
        },
        {
            "title": "The Ask",
            "segment_range": (11, 14),
            "notes": [
                {"text": "Raising $400K pre-seed extension: ~half for hardware revision 2, half for a hire and pilot runway.", "segment_idx": 12},
                {"text": "The embedded-systems hire has already been made and started this week.", "segment_idx": 14},
            ],
        },
        {
            "title": "Risk & Next Steps",
            "segment_range": (15, 18),
            "notes": [
                {"text": "Biggest identified risk is long facilities-operator sales cycles; mitigated with low first-year pricing.", "segment_idx": 16},
                {"text": "Elena to review internally and respond within two weeks; requested Meridian Grid pilot performance data.", "segment_idx": 17},
            ],
        },
    ],
    "summary_overview": (
        "Maya and Owen walked Elena Cho of Bluecrest Ventures through Solstice's retrofit sensor and AI "
        "platform for structural monitoring, emphasizing the jump from a 5-day to a 90-day battery life "
        "via event-triggered sampling and the fusion of vision and vibration data for early anomaly "
        "detection. The company has three paid pilots, the largest with Meridian Grid, and is raising a "
        "$400K pre-seed extension split between a second hardware revision and extending pilot runway. "
        "The main identified risk is long facilities-operator sales cycles. Elena requested Meridian Grid's "
        "pilot performance data and will respond within two weeks."
    ),
    "action_items": [
        {"text": "Send Meridian Grid pilot performance data to Elena Cho.", "assignee": "Maya Ferreira", "due_date": "2026-08-21", "source_segment_idx": 18},
        {"text": "Prepare a response to Bluecrest Ventures once their internal review concludes.", "assignee": "Maya Ferreira", "due_date": None, "source_segment_idx": 17},
    ],
}
