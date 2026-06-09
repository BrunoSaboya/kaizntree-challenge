export interface ProductFinancials {
  product_id: number;
  product_name: string;
  sku: string;
  unit_type: string;
  min_stock_quantity: number;
  total_cost: string;
  cogs: string;
  total_revenue: string;
  profit: string;
  margin_pct: string | null;
  units_purchased: string;
  units_sold: string;
  current_stock: string;
  inventory_value: string;
}

export interface FinancialSummary {
  total_cost: string;
  total_cogs: string;
  total_revenue: string;
  total_profit: string;
  overall_margin_pct: string | null;
  inventory_value: string;
  product_count: number;
}
