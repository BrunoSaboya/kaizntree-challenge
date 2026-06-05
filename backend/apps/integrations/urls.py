from django.urls import path
from .views import IntegrationStatusView, ShopifyWebhookView

urlpatterns = [
    path("integrations/status/", IntegrationStatusView.as_view(), name="integration-status"),
    path("integrations/shopify/webhook/", ShopifyWebhookView.as_view(), name="shopify-webhook"),
]
