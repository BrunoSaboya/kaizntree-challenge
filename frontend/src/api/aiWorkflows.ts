import api from "./client";

export interface ParsedLineItem {
  raw_product_name: string;
  quantity: number;
  cost_per_unit: number | null;
  notes: string;
}

export interface ProductMatch {
  raw_product_name: string;
  quantity: number;
  cost_per_unit: number | null;
  notes: string;
  match_confidence: number;
  matched_product: { id: number; name: string; sku: string } | null;
}

export interface ParsedPurchaseOrder {
  supplier_name: string | null;
  order_date: string | null;
  line_items: ParsedLineItem[];
  product_matches: ProductMatch[];
  confidence_score: number;
  extraction_notes: string;
}

export const aiWorkflowsApi = {
  parsePurchaseOrder: (text: string) =>
    api.post<ParsedPurchaseOrder>("/ai/parse-purchase-order/", { text }).then((r) => r.data),
};
