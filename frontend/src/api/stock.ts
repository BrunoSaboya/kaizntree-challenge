import api from "./client";
import type { PaginatedResponse, Stock } from "@/types/product";

export interface StockFilters {
  product?: number;
  page?: number;
}

export const stockApi = {
  list: (filters: StockFilters = {}) =>
    api.get<PaginatedResponse<Stock>>("/stock/", { params: filters }).then((r) => r.data),

  get: (id: number) => api.get<Stock>(`/stock/${id}/`).then((r) => r.data),

  create: (data: Partial<Stock>) =>
    api.post<Stock>("/stock/", data).then((r) => r.data),

  update: (id: number, data: Partial<Stock>) =>
    api.patch<Stock>(`/stock/${id}/`, data).then((r) => r.data),

  delete: (id: number) => api.delete(`/stock/${id}/`),

  expiringSoon: (days = 30) =>
    api.get<Stock[]>("/stock/expiring_soon/", { params: { days } }).then((r) => r.data),
};
