"""Fictional seed meeting. Company, people, product and all figures are invented —
see docs/ARCHITECTURE.md §1 on why the real reference transcripts were not used
directly. Written to match their cadence (a founder-led startup morning standup),
not their content.
"""

MEETING = {
    "title": "Morning Standup — Solstice Analytics",
    "started_at": "2026-08-18T09:00:00+00:00",
    "source": "seed",
    "participants": [
        {"name": "Maya Ferreira", "email": "maya@solsticeanalytics.dev", "is_host": True},
        {"name": "Owen Kessler", "email": "owen@solsticeanalytics.dev"},
        {"name": "Priya Raman", "email": "priya@solsticeanalytics.dev"},
        {"name": "Lina Osei", "email": "lina@solsticeanalytics.dev"},
        {"name": "Jordan Lee", "email": "jordan@solsticeanalytics.dev"},
    ],
    "tags": ["standup", "engineering", "fundraising"],
    "dialogue": [
        ("Maya Ferreira", "Morning everyone. Let's keep this tight, we've got the expo booth to finish by Thursday. Owen, where's the demo build at?"),
        ("Owen Kessler", "Build's stable. I cut a release last night, no crashes in the last forty minutes of soak testing. The one thing I'm not happy with is the cold start on the dashboard, it's sitting around six seconds."),
        ("Maya Ferreira", "Six seconds on stage is an eternity. Priya, is that a backend thing or is it the frontend bundle?"),
        ("Priya Raman", "It's mostly us. We're doing a full sensor snapshot fetch on load instead of paginating it. I can fix that today, should get us under two seconds."),
        ("Owen Kessler", "If you can get me a build by end of day I'll run it through the same soak test tonight."),
        ("Priya Raman", "Yeah, I'll have a PR up in a couple hours."),
        ("Maya Ferreira", "Great. Lina, how's the booth signage and the one-pager coming along?"),
        ("Lina Osei", "Signage is at the printer, picking it up tomorrow morning. The one-pager, I've got a draft but I want another pass on the numbers section before it goes out."),
        ("Maya Ferreira", "What's the sticking point?"),
        ("Lina Osei", "Just that our uptime number is from the pilot deployment, not production, and I don't want someone at the booth asking a hard question we can't back up."),
        ("Maya Ferreira", "Fair, let's just label it as pilot data explicitly instead of dropping it. Better than getting caught out."),
        ("Lina Osei", "Works for me, I'll add the caveat and get it to print by tonight."),
        ("Maya Ferreira", "Jordan, you were looking at the competitor booths last week, anything worth reacting to?"),
        ("Jordan Lee", "Yeah so I went through the exhibitor list, there are at least two other companies doing infrastructure monitoring, but from what I can tell they're both still camera-only, no structural sensor fusion. I think our pitch on combining vibration data with vision still holds up."),
        ("Owen Kessler", "That matches what I saw at their websites too. Nobody's talking about retrofit sensors, everyone assumes greenfield installs."),
        ("Maya Ferreira", "Good, that's our wedge, let's make sure the booth script leads with that."),
        ("Jordan Lee", "I can draft two or three talking points around it if that's useful."),
        ("Maya Ferreira", "Please do, send it to Lina so it's consistent with the one-pager language."),
        ("Priya Raman", "One more thing, unrelated to the expo. The GIS ingestion pipeline hit a rate limit yesterday from our satellite imagery provider. I put in a request for a higher tier but it might take a few days to process."),
        ("Maya Ferreira", "Does that block anything for the demo?"),
        ("Priya Raman", "No, the demo dataset is cached locally, this only affects new sites we'd onboard live."),
        ("Maya Ferreira", "Okay, keep an eye on it but not urgent for this week. Owen, anything on the model side?"),
        ("Owen Kessler", "Small thing, the anomaly detector's false positive rate crept up after we added the new vibration sensor type. I think it's a calibration issue, not a model issue. I'll have a fix by Wednesday, well before the expo."),
        ("Maya Ferreira", "Good, let's not touch the model itself this close to the demo, just the calibration."),
        ("Owen Kessler", "Agreed, that's the plan."),
        ("Maya Ferreira", "Alright, let's regroup tomorrow same time. Thanks everyone."),
    ],
    "chapters": [
        {
            "title": "Expo Readiness: Demo & Performance",
            "segment_range": (0, 5),
            "notes": [
                {"text": "Demo build is stable after overnight soak testing.", "segment_idx": 1},
                {"text": "Dashboard cold start is ~6s, needs to be under 2s before the expo.", "segment_idx": 2},
                {"text": "Root cause is a full sensor snapshot fetch on load rather than pagination.", "segment_idx": 3},
            ],
        },
        {
            "title": "Booth Materials",
            "segment_range": (6, 11),
            "notes": [
                {"text": "Signage is at the printer, pickup tomorrow morning.", "segment_idx": 7},
                {"text": "One-pager uptime figure will be explicitly labeled as pilot data, not production.", "segment_idx": 10},
            ],
        },
        {
            "title": "Competitive Positioning",
            "segment_range": (12, 17),
            "notes": [
                {"text": "Competing booths are camera-only; nobody else combines vibration data with vision.", "segment_idx": 13},
                {"text": "Wedge is retrofit sensor support — competitors assume greenfield installs only.", "segment_idx": 15},
            ],
        },
        {
            "title": "Backend & Model Notes",
            "segment_range": (18, 24),
            "notes": [
                {"text": "Satellite imagery provider rate-limited the GIS pipeline; upgrade request pending, doesn't block the demo.", "segment_idx": 18},
                {"text": "Anomaly detector false-positive rate rose after a new sensor type was added — calibration issue, fix due Wednesday.", "segment_idx": 22},
            ],
        },
    ],
    "summary_overview": (
        "The team ran through final preparations for Thursday's infrastructure expo. The dashboard "
        "demo is stable but has a cold-start performance issue that Priya is fixing today by paginating "
        "the sensor snapshot fetch. Booth materials are on track, with the one-pager being revised to "
        "clearly label uptime figures as pilot data rather than production. A competitive scan showed "
        "rival booths are camera-only, reinforcing Solstice's retrofit sensor-fusion positioning as the "
        "differentiator to lead with. On the model side, a calibration issue introduced by a new vibration "
        "sensor type is being fixed without touching the underlying model this close to the demo."
    ),
    "action_items": [
        {"text": "Paginate the sensor snapshot fetch to bring dashboard cold start under 2 seconds.", "assignee": "Priya Raman", "due_date": "2026-08-18", "source_segment_idx": 3},
        {"text": "Run the updated build through overnight soak testing once Priya's fix lands.", "assignee": "Owen Kessler", "due_date": "2026-08-18", "source_segment_idx": 4},
        {"text": "Add an explicit pilot-data caveat to the one-pager's uptime figure before printing.", "assignee": "Lina Osei", "due_date": "2026-08-18", "source_segment_idx": 11},
        {"text": "Draft 2-3 talking points on the retrofit sensor-fusion differentiator for the booth script.", "assignee": "Jordan Lee", "due_date": "2026-08-19", "source_segment_idx": 16},
        {"text": "Fix anomaly detector calibration for the new vibration sensor type.", "assignee": "Owen Kessler", "due_date": "2026-08-20", "source_segment_idx": 22},
    ],
}
