from django.test import TestCase
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.contrib.auth.models import User

from .models import Complaint


class NPlusOneTest(TestCase):

    def test_n_plus_one(self):
        user1 = User.objects.create_user(username="user1")
        user2 = User.objects.create_user(username="user2")
        user3 = User.objects.create_user(username="user3")

        Complaint.objects.create(
            resident=user1,
            title="Complaint 1",
            description="Test complaint 1",
            location="Property 1",
        )

        Complaint.objects.create(
            resident=user2,
            title="Complaint 2",
            description="Test complaint 2",
            location="Property 2",
        )

        Complaint.objects.create(
            resident=user3,
            title="Complaint 3",
            description="Test complaint 3",
            location="Property 3",
        )

        complaints = Complaint.objects.select_related('resident')

        with CaptureQueriesContext(connection) as context:
            for complaint in complaints:
                print(complaint.resident.username)

        print("QUERY COUNT:", len(context.captured_queries))
        
class PrefetchTest(TestCase):

    def test_prefetch(self):
        user1 = User.objects.create_user(username="user1")
        user2 = User.objects.create_user(username="user2")
        user3 = User.objects.create_user(username="user3")

        Complaint.objects.create(
            resident=user1,
            title="Complaint 1",
            description="Test complaint 1",
            location="Property 1",
        )

        Complaint.objects.create(
            resident=user2,
            title="Complaint 2",
            description="Test complaint 2",
            location="Property 2",
        )

        Complaint.objects.create(
            resident=user3,
            title="Complaint 3",
            description="Test complaint 3",
            location="Property 3",
        )

        users = User.objects.prefetch_related('complaints')

        with CaptureQueriesContext(connection) as context:
            for user in users:
                for complaint in user.complaints.all():
                    print(complaint.title)

        print("QUERY COUNT:", len(context.captured_queries))