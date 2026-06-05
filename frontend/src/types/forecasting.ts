export type ReorderStatus = "OK" | "LOW" | "CRITICAL" | "OUT_OF_STOCK";

export const REORDER_STATUS_LABELS: Record<ReorderStatus, string> = {
  OK: "OK",
  LOW: "Low Stock",
  CRITICAL: "Critical",
  OUT_OF_STOCK: "Out of Stock",
};

export const REORDER_STATUS_COLORS: Record<ReorderStatus, string> = {
  OK: "green",
  LOW: "yellow",
  CRITICAL: "orange",
  OUT_OF_STOCK: "red",
};

export interface ReorderRecommendation {
  product_id: number;
  product_name: string;
  sku: string;
  unit_type: string;
  current_stock: number;
  avg_daily_consumption: number;
  sigma_daily: number;
  safety_stock: number;
  reorder_point: number;
  days_of_stock_remaining: number | null;
  recommended_reorder_qty: number;
  lead_time_days: number;
  status: ReorderStatus;
}
