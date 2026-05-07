CURATED_ICONS = [
    # Sleep & Energy
    "fa5s.sun", "fa5s.moon", "fa5s.bed", "fa5s.clock",
    # Exercise & Movement
    "fa5s.dumbbell", "fa5s.running", "fa5s.walking", "fa5s.biking",
    "fa5s.swimmer", "fa5s.hiking",
    # Wellness
    "fa5s.heartbeat", "fa5s.heart", "fa5s.spa", "fa5s.lungs",
    "fa5s.shower", "fa5s.tooth", "fa5s.pills",
    # Food & Drink
    "fa5s.utensils", "fa5s.apple-alt", "fa5s.carrot",
    "fa5s.tint", "fa5s.coffee", "fa5s.glass-whiskey",
    # Mind & Learning
    "fa5s.book", "fa5s.book-open", "fa5s.brain", "fa5s.laptop-code",
    "fa5s.language", "fa5s.pen", "fa5s.music", "fa5s.graduation-cap", "fa5s.chess",
    # Social & Family
    "fa5s.home", "fa5s.users", "fa5s.phone", "fa5s.comments", "fa5s.praying-hands",
    # Productivity & Goals
    "fa5s.tasks", "fa5s.bullseye", "fa5s.trophy", "fa5s.star", "fa5s.fire",
    # Restrictions
    "fa5s.ban", "fa5s.mobile-alt", "fa5s.smoking-ban", "fa5s.wine-glass-alt", "fa5s.gamepad",
    # Finance & Nature
    "fa5s.piggy-bank", "fa5s.dollar-sign", "fa5s.leaf",
    # General
    "fa5s.check-circle",
]

_KEYWORD_MAP = {
    "wake up":      "fa5s.sun",
    "sleep":        "fa5s.moon",
    "masturbat":    "fa5s.ban",
    "language":     "fa5s.language",
    "translat":     "fa5s.language",
    "programming":  "fa5s.laptop-code",
    "code":         "fa5s.laptop-code",
    "exercise":     "fa5s.dumbbell",
    "work out":     "fa5s.dumbbell",
    "calorie":      "fa5s.utensils",
    "food":         "fa5s.utensils",
    "eat":          "fa5s.utensils",
    "family":       "fa5s.home",
    "social media": "fa5s.mobile-alt",
    "detox":        "fa5s.mobile-alt",
    "read":         "fa5s.book",
    "learn":        "fa5s.book",
    "meditat":      "fa5s.spa",
    "water":        "fa5s.tint",
    "journal":      "fa5s.pen",
    "walk":         "fa5s.walking",
    "run":          "fa5s.running",
    "fruit":        "fa5s.apple-alt",
    "milk":         "fa5s.glass-whiskey",
    "medicine":     "fa5s.pills",
    "no ":          "fa5s.ban",
    "sun":          "fa5s.sun",
}


def icon_for(name: str, stored: str = "") -> str:
    if stored:
        return stored
    low = name.lower()
    for key, icon_name in _KEYWORD_MAP.items():
        if key in low:
            return icon_name
    return "fa5s.check-circle"
