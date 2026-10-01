from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch

from core.authorization import AuthorizationError


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
        

        call_args = mock_db.query.call_args
        parameters = call_args.args[1]
        
        query = call_args.args[0]

        self.assertIn(
            '$role = "resident"',
            query,
        )

        self.assertIn(
            'r.resident_id = $resident_id',
            query,
        )
        
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
        )
    
    @patch("core.views.Neo4jConnection")
    @patch("core.views.get_authorization_context")
    def test_resident_cannot_search_other_property(
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
            {"q": "P006"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            [],
        )

        call_args = mock_db.query.call_args
        query = call_args.args[0]
        parameters = call_args.args[1]

        self.assertIn(
            '$role = "resident"',
            query,
        )

        self.assertIn(
            'r.resident_id = $resident_id',
            query,
        )

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
        )
        
    @patch("core.views.Neo4jConnection")
    @patch("core.views.get_authorization_context")
    def test_resident_cannot_search_other_resident_complaint(
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
            {"q": "C001"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            [],
        )

        call_args = mock_db.query.call_args
        query = call_args.args[0]
        parameters = call_args.args[1]

        self.assertIn(
            '$role = "resident"',
            query,
        )

        self.assertIn(
            'r.resident_id = $resident_id',
            query,
        )

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
        )
        
    @patch("core.views.Neo4jConnection")
    @patch("core.views.get_authorization_context")
    @patch("core.views.authorize_resource")
    def test_manager_cannot_update_complaint_from_other_estate(
        self,
        mock_authorize_resource,
        mock_context,
        mock_db_class,
    ):
        mock_context.return_value = {
            "role": "manager",
            "estate_id": "E001",
            "estate_name": "Greenfield Estate",
            "scope": "current_estate",
        }

        mock_authorize_resource.side_effect = AuthorizationError(
            "You are not authorized to access this complaint."
        )

        self.user.profile.role = "manager"
        self.user.profile.resident_id = None
        self.user.profile.save()

        self.client.force_authenticate(user=self.user)

        response = self.client.put(
            "/api/complaints/C002/",
            {
                "status": "Resolved",
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

        mock_authorize_resource.assert_called_once_with(
            mock_context.return_value,
            "complaint",
            "C002",
        )
        
    @patch("core.views.Neo4jConnection")
    @patch("core.views.get_authorization_context")
    @patch("core.views.authorize_resource")
    def test_manager_cannot_delete_complaint_from_other_estate(
        self,
        mock_authorize_resource,
        mock_context,
        mock_db_class,
    ):
        mock_context.return_value = {
            "role": "manager",
            "estate_id": "E001",
            "estate_name": "Greenfield Estate",
            "scope": "current_estate",
        }

        mock_authorize_resource.side_effect = AuthorizationError(
            "You are not authorized to access this complaint."
        )

        self.user.profile.role = "manager"
        self.user.profile.resident_id = None
        self.user.profile.save()

        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            "/api/complaints/C002/delete/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertIn(
            "not authorized",
            response.data["error"].lower(),
        )

        mock_authorize_resource.assert_called_once_with(
            mock_context.return_value,
            "complaint",
            "C002",
        )

        mock_db_class.assert_not_called()
        
    @patch("core.views.Neo4jConnection")
    @patch("core.views.get_authorization_context")
    @patch("core.views.authorize_resource")
    def test_manager_cannot_assign_property_from_other_estate_to_complaint(
        self,
        mock_authorize_resource,
        mock_context,
        mock_db_class,
    ):
        mock_context.return_value = {
            "role": "manager",
            "estate_id": "E001",
            "estate_name": "Greenfield Estate",
            "scope": "current_estate",
        }

        def authorize_side_effect(context, resource_type, resource_id):
            if resource_type == "property" and resource_id == "P005":
                raise AuthorizationError(
                    "You are not authorized to access this property."
                )

        mock_authorize_resource.side_effect = authorize_side_effect

        self.user.profile.role = "manager"
        self.user.profile.resident_id = None
        self.user.profile.save()

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/complaints/assign-property/",
            {
                "complaint_id": "C001",
                "property_id": "P005",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("not authorized", response.data["error"].lower())

        mock_db_class.assert_not_called()