from django.db.models import Sum
from .models import XPEvent
from .gamification import get_level_progress


def user_level(request):
    if request.user.is_authenticated:
        total_xp = XPEvent.objects.filter(user=request.user).aggregate(
            Sum("points")
        )["points__sum"] or 0

        current_level, _ = get_level_progress(total_xp)

        return {
            "global_level_number": current_level[0],
            "global_level_title": current_level[1],
        }

    return {}
