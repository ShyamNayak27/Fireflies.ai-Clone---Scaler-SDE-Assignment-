"""Fictional seed meeting — see meeting_01 module docstring."""

MEETING = {
    "title": "Evening Standup — Detection Pipeline Review",
    "started_at": "2026-09-01T19:30:00+00:00",
    "source": "seed",
    "participants": [
        {"name": "Maya Ferreira", "email": "maya@solsticeanalytics.dev", "is_host": True},
        {"name": "Owen Kessler", "email": "owen@solsticeanalytics.dev"},
        {"name": "Devon Ashworth", "email": "devon@solsticeanalytics.dev"},
        {"name": "Priya Raman", "email": "priya@solsticeanalytics.dev"},
    ],
    "tags": ["standup", "engineering", "ml"],
    "dialogue": [
        ("Maya Ferreira", "Let's start with the detection pipeline. Devon, where are we?"),
        ("Devon Ashworth", "The crack-detection model is trained on the new dataset, precision's up to ninety-one percent, but recall dropped a bit on hairline cracks under two millimeters."),
        ("Owen Kessler", "Is that a labeling issue or an actual model limitation?"),
        ("Devon Ashworth", "Bit of both honestly. Some of the hairline cracks in the training set were labeled inconsistently, I want to do another labeling pass before I conclude it's the model."),
        ("Maya Ferreira", "How long would that pass take?"),
        ("Devon Ashworth", "Two days if I do it myself, less if I get help."),
        ("Priya Raman", "I can help with labeling tomorrow afternoon, I've got a lighter day."),
        ("Devon Ashworth", "That'd help a lot, thank you."),
        ("Maya Ferreira", "Good, let's get that resolved before we commit to a demo number for the next round of customer calls."),
        ("Owen Kessler", "Speaking of customer calls, I want to flag that Meridian Grid asked if we can export detection events to their existing ticketing system instead of just the dashboard."),
        ("Maya Ferreira", "Do we have a sense of what that integration would take?"),
        ("Priya Raman", "If it's a standard webhook on their end, that's maybe a day of work. If they need a specific format or auth scheme, more."),
        ("Owen Kessler", "I'll ask their engineering contact for the webhook spec, should have an answer by Friday."),
        ("Maya Ferreira", "Great, let's not build anything until we know what we're building against."),
        ("Devon Ashworth", "One more thing on the model side, I want to start collecting a small set of night-vision footage. Right now everything in the dataset is daylight, and a few pilot sites run cameras through the night."),
        ("Owen Kessler", "How much footage do you think we need to get a usable baseline?"),
        ("Devon Ashworth", "Even a few hours from two or three sites would tell us whether the current model degrades badly or just moderately at night."),
        ("Maya Ferreira", "Priya, do we have permission to pull night footage from the pilot sites already, or do we need to ask?"),
        ("Priya Raman", "We have permission for daytime, I'd want to double check the data agreement before pulling anything overnight."),
        ("Maya Ferreira", "Please check that first, don't want to be pulling data outside what we agreed to."),
        ("Priya Raman", "Will do, I'll check tomorrow morning."),
        ("Maya Ferreira", "Okay. Anything else before we wrap?"),
        ("Owen Kessler", "Nothing from me."),
        ("Devon Ashworth", "Same, all good."),
        ("Maya Ferreira", "Great, thanks everyone."),
    ],
    "chapters": [
        {
            "title": "Crack Detection Model",
            "segment_range": (0, 8),
            "notes": [
                {"text": "Precision improved to 91% on the new dataset; recall dropped on hairline cracks under 2mm.", "segment_idx": 1},
                {"text": "Suspected inconsistent labeling of hairline cracks in training data; relabeling pass planned.", "segment_idx": 3},
            ],
        },
        {
            "title": "Meridian Grid Integration Request",
            "segment_range": (9, 13),
            "notes": [
                {"text": "Meridian Grid wants detection events exported to their ticketing system, not just the dashboard.", "segment_idx": 9},
                {"text": "Scope depends on their webhook spec; Owen requesting details before any build starts.", "segment_idx": 12},
            ],
        },
        {
            "title": "Night-Vision Data Collection",
            "segment_range": (14, 20),
            "notes": [
                {"text": "Current dataset is daylight-only; some pilot sites run cameras overnight.", "segment_idx": 14},
                {"text": "Data-sharing agreement needs to be checked before pulling any overnight footage.", "segment_idx": 18},
            ],
        },
    ],
    "summary_overview": (
        "The crack-detection model showed a precision improvement to 91% on the new dataset, though "
        "recall on hairline cracks dropped, likely due to inconsistent labeling that the team will address "
        "with a relabeling pass before committing to a demo number. Meridian Grid has requested exporting "
        "detection events into their own ticketing system rather than relying solely on the dashboard, "
        "pending their webhook specification. Separately, the team identified a gap in night-vision "
        "coverage in the training data and will check the pilot sites' data agreements before collecting "
        "any overnight footage."
    ),
    "action_items": [
        {"text": "Relabel hairline crack examples in the training dataset.", "assignee": "Devon Ashworth", "due_date": "2026-09-03", "source_segment_idx": 3},
        {"text": "Help with the crack-label relabeling pass.", "assignee": "Priya Raman", "due_date": "2026-09-02", "source_segment_idx": 6},
        {"text": "Get the webhook specification from Meridian Grid's engineering contact.", "assignee": "Owen Kessler", "due_date": "2026-09-05", "source_segment_idx": 12},
        {"text": "Check the pilot site data agreements before collecting overnight camera footage.", "assignee": "Priya Raman", "due_date": "2026-09-02", "source_segment_idx": 19},
    ],
}
