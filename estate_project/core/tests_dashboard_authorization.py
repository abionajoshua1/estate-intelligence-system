from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch


class DashboardAuthorizationTests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="manager_test",
            password="testpassword123",
        )

        self.user.profile.role = "manager"
        self.user.profile.resident_id = None
        self.user.profile.save()

        self.client.force_authenticate(user=self.user)

    @patch("core.dashboard_views.Neo4jConnection")
    @patch("core.dashboard_views.get_authorization_context")
    def test_manager_dashboard_uses_current_estate_scope(
        self,
        mock_context,
        mock_db_class,
    ):
        mock_context.return_value = {
            "role": "manager",
            "estate_id": "E001",
            "estate_name": "Greenfield Estate",
            "scope": "current_estate",
        }

        mock_db = mock_db_class.return_value

        mock_db.query.side_effect = [
            [{"total_residents": 5}],
            [{"total_properties": 10}],
            [{"total_estates": 1}],
            [{"available_properties": 2}],
            [{"occupied_properties": 6}],
            [{"maintenance_properties": 2}],
            [{"total_complaints": 4}],
            [{"open_complaints": 1}],
            [{"in_progress_complaints": 1}],
            [{"resolved_complaints": 2}],
        ]

        response = self.client.get("/api/dashboard/overview/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["total_residents"],
            5,
        )

        self.assertEqual(
            response.data["total_properties"],
            10,
        )

        self.assertEqual(
            response.data["total_estates"],
            1,
        )

        # Check every dashboard query received the manager's
        # authenticated estate context.
        for call in mock_db.query.call_args_list:
            parameters = call.args[1]

            self.assertEqual(
                parameters["scope"],
                "current_estate",
            )

            self.assertEqual(
                parameters["estate_id"],
                "E001",
            )
            
    @patch("core.dashboard_views.Neo4jConnection")
    @patch("core.dashboard_views.get_authorization_context")
    def test_admin_dashboard_uses_global_scope(
        self,
        mock_context,
        mock_db_class,
    ):
        mock_context.return_value = {
            "role": "admin",
            "estate_id": None,
            "estate_name": None,
            "scope": "global",
        }

        mock_db = mock_db_class.return_value

        mock_db.query.side_effect = [
            [{"total_residents": 20}],
            [{"total_properties": 40}],
            [{"total_estates": 4}],
            [{"available_properties": 10}],
            [{"occupied_properties": 25}],
            [{"maintenance_properties": 5}],
            [{"total_complaints": 15}],
            [{"open_complaints": 5}],
            [{"in_progress_complaints": 4}],
            [{"resolved_complaints": 6}],
        ]

        response = self.client.get("/api/dashboard/overview/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["total_residents"],
            20,
        )

        self.assertEqual(
            response.data["total_properties"],
            40,
        )

        self.assertEqual(
            response.data["total_estates"],
            4,
        )

        for call in mock_db.query.call_args_list:
            parameters = call.args[1]

            self.assertEqual(
                parameters["scope"],
                "global",
            )

            self.assertIsNone(
                parameters["estate_id"],
            )    
            
    @patch("core.dashboard_views.Neo4jConnection")
    @patch("core.dashboard_views.get_authorization_context")
    def test_manager_complaints_by_category_uses_current_estate_scope(
        self,
        mock_context,
        mock_db_class,
    ):
        mock_context.return_value = {
            "role": "manager",
            "estate_id": "E001",
            "estate_name": "Greenfield Estate",
            "scope": "current_estate",
        }

        mock_db = mock_db_class.return_value
        mock_db.query.return_value = [
            {
                "category": "Electrical",
                "total": 3,
            },
            {
                "category": "Plumbing",
                "total": 2,
            },
        ]

        response = self.client.get(
            "/api/dashboard/complaints-by-category/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            mock_db.query.return_value,
        )

        call_args = mock_db.query.call_args
        query = call_args.args[0]
        parameters = call_args.args[1]

        self.assertIn(
            'e.estate_id = $estate_id',
            query,
        )

        self.assertEqual(
            parameters["scope"],
            "current_estate",
        )

        self.assertEqual(
            parameters["estate_id"],
            "E001",
        )
        
    @patch("core.dashboard_views.Neo4jConnection")
    @patch("core.dashboard_views.get_authorization_context")
    def test_admin_complaints_by_category_uses_global_scope(
        self,
        mock_context,
        mock_db_class,
    ):
        mock_context.return_value = {
            "role": "admin",
            "estate_id": None,
            "estate_name": None,
            "scope": "global",
        }

        mock_db = mock_db_class.return_value
        mock_db.query.return_value = [
            {
                "category": "Electrical",
                "total": 8,
            },
            {
                "category": "Plumbing",
                "total": 5,
            },
        ]

        response = self.client.get(
            "/api/dashboard/complaints-by-category/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        call_args = mock_db.query.call_args
        query = call_args.args[0]
        parameters = call_args.args[1]

        self.assertIn(
            '$scope = "global"',
            query,
        )

        self.assertEqual(
            parameters["scope"],
            "global",
        )

        self.assertIsNone(
            parameters["estate_id"],
        )
        
    @patch("core.dashboard_views.Neo4jConnection")
    @patch("core.dashboard_views.get_authorization_context")
    def test_manager_properties_by_status_uses_current_estate_scope(
        self,
        mock_context,
        mock_db_class,
    ):
        mock_context.return_value = {
            "role": "manager",
            "estate_id": "E001",
            "estate_name": "Greenfield Estate",
            "scope": "current_estate",
        }

        mock_db = mock_db_class.return_value
        mock_db.query.return_value = [
            {
                "status": "Occupied",
                "total": 6,
            },
            {
                "status": "Available",
                "total": 2,
            },
        ]

        response = self.client.get(
            "/api/dashboard/properties-by-status/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        call_args = mock_db.query.call_args
        query = call_args.args[0]
        parameters = call_args.args[1]

        self.assertIn(
            'e.estate_id = $estate_id',
            query,
        )

        self.assertEqual(
            parameters["scope"],
            "current_estate",
        )

        self.assertEqual(
            parameters["estate_id"],
            "E001",
        )
        
    @patch("core.dashboard_views.Neo4jConnection")
    @patch("core.dashboard_views.get_authorization_context")
    def test_admin_properties_by_status_uses_global_scope(
        self,
        mock_context,
        mock_db_class,
    ):
        mock_context.return_value = {
            "role": "admin",
            "estate_id": None,
            "estate_name": None,
            "scope": "global",
        }

        mock_db = mock_db_class.return_value
        mock_db.query.return_value = [
            {
                "status": "Occupied",
                "total": 25,
            },
            {
                "status": "Available",
                "total": 10,
            },
        ]

        response = self.client.get(
            "/api/dashboard/properties-by-status/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        call_args = mock_db.query.call_args
        query = call_args.args[0]
        parameters = call_args.args[1]

        self.assertIn(
        '$scope = "global"',
        query,
        )

        self.assertEqual(
            parameters["scope"],
            "global",
        )

        self.assertIsNone(
            parameters["estate_id"],
        )
        
    @patch("core.dashboard_views.Neo4jConnection")
    @patch("core.dashboard_views.get_authorization_context")
    def test_manager_residents_with_most_complaints_uses_current_estate_scope(
        self,
        mock_context,
        mock_db_class,
    ):
        mock_context.return_value = {
            "role": "manager",
            "estate_id": "E001",
            "estate_name": "Greenfield Estate",
            "scope": "current_estate",
        }

        mock_db = mock_db_class.return_value
        mock_db.query.return_value = [
            {
                "resident_id": "R001",
                "resident_name": "John Doe",
                "total_complaints": 4,
            },
        ]

        response = self.client.get(
            "/api/dashboard/top-residents/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        call_args = mock_db.query.call_args
        query = call_args.args[0]
        parameters = call_args.args[1]

        self.assertIn(
            'e.estate_id = $estate_id',
            query,
        )

        self.assertEqual(
            parameters["scope"],
            "current_estate",
        )

        self.assertEqual(
            parameters["estate_id"],
            "E001",
        )
        
    @patch("core.dashboard_views.Neo4jConnection")
    @patch("core.dashboard_views.get_authorization_context")
    def test_admin_residents_with_most_complaints_uses_global_scope(
        self,
        mock_context,
        mock_db_class,
    ):
        mock_context.return_value = {
            "role": "admin",
            "estate_id": None,
            "estate_name": None,
            "scope": "global",
        }

        mock_db = mock_db_class.return_value
        mock_db.query.return_value = [
            {
                "resident_id": "R001",
                "resident_name": "John Doe",
                "total_complaints": 8,
            },
        ]

        response = self.client.get(
            "/api/dashboard/top-residents/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        call_args = mock_db.query.call_args
        query = call_args.args[0]
        parameters = call_args.args[1]

        self.assertIn(
            '$scope = "global"',
            query,
        )

        self.assertEqual(
            parameters["scope"],
            "global",
        )

        self.assertIsNone(
            parameters["estate_id"],
        )
        
    @patch("core.dashboard_views.Neo4jConnection")
    @patch("core.dashboard_views.get_authorization_context")
    def test_manager_properties_with_most_complaints_uses_current_estate_scope(
        self,
        mock_context,
        mock_db_class,
    ):
        mock_context.return_value = {
            "role": "manager",
            "estate_id": "E001",
            "estate_name": "Greenfield Estate",
            "scope": "current_estate",
        }

        mock_db = mock_db_class.return_value
        mock_db.query.return_value = [
            {
                "property_id": "P001",
                "property_number": "12A",
                "property_type": "Flat",
                "total_complaints": 3,
            }
        ]

        response = self.client.get("/api/dashboard/top-properties/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        query = mock_db.query.call_args.args[0]
        parameters = mock_db.query.call_args.args[1]

        self.assertIn("e.estate_id = $estate_id", query)
        self.assertEqual(parameters["scope"], "current_estate")
        self.assertEqual(parameters["estate_id"], "E001")


    @patch("core.dashboard_views.Neo4jConnection")
    @patch("core.dashboard_views.get_authorization_context")
    def test_admin_properties_with_most_complaints_uses_global_scope(
        self,
        mock_context,
        mock_db_class,
    ):
        mock_context.return_value = {
            "role": "admin",
            "estate_id": None,
            "estate_name": None,
            "scope": "global",
        }

        mock_db = mock_db_class.return_value
        mock_db.query.return_value = [
            {
                "property_id": "P001",
                "property_number": "12A",
                "property_type": "Flat",
                "total_complaints": 3,
            }
        ]

        response = self.client.get("/api/dashboard/top-properties/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        query = mock_db.query.call_args.args[0]
        parameters = mock_db.query.call_args.args[1]

        self.assertIn('$scope = "global"', query)
        self.assertEqual(parameters["scope"], "global")
        self.assertIsNone(parameters["estate_id"])
        
        
    @patch("core.dashboard_views.Neo4jConnection")
    @patch("core.dashboard_views.get_authorization_context")
    def test_manager_recent_complaint_activity_uses_current_estate_scope(
        self,
        mock_context,
        mock_db_class,
    ):
        mock_context.return_value = {
            "role": "manager",
            "estate_id": "E001",
            "estate_name": "Greenfield Estate",
            "scope": "current_estate",
        }

        mock_db = mock_db_class.return_value
        mock_db.query.return_value = [
            {
                "complaint_id": "C001",
                "title": "Leaking pipe",
                "category": "Plumbing",
                "priority": "High",
                "status": "Open",
                "resident_name": "Joshua",
                "property_number": "12A",
                "created_at": "2026-09-30T10:00:00",
            }
        ]

        response = self.client.get("/api/dashboard/recent-complaints/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        query = mock_db.query.call_args.args[0]
        parameters = mock_db.query.call_args.args[1]

        self.assertIn("e.estate_id = $estate_id", query)
        self.assertEqual(parameters["scope"], "current_estate")
        self.assertEqual(parameters["estate_id"], "E001")


    @patch("core.dashboard_views.Neo4jConnection")
    @patch("core.dashboard_views.get_authorization_context")
    def test_admin_recent_complaint_activity_uses_global_scope(
        self,
        mock_context,
        mock_db_class,
    ):
        mock_context.return_value = {
            "role": "admin",
            "estate_id": None,
            "estate_name": None,
            "scope": "global",
        }

        mock_db = mock_db_class.return_value
        mock_db.query.return_value = [
            {
                "complaint_id": "C001",
                "title": "Leaking pipe",
                "category": "Plumbing",
                "priority": "High",
                "status": "Open",
                "resident_name": "Joshua",
                "property_number": "12A",
                "created_at": "2026-09-30T10:00:00",
            }
        ]

        response = self.client.get("/api/dashboard/recent-complaints/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        query = mock_db.query.call_args.args[0]
        parameters = mock_db.query.call_args.args[1]

        self.assertIn('$scope = "global"', query)
        self.assertEqual(parameters["scope"], "global")
        self.assertIsNone(parameters["estate_id"])