from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from .tasks import send_complaint_email
from unittest.mock import patch

from .views import queue_complaint_email

from rest_framework import status
from rest_framework.test import APITestCase
from dashboard.models import Profile

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



class ComplaintStatusEmailIntegrationTests(APITestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="status_email_resident",
            password="testpassword123",
            email="status@example.com",
        )
        self.user.profile.role = "admin"
        self.user.profile.save()

        self.profile = self.user.profile
        self.profile.resident_id = "R_EMAIL_TEST"
        self.profile.save()

        self.client.force_authenticate(user=self.user)

    @patch("core.views.queue_complaint_email")
    @patch("core.views.Neo4jConnection")
    @patch("core.views.authorize_resource")
    @patch("core.views.get_authorization_context")
    def test_status_change_queues_one_email(
        self,
        mock_context,
        mock_authorize,
        mock_db_class,
        mock_queue_email,
    ):
        mock_context.return_value = {
            "role": "admin",
            "scope": "all_estates",
            "estate_id": None,
            "estate_name": None,
        }

        mock_db = mock_db_class.return_value
        mock_db.query.side_effect = [
            [
                {
                    "resident_id": "R_EMAIL_TEST",
                    "complaint_id": "C900",
                    "title": "Leaking tap",
                    "description": "Water is leaking.",
                    "category": "Plumbing",
                    "priority": "Medium",
                    "status": "Open",
                    "created_at": "2026-10-15",
                }
            ],
            [
                {
                    "complaint_id": "C900",
                    "title": "Leaking tap",
                    "description": "Water is leaking.",
                    "category": "Plumbing",
                    "priority": "Medium",
                    "status": "Resolved",
                    "created_at": "2026-10-15",
                    "resolved_at": "2026-10-15",
                }
            ],
        ]

        response = self.client.put(
            "/api/complaints/C900/",
            {"status": "Resolved"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_queue_email.assert_called_once()
        self.assertEqual(
            mock_queue_email.call_args.args[1],
            "Complaint Resolved",
        )
        mock_db.close.assert_called_once()


class ComplaintCreationEmailIntegrationTests(APITestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="creation_email_admin",
            password="testpassword123",
            email="admin@example.com",
        )
        self.user.profile.role = "admin"
        self.user.profile.save()
        self.resident = User.objects.create_user(
            username="creation_email_resident",
            email="resident@example.com",
        )
        self.resident.profile.resident_id = "R_EMAIL_TEST"
        self.resident.profile.save()

        self.client.force_authenticate(user=self.user)

    @patch("core.views.queue_complaint_email")
    @patch("core.views.Neo4jConnection")
    @patch("core.views.authorize_resource")
    @patch("core.views.get_authorization_context")
    def test_successful_creation_queues_one_email(
        self,
        mock_context,
        mock_authorize,
        mock_db_class,
        mock_queue_email,
    ):
        mock_context.return_value = {
            "role": "admin",
            "scope": "all_estates",
            "estate_id": None,
            "estate_name": None,
        }

        mock_db = mock_db_class.return_value
        mock_db.query.side_effect = [
            [{"resident_id": "R_EMAIL_TEST"}],
            [{"property_id": "P_EMAIL_TEST"}],
            [],
            [
                {
                    "complaint_id": "C001",
                    "title": "Leaking tap",
                    "description": "Water is leaking.",
                    "category": "Plumbing",
                    "priority": "Medium",
                    "status": "Open",
                    "created_at": "2026-10-15",
                }
            ],
        ]

        response = self.client.post(
            "/api/complaints/create/",
            {
                "resident_id": "R_EMAIL_TEST",
                "property_id": "P_EMAIL_TEST",
                "title": "Leaking tap",
                "description": "Water is leaking.",
                "category": "Plumbing",
                "priority": "Medium",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["complaint"]["complaint_id"],
            "C001",
        )
        mock_queue_email.assert_called_once()

        email_args = mock_queue_email.call_args.args
        self.assertEqual(email_args[0].pk, self.resident.pk)
        self.assertEqual(email_args[1], "Complaint Submitted")
        self.assertIn("Leaking tap", email_args[2])

        mock_db.close.assert_called_once()
class ComplaintAssignmentEmailIntegrationTests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="assignment_email_admin",
            password="testpassword123",
            email="admin@example.com",
        )
        self.user.profile.role = "admin"
        self.user.profile.save()

        self.resident = User.objects.create_user(
            username="assignment_email_resident",
            email="resident@example.com",
        )
        self.resident.profile.resident_id = "R_ASSIGN_EMAIL"
        self.resident.profile.save()

        self.client.force_authenticate(user=self.user)

    @patch("core.views.queue_complaint_email")
    @patch("core.views.create_notification")
    @patch("core.views.Neo4jConnection")
    @patch("core.views.authorize_resource")
    @patch("core.views.get_authorization_context")
    def test_assignment_queues_email_for_resident(
        self,
        mock_context,
        mock_authorize,
        mock_db_class,
        mock_notification,
        mock_queue_email,
    ):
        mock_context.return_value = {
            "role": "admin",
            "scope": "all_estates",
            "estate_id": None,
            "estate_name": None,
        }

        mock_db = mock_db_class.return_value
        mock_db.query.side_effect = [
            [
                {
                    "complaint_id": "C900",
                    "complaint_title": "Leaking tap",
                    "resident_id": "R_ASSIGN_EMAIL",
                }
            ],
            [{"team_id": "T001"}],
            [],
            [
                {
                    "complaint_id": "C900",
                    "complaint_title": "Leaking tap",
                    "resident_id": "R_ASSIGN_EMAIL",
                    "team_id": "T001",
                    "team_name": "Plumbing Team",
                }
            ],
        ]

        response = self.client.post(
            "/api/complaints/assign-team/",
            {
                "complaint_id": "C900",
                "team_id": "T001",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["assignment"]["team_name"],
            "Plumbing Team",
        )

        mock_queue_email.assert_called_once()
        email_args = mock_queue_email.call_args.args

        self.assertEqual(email_args[0].pk, self.resident.pk)
        self.assertEqual(email_args[1], "Complaint Assigned")
        self.assertIn("Leaking tap", email_args[2])
        self.assertIn("Plumbing Team", email_args[2])
        self.assertIn("In Progress", email_args[2])

        mock_notification.assert_called_once()
        mock_db.close.assert_called_once()
