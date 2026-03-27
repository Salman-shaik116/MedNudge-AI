import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase


class AIDoctorChatApiTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.user = User.objects.create_user(
			username="testuser",
			email="test@example.com",
			password="pass12345",
		)

	def test_unauthenticated_returns_401(self):
		res = self.client.post(
			"/api/ai-doctor/chat/",
			data=json.dumps({"message": "hello"}),
			content_type="application/json",
		)
		self.assertEqual(res.status_code, 401)

	def test_invalid_json_returns_400(self):
		self.client.login(username="testuser", password="pass12345")
		res = self.client.post(
			"/api/ai-doctor/chat/",
			data="{not json}",
			content_type="application/json",
		)
		self.assertEqual(res.status_code, 400)

	@patch("website.views.SymptomAgent")
	def test_valid_request_returns_reply(self, mock_agent_cls):
		self.client.login(username="testuser", password="pass12345")

		mock_agent = mock_agent_cls.return_value
		mock_agent.reply.return_value = "Test reply"

		res = self.client.post(
			"/api/ai-doctor/chat/",
			data=json.dumps({"message": "I have a headache"}),
			content_type="application/json",
		)

		self.assertEqual(res.status_code, 200)
		payload = res.json()
		self.assertEqual(payload.get("reply"), "Test reply")
		mock_agent.reply.assert_called_once()
