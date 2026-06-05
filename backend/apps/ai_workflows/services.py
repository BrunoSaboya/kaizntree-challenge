"""
AI-powered document parsing for purchase order extraction.

Accepts free-form text (invoice, email, vendor quote) and returns a structured
draft PO payload. Never auto-creates or confirms any order — the caller is
always responsible for the final submission after human review.
"""

import difflib
import json
import os

import anthropic

from apps.inventory.models import Product


class AIServiceUnavailableError(Exception):
    pass


_EXTRACT_TOOL = {
    "name": "extract_purchase_order",
    "description": (
        "Extract structured purchase order data from an invoice, email, or vendor quote."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "supplier_name": {
                "type": "string",
                "description": "Supplier/vendor name as it appears in the document",
            },
            "order_date": {
                "type": "string",
                "description": "Order or invoice date in YYYY-MM-DD format; omit if not present",
            },
            "line_items": {
                "type": "array",
                "description": "All product line items found in the order",
                "items": {
                    "type": "object",
                    "properties": {
                        "raw_product_name": {
                            "type": "string",
                            "description": "Product name exactly as written in the document",
                        },
                        "quantity": {
                            "type": "number",
                            "description": "Quantity ordered",
                        },
                        "cost_per_unit": {
                            "type": "number",
                            "description": "Unit price; omit if not stated",
                        },
                        "notes": {
                            "type": "string",
                            "description": "Packaging notes or additional description",
                        },
                    },
                    "required": ["raw_product_name", "quantity"],
                },
            },
            "confidence_score": {
                "type": "number",
                "description": "Overall extraction confidence between 0.0 and 1.0",
            },
            "extraction_notes": {
                "type": "string",
                "description": "Any ambiguities or issues found during extraction",
            },
        },
        "required": ["supplier_name", "line_items", "confidence_score"],
    },
}


def _fuzzy_match_products(line_items: list[dict], catalog: list[dict]) -> list[dict]:
    """Score each extracted line item against the user's product catalog."""
    results = []
    for item in line_items:
        raw = item.get("raw_product_name", "").lower().strip()
        best_product = None
        best_score = 0.0

        for product in catalog:
            name_score = difflib.SequenceMatcher(None, raw, product["name"].lower()).ratio()
            sku_score = difflib.SequenceMatcher(None, raw, product["sku"].lower()).ratio()
            score = max(name_score, sku_score)
            if score > best_score:
                best_score = score
                best_product = product

        results.append({
            "raw_product_name": item.get("raw_product_name"),
            "quantity": item.get("quantity"),
            "cost_per_unit": item.get("cost_per_unit"),
            "notes": item.get("notes", ""),
            "match_confidence": round(best_score, 2),
            "matched_product": best_product if best_score >= 0.5 else None,
        })
    return results


def parse_purchase_order_document(text: str, user) -> dict:
    """
    Parse free-form invoice or vendor quote text into a structured draft PO.

    Returns a dict for display in a human-review UI. Raises
    AIServiceUnavailableError when ANTHROPIC_API_KEY is absent.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise AIServiceUnavailableError("ANTHROPIC_API_KEY is not configured")

    catalog = list(Product.objects.filter(owner=user).values("id", "name", "sku"))

    system_prompt = (
        "You are a document parsing assistant for a CPG inventory management system. "
        "Extract purchase order data precisely from the provided text. "
        "Only populate fields that are explicitly stated in the document."
    )
    if catalog:
        system_prompt += (
            "\n\nUser's existing products (use for context when identifying items):\n"
            + json.dumps(catalog, indent=2)
        )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Extract purchase order data from this document:\n\n{text}",
            }
        ],
        tools=[_EXTRACT_TOOL],
        tool_choice={"type": "any"},
    )

    extracted = None
    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_purchase_order":
            extracted = block.input
            break

    if not extracted:
        return {
            "supplier_name": None,
            "order_date": None,
            "line_items": [],
            "product_matches": [],
            "confidence_score": 0.0,
            "extraction_notes": "No structured data could be extracted from the document.",
        }

    line_items = extracted.get("line_items", [])
    return {
        "supplier_name": extracted.get("supplier_name"),
        "order_date": extracted.get("order_date"),
        "line_items": line_items,
        "product_matches": _fuzzy_match_products(line_items, catalog),
        "confidence_score": extracted.get("confidence_score", 0.0),
        "extraction_notes": extracted.get("extraction_notes", ""),
    }
