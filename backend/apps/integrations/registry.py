"""
Integration registry — instantiates adapters from Django settings.

Adapters are only created when their required credentials are present.
Missing credentials return None (graceful degradation), matching the same
pattern used for ANTHROPIC_API_KEY in the ai_workflows app.

Usage:
    from apps.integrations.registry import get_shopify_adapter, get_quickbooks_adapter

    adapter = get_shopify_adapter()
    if adapter is None:
        return Response({"error": "Shopify is not configured."}, status=503)
"""

from django.conf import settings

from .adapters.shopify import ShopifyAdapter
from .adapters.amazon import AmazonAdapter
from .adapters.quickbooks import QuickBooksAdapter
from .adapters.netsuite import NetSuiteAdapter


def get_shopify_adapter() -> ShopifyAdapter | None:
    secret = getattr(settings, "SHOPIFY_WEBHOOK_SECRET", "")
    if not secret:
        return None
    return ShopifyAdapter(
        webhook_secret=secret,
        shop_domain=getattr(settings, "SHOPIFY_SHOP_DOMAIN", ""),
        access_token=getattr(settings, "SHOPIFY_ACCESS_TOKEN", ""),
    )


def get_amazon_adapter() -> AmazonAdapter | None:
    seller_id = getattr(settings, "AMAZON_SELLER_ID", "")
    if not seller_id:
        return None
    return AmazonAdapter(
        seller_id=seller_id,
        lwa_client_id=getattr(settings, "AMAZON_LWA_CLIENT_ID", ""),
        lwa_client_secret=getattr(settings, "AMAZON_LWA_CLIENT_SECRET", ""),
        lwa_refresh_token=getattr(settings, "AMAZON_LWA_REFRESH_TOKEN", ""),
        aws_access_key=getattr(settings, "AMAZON_AWS_ACCESS_KEY", ""),
        aws_secret_key=getattr(settings, "AMAZON_AWS_SECRET_KEY", ""),
        marketplace_id=getattr(settings, "AMAZON_MARKETPLACE_ID", "ATVPDKIKX0DER"),
    )


def get_quickbooks_adapter() -> QuickBooksAdapter | None:
    client_id = getattr(settings, "QUICKBOOKS_CLIENT_ID", "")
    if not client_id:
        return None
    return QuickBooksAdapter(
        client_id=client_id,
        realm_id=getattr(settings, "QUICKBOOKS_REALM_ID", ""),
        environment=getattr(settings, "QUICKBOOKS_ENVIRONMENT", "sandbox"),
        client_secret=getattr(settings, "QUICKBOOKS_CLIENT_SECRET", ""),
        access_token=getattr(settings, "QUICKBOOKS_ACCESS_TOKEN", ""),
        refresh_token=getattr(settings, "QUICKBOOKS_REFRESH_TOKEN", ""),
    )


def get_netsuite_adapter() -> NetSuiteAdapter | None:
    account_id = getattr(settings, "NETSUITE_ACCOUNT_ID", "")
    if not account_id:
        return None
    return NetSuiteAdapter(
        account_id=account_id,
        subsidiary_id=getattr(settings, "NETSUITE_SUBSIDIARY_ID", "1"),
        consumer_key=getattr(settings, "NETSUITE_CONSUMER_KEY", ""),
        consumer_secret=getattr(settings, "NETSUITE_CONSUMER_SECRET", ""),
        token_id=getattr(settings, "NETSUITE_TOKEN_ID", ""),
        token_secret=getattr(settings, "NETSUITE_TOKEN_SECRET", ""),
    )


def get_integration_status() -> dict:
    """Returns which integrations are configured (credentials present)."""
    return {
        "shopify": get_shopify_adapter() is not None,
        "amazon": get_amazon_adapter() is not None,
        "quickbooks": get_quickbooks_adapter() is not None,
        "netsuite": get_netsuite_adapter() is not None,
    }
