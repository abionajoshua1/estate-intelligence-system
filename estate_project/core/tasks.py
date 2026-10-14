import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_complaint_email(self, user_id, subject, message):
    """Send a complaint-related email to a resident asynchronously."""
    User = get_user_model()

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning(
            "Complaint email skipped: user %s does not exist.",
            user_id,
        )
        return "skipped_user_not_found"

    if not user.email or not user.email.strip():
        logger.info(
            "Complaint email skipped: user %s has no email address.",
            user_id,
        )
        return "skipped_no_email"

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    logger.info(
        "Complaint email sent to user ID %s.",
        user_id,
    )
    return "sent"
