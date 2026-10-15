from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from .tasks import send_complaint_email
from unittest.mock import patch

from .views import queue_complaint_email

@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="noreply@example.com",
)
class SendComplaintEmailTests(TestCase):

    def setUp(self):
        self.User = get_user_model()

    def test_email_is_sent_to_user(self):
        user = self.User.objects.create_user(
            username="email_resident",
            email="resident@example.com",
        )

        result = send_complaint_email.run(
            user.pk,
            "Complaint Submitted",
            "Your complaint has been submitted.",
        )

        self.assertEqual(result, "sent")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Complaint Submitted")
        self.assertEqual(
            mail.outbox[0].body,
            "Your complaint has been submitted.",
        )
        self.assertEqual(
            mail.outbox[0].from_email,
            "noreply@example.com",
        )
        self.assertEqual(
            mail.outbox[0].to,
            ["resident@example.com"],
        )

    def test_user_without_email_is_skipped(self):
        user = self.User.objects.create_user(
            username="no_email_resident",
            email="",
        )

        result = send_complaint_email.run(
            user.pk,
            "Complaint Submitted",
            "Your complaint has been submitted.",
        )

        self.assertEqual(result, "skipped_no_email")
        self.assertEqual(len(mail.outbox), 0)

    def test_nonexistent_user_is_skipped(self):
        result = send_complaint_email.run(
            999999,
            "Complaint Submitted",
            "Your complaint has been submitted.",
        )

        self.assertEqual(result, "skipped_user_not_found")
        self.assertEqual(len(mail.outbox), 0)



class QueueComplaintEmailTests(TestCase):

    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="queue_resident",
            email="queue@example.com",
        )

    @patch("core.views.send_complaint_email.delay")
    def test_valid_email_is_queued(self, mock_delay):
        queue_complaint_email(
            self.user,
            "Complaint Submitted",
            "Your complaint has been submitted.",
        )

        mock_delay.assert_called_once_with(
            self.user.pk,
            "Complaint Submitted",
            "Your complaint has been submitted.",
        )

    @patch("core.views.send_complaint_email.delay")
    def test_missing_email_is_not_queued(self, mock_delay):
        self.user.email = ""
        self.user.save()

        queue_complaint_email(
            self.user,
            "Complaint Submitted",
            "Your complaint has been submitted.",
        )

        mock_delay.assert_not_called()

    @patch(
        "core.views.send_complaint_email.delay",
        side_effect=RuntimeError("Broker unavailable"),
    )
    def test_broker_failure_does_not_propagate(self, mock_delay):
        queue_complaint_email(
            self.user,
            "Complaint Submitted",
            "Your complaint has been submitted.",
        )

        mock_delay.assert_called_once()
