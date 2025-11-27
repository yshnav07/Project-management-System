from .models import Notification

def notifications_processor(request):
    if request.user.is_authenticated:
        return {
            "notifications": Notification.objects.filter(
                user=request.user, is_read=False
            )
        }
    return {"notifications": []}
