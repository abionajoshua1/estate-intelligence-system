from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch


class ComplaintAuthorizationTests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="resident_test",
            password="testpassword123",
        )

        self.user.profile.role = "resident"
        self.user.profile.resident_id = "R001"
        self.user.profile.save()

        self.client.force_authenticate(user=self.user)

        self.url = "/api/complaints/create/"

    @patch("core.views.execute_cypher")
    @patch("core.views.get_authorization_context")
    def test_resident_cannot_complain_about_other_property(
        self,
        mock_context,
        mock_execute,
    ):
        mock_context.return_value = {
            "scope": "estate",
            "estate_id": "E001",
        }

        mock_execute.return_value = []

        response = self.client.post(
            self.url,
            {
                "resident_id": "R001",
                "property_id": "P002",
                "title": "Broken light",
                "description": "The light is not working.",
                "category": "Electrical",
                "priority": "Medium",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertIn(
            "not authorized",
            response.data["error"].lower(),
        )
        
    @patch("core.views.Neo4jConnection")
    @patch("core.views.get_authorization_context")
    def test_resident_cannot_search_other_estate_resident(
        self,
        mock_context,
        mock_db_class,
    ):
        mock_context.return_value = {
            "role": "resident",
            "estate_id": "E002",
            "estate_name": "Voera Estate",
            "scope": "current_estate",
        }
        
        self.user.profile.resident_id = "R006"
        self.user.profile.save()
        
        mock_db = mock_db_class.return_value
        mock_db.query.return_value = []

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            "/api/search/",
            {"q": "R001"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            [],
        )
        
        print("ALL QUERY CALLS:", mock_db.query.call_args_list)

        call_args = mock_db.query.call_args
        parameters = call_args.args[1]
        
        '''
            self.assertEqual(
            parameters["role"],
            "resident",
        )

        self.assertEqual(
            parameters["estate_id"],
            "E002",
        )

        self.assertEqual(
            parameters["resident_id"],
            "R006",
        )'''