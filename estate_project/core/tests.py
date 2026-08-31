from django.test import TestCase

from .ai_service import generate_cypher
from .cypher_guard import is_safe_cypher
from .cypher_normalizer import normalize_cypher
from .views import format_results

from rest_framework.test import APITestCase
from unittest.mock import patch
from rest_framework import status

from django.contrib.auth import get_user_model


class CypherNormalizerTests(TestCase):

    def test_status_is_normalized(self):
        query = 'MATCH (p:Property) WHERE p.status = "available" RETURN p'
        result = normalize_cypher(query)

        self.assertIn('"Available"', result)

    def test_in_progress_is_normalized(self):
        query = 'MATCH (c:Complaint) WHERE c.status = "in progress" RETURN c'
        result = normalize_cypher(query)

        self.assertIn('"In Progress"', result)

    def test_unrelated_query_is_unchanged(self):
        query = "MATCH (p:Property) RETURN p"
        self.assertEqual(normalize_cypher(query), query)


class CypherGuardTests(TestCase):

    def test_match_is_allowed(self):
        query = "MATCH (p:Property) RETURN p"
        self.assertTrue(is_safe_cypher(query))

    def test_optional_match_is_allowed(self):
        query = "OPTIONAL MATCH (p:Property) RETURN p"
        self.assertTrue(is_safe_cypher(query))

    def test_invalid_start_is_rejected(self):
        query = "MATCHING (p:Property) RETURN p"
        self.assertFalse(is_safe_cypher(query))

    def test_delete_is_rejected(self):
        query = "MATCH (p:Property) RETURN p; DELETE p"
        self.assertFalse(is_safe_cypher(query))


class GenerateCypherTests(TestCase):

    def test_resident_property_uses_parameter(self):
        result = generate_cypher("Where does Jane Smith live?")

        cypher, parameters = result

        self.assertIn("$resident_name", cypher)
        self.assertEqual(
            parameters,
            {"resident_name": "Jane Smith"},
        )

    def test_resident_by_property_uses_parameter(self):
        result = generate_cypher("Who lives in B201?")

        cypher, parameters = result

        self.assertIn("$property_number", cypher)
        self.assertEqual(
            parameters,
            {"property_number": "B201"},
        )

    def test_manager_query_uses_parameter(self):
        result = generate_cypher(
            "Who manages the property where John Doe lives?"
        )

        cypher, parameters = result

        self.assertIn("$resident_name", cypher)
        self.assertEqual(
            parameters,
            {"resident_name": "John Doe"},
        )


class FormatterTests(TestCase):

    def test_residents_formatter(self):
        data = [
            {
                "resident_id": "R003",
                "name": "John Doe",
            }
        ]

        result = format_results("Show all residents", data)

        self.assertIn("John Doe", result)
        self.assertIn("R003", result)

    def test_resident_location_formatter(self):
        data = [
            {
                "resident_id": "R004",
                "name": "Jane Smith",
                "property_id": "P004",
                "property_number": "C301",
                "property_type": "Duplex",
                "estate_id": "E001",
                "estate": "Greenfield Estate",
            }
        ]

        result = format_results(
            "Where does Jane Smith live?",
            data,
        )

        self.assertIn("Jane Smith", result)
        self.assertIn("C301", result)
        self.assertIn("Greenfield Estate", result)

    def test_properties_needing_attention_formatter(self):
        data = [
            {
                "property_id": "P002",
                "property_number": "B201",
                "property_type": "Apartment",
                "status": "Occupied",
                "complaint_count": 1,
            }
        ]

        result = format_results(
            "What properties need attention?",
            data,
        )

        self.assertIn("Properties Needing Attention", result)
        self.assertIn("B201", result)
        self.assertIn("1 complaint", result)
        

class AIQueryV3APITests(APITestCase):

    def setUp(self):
        self.url = "/api/ai/v3/"

        User = get_user_model()

        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword123",
        )

        self.client.force_authenticate(user=self.user)
        
        
    @patch("core.views.execute_cypher")
    @patch("core.views.generate_cypher")
    def test_valid_ai_query(self, mock_generate, mock_execute):
        mock_generate.return_value = (
            "MATCH (r:Resident) RETURN r.resident_id AS resident_id, r.name AS name",
            {},
        )

        mock_execute.return_value = [
            {
                "resident_id": "R003",
                "name": "John Doe",
            }
        ]

        response = self.client.post(
            self.url,
            {"question": "Show all residents"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["question"], "Show all residents")
        self.assertIn("John Doe", response.data["response"])

    def test_empty_question(self):
        response = self.client.post(
            self.url,
            {"question": ""},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"],
            "Question cannot be empty.",
        )

    @patch("core.views.generate_cypher")
    def test_unsafe_cypher_is_rejected(self, mock_generate):
        mock_generate.return_value = (
            "MATCH (p:Property) DELETE p",
            {},
        )

        response = self.client.post(
            self.url,
            {"question": "Delete all properties"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"],
            "Unsafe Cypher generated.",
        )

    @patch("core.views.generate_cypher")
    def test_unsupported_query(self, mock_generate):
        mock_generate.return_value = (
            'RETURN "UNSUPPORTED_QUERY" AS error',
            {},
        )

        response = self.client.post(
            self.url,
            {"question": "What is the weather today?"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"], [])

    @patch("core.views.generate_cypher")
    def test_empty_generated_cypher(self, mock_generate):
        mock_generate.return_value = ("", {})

        response = self.client.post(
            self.url,
            {"question": "Show residents"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(
            response.data["error"],
            "Unable to generate a valid database query.",
        )