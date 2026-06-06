export type UnitType = "kg" | "g" | "l" | "ml" | "count";

export const UNIT_TYPE_LABELS: Record<UnitType, string> = {
  kg: "Kilograms",
  g: "Grams",
  l: "Litres",
  ml: "Millilitres",
  count: "Unit",
};

export interface Product {
  id: number;
  name: string;
  description: string;
  sku: string;
  unit_type: UnitType;
  min_stock_quantity: number;
  total_stock: string | null;
  created_at: string;
  updated_at: string;
}

export interface Stock {
  id: number;
  product: number;
  product_name: string;
  product_sku: string;
  identifier: string;
  quantity: string;
  notes: string;
  expiry_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
