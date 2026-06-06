from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.inventory.tests.factories import ProductFactory, UserFactory


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    token = AccessToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def _make_mock_response(extracted: dict):
    block = MagicMock()
    block.type = "tool_use"
    block.name = "extract_purchase_order"
    block.input = extracted
    response = MagicMock()
    response.content = [block]
    return response


@pytest.mark.django_db
class TestParsePurchaseOrderView:
    URL = "parse-purchase-order"

    def test_auth_required(self):
        client = APIClient()
        resp = client.post(reverse(self.URL), {"text": "invoice..."}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_text_returns_400(self, auth_client):
        resp = auth_client.post(reverse(self.URL), {"text": ""}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_text_returns_400(self, auth_client):
        resp = auth_client.post(reverse(self.URL), {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_503_when_api_key_absent(self, auth_client, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        resp = auth_client.post(
            reverse(self.URL), {"text": "Invoice from vendor"}, format="json"
        )
        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_successful_parse_response_shape(self, auth_client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        extracted = {
            "supplier_name": "Acme Farms",
            "order_date": "2025-01-15",
            "line_items": [
                {"raw_product_name": "Organic Oats", "quantity": 100, "cost_per_unit": 2.50}
            ],
            "confidence_score": 0.95,
            "extraction_notes": "",
        }
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(extracted)

        with patch("apps.ai_workflows.services.anthropic.Anthropic", return_value=mock_client):
            resp = auth_client.post(
                reverse(self.URL),
                {"text": "Invoice from Acme Farms: 100 units of Organic Oats @ $2.50"},
                format="json",
            )

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["supplier_name"] == "Acme Farms"
        assert data["confidence_score"] == 0.95
        assert len(data["line_items"]) == 1
        assert "product_matches" in data
        assert "order_date" in data

    def test_product_fuzzy_match_found(self, auth_client, user, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        ProductFactory(organization=user.organization, name="Organic Oats", sku="OAT-001")
        extracted = {
            "supplier_name": "Acme",
            "line_items": [{"raw_product_name": "Organic Oats", "quantity": 50}],
            "confidence_score": 0.9,
        }
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(extracted)

        with patch("apps.ai_workflows.services.anthropic.Anthropic", return_value=mock_client):
            resp = auth_client.post(
                reverse(self.URL), {"text": "50 units Organic Oats"}, format="json"
            )

        assert resp.status_code == status.HTTP_200_OK
        match = resp.json()["product_matches"][0]
        assert match["matched_product"] is not None
        assert match["matched_product"]["name"] == "Organic Oats"
        assert match["match_confidence"] >= 0.9

    def test_no_product_match_when_catalog_empty(self, auth_client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        extracted = {
            "supplier_name": "Unknown Vendor",
            "line_items": [{"raw_product_name": "Mystery Spice", "quantity": 10}],
            "confidence_score": 0.7,
        }
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(extracted)

        with patch("apps.ai_workflows.services.anthropic.Anthropic", return_value=mock_client):
            resp = auth_client.post(
                reverse(self.URL), {"text": "10 Mystery Spice"}, format="json"
            )

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["product_matches"][0]["matched_product"] is None

    def test_graceful_degradation_when_no_tool_use_returned(self, auth_client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        mock_response = MagicMock()
        mock_response.content = []
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("apps.ai_workflows.services.anthropic.Anthropic", return_value=mock_client):
            resp = auth_client.post(
                reverse(self.URL), {"text": "not an invoice"}, format="json"
            )

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["confidence_score"] == 0.0
        assert data["line_items"] == []
        assert data["product_matches"] == []
