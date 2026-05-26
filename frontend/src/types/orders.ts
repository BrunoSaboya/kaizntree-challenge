export type OrderStatus = "draft" | "confirmed" | "cancelled";

export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  draft: "Draft",
  confirmed: "Confirmed",
  cancelled: "Cancelled",
};

export const ORDER_STATUS_COLORS: Record<OrderStatus, string> = {
  draft: "yellow",
  confirmed: "green",
  cancelled: "red",
};

export interface PurchaseOrder {
  id: number;
  product: number;
  product_name: string;
  product_sku: string;
  stock: number | null;
  stock_identifier: string | null;
  quantity: string;
  cost_per_unit: string;
  total_cost: string;
  status: OrderStatus;
  notes: string;
  order_date: string;
  created_at: string;
  updated_at: string;
}

export interface SalesOrder {
  id: number;
  product: number;
  product_name: string;
  product_sku: string;
  stock: number | null;
  stock_identifier: string | null;
  quantity: string;
  price_per_unit: string;
  total_revenue: string;
  status: OrderStatus;
  notes: string;
  order_date: string;
  created_at: string;
  updated_at: string;
}
