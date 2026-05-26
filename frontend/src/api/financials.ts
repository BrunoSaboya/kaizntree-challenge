import api from "./client";
import type { FinancialSummary, ProductFinancials } from "@/types/financials";

export const financialsApi = {
  summary: () => api.get<FinancialSummary>("/financials/summary/").then((r) => r.data),
  products: () => api.get<ProductFinancials[]>("/financials/products/").then((r) => r.data),
};
