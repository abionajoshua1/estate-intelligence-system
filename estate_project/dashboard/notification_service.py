from .models import Notification


def create_notification(
    *,
    user,
    title,
    message,
    notification_type="general",
):
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
    )