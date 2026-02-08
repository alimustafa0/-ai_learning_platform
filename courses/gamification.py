LEVELS = [
    (1, "Beginner", 0),
    (2, "Learner", 50),
    (3, "Explorer", 120),
    (4, "Builder", 250),
    (5, "Professional", 500),
    (6, "Expert", 900),
    (7, "Master", 1500),
]

def get_level_from_xp(total_xp):
    current_level = LEVELS[0]

    for level in LEVELS:
        if total_xp >= level[2]:
            current_level = level
        else:
            break

    return current_level
