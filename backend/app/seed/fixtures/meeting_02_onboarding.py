"""Fictional seed meeting — see meeting_01 module docstring for why this is invented
content rather than the real reference transcripts."""

MEETING = {
    "title": "Evening Sync — Welcoming Marcus",
    "started_at": "2026-08-25T19:30:00+00:00",
    "source": "seed",
    "participants": [
        {"name": "Maya Ferreira", "email": "maya@solsticeanalytics.dev", "is_host": True},
        {"name": "Owen Kessler", "email": "owen@solsticeanalytics.dev"},
        {"name": "Devon Ashworth", "email": "devon@solsticeanalytics.dev"},
        {"name": "Marcus Webb", "email": "marcus@solsticeanalytics.dev"},
    ],
    "tags": ["standup", "onboarding", "hardware"],
    "dialogue": [
        (
            "Maya Ferreira",
            "Let's kick off with introductions since Marcus is joining us for the first time. Marcus, do you want to give everyone a quick background?",
        ),
        (
            "Marcus Webb",
            "Sure, thanks. I spent the last three years doing embedded systems work for industrial sensor arrays, mostly vibration and acoustic monitoring for manufacturing lines. Before that I was doing firmware for a drone startup. I'm excited to get into the retrofit hardware side here.",
        ),
        (
            "Owen Kessler",
            "That's a great fit, honestly, we've been needing someone who's actually shipped sensor hardware at volume instead of just prototypes.",
        ),
        (
            "Maya Ferreira",
            "Agreed. Marcus, your focus for the first couple weeks is going to be the retrofit sensor pod, the thing that clips onto existing structural supports without needing an electrician on site.",
        ),
        (
            "Marcus Webb",
            "Understood. Is there an existing prototype I can look at, or am I starting from a spec?",
        ),
        (
            "Devon Ashworth",
            "There's a rough prototype on my desk, it works but the battery life is bad, we're getting maybe five days instead of the ninety we need.",
        ),
        (
            "Marcus Webb",
            "Five days versus ninety is usually a duty-cycle problem, not a hardware problem. Is it sampling continuously?",
        ),
        (
            "Devon Ashworth",
            "Yeah, continuous sampling at 200 hertz on the accelerometer, all the time.",
        ),
        (
            "Marcus Webb",
            "That'll do it. We should be able to get away with event-triggered sampling, wake on a threshold crossing, sleep otherwise. I've done exactly this pattern before.",
        ),
        (
            "Owen Kessler",
            "If you can get us into the double digits on battery life that alone would unblock the retrofit pitch, that's been our weakest answer in customer calls.",
        ),
        (
            "Marcus Webb",
            "I'll take a look at the firmware tomorrow and give you a real estimate by Wednesday rather than guessing today.",
        ),
        (
            "Maya Ferreira",
            "Perfect. Devon, can you walk Marcus through the current firmware repo after this call?",
        ),
        ("Devon Ashworth", "Yep, I'll block an hour tomorrow morning."),
        (
            "Maya Ferreira",
            "Great. Switching gears, Owen, where are we on the calibration fix from Monday?",
        ),
        (
            "Owen Kessler",
            "Shipped and it held through the expo, false positive rate is back down to baseline. No issues since.",
        ),
        ("Maya Ferreira", "Good, that one's closed then. Anything blocking anyone else?"),
        (
            "Devon Ashworth",
            "Just flagging, I'm going to need review on a PR that touches the sensor fusion weighting, it's a bigger change than usual.",
        ),
        ("Owen Kessler", "Send it my way, I'll look tonight."),
        (
            "Maya Ferreira",
            "Alright, I think that covers it. Marcus, welcome aboard, glad to have you.",
        ),
        (
            "Marcus Webb",
            "Thanks, excited to be here. This is exactly the kind of problem I wanted to work on next.",
        ),
    ],
    "chapters": [
        {
            "title": "Onboarding: Marcus Webb",
            "segment_range": (0, 4),
            "notes": [
                {
                    "text": "Marcus joins with embedded systems background: industrial vibration/acoustic sensors and drone firmware.",
                    "segment_idx": 1,
                },
                {
                    "text": "First assignment: the retrofit sensor pod for existing structural supports.",
                    "segment_idx": 3,
                },
            ],
        },
        {
            "title": "Retrofit Pod: Battery Life",
            "segment_range": (5, 12),
            "notes": [
                {
                    "text": "Current prototype gets ~5 days battery life against a 90-day target.",
                    "segment_idx": 5,
                },
                {
                    "text": "Root cause suspected: continuous 200Hz sampling instead of event-triggered wake.",
                    "segment_idx": 7,
                },
                {
                    "text": "Marcus to estimate achievable battery life by Wednesday after reviewing firmware.",
                    "segment_idx": 10,
                },
            ],
        },
        {
            "title": "Follow-ups",
            "segment_range": (13, 19),
            "notes": [
                {
                    "text": "Anomaly detector calibration fix held through the expo — closed.",
                    "segment_idx": 14,
                },
                {"text": "Sensor fusion weighting PR needs review from Owen.", "segment_idx": 16},
            ],
        },
    ],
    "summary_overview": (
        "The team welcomed new hire Marcus Webb, whose embedded systems background in industrial "
        "sensor arrays lines up directly with the retrofit sensor pod work. His first task is investigating "
        "the pod's battery life, currently around five days against a ninety-day target, which the team "
        "suspects is a duty-cycle problem from continuous sampling rather than a hardware limitation. "
        "Separately, the anomaly detector calibration fix from earlier in the week held through the expo "
        "with no regressions, and a pending sensor fusion PR is queued for review."
    ),
    "action_items": [
        {
            "text": "Walk Marcus through the current sensor pod firmware repository.",
            "assignee": "Devon Ashworth",
            "due_date": "2026-08-26",
            "source_segment_idx": 12,
        },
        {
            "text": "Investigate event-triggered sampling for the retrofit pod and estimate achievable battery life.",
            "assignee": "Marcus Webb",
            "due_date": "2026-08-27",
            "source_segment_idx": 10,
        },
        {
            "text": "Review the sensor fusion weighting PR.",
            "assignee": "Owen Kessler",
            "due_date": "2026-08-26",
            "source_segment_idx": 17,
        },
    ],
}
