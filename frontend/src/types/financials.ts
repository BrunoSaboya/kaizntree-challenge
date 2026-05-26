export interface ProductFinancials {
  product_id: number;
  product_name: string;
  sku: string;
  unit_type: string;
  total_cost: string;
  total_revenue: string;
  profit: string;
  margin_pct: string | null;
  units_purchased: string;
  units_sold: string;
  current_stock: string;
}

export interface FinancialSummary {
  total_cost: string;
  total_revenue: string;
  total_profit: string;
  overall_margin_pct: string | null;
  product_count: number;
}
