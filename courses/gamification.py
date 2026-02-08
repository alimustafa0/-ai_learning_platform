LEVELS = [
    (1, "Beginner", 0),
    (2, "Learner", 50),
    (3, "Explorer", 120),
    (4, "Builder", 250),
    (5, "Professional", 500),
    (6, "Expert", 900),
    (7, "Master", 1500),
]

def get_level_progress(total_xp):
    current_level = LEVELS[0]
    next_level = None

    for i, level in enumerate(LEVELS):
        if total_xp >= level[2]:
            current_level = level
            if i + 1 < len(LEVELS):
                next_level = LEVELS[i + 1]
        else:
            break

    return current_level, next_level