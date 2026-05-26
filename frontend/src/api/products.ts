import api from "./client";
import type { PaginatedResponse, Product, Stock } from "@/types/product";
import type { ProductFinancials } from "@/types/financials";

export interface ProductFilters {
  search?: string;
  unit_type?: string;
  page?: number;
  page_size?: number;
}

export const productsApi = {
  list: (filters: ProductFilters = {}) =>
    api.get<PaginatedResponse<Product>>("/products/", { params: filters }).then((r) => r.data),

  get: (id: number) => api.get<Product>(`/products/${id}/`).then((r) => r.data),

  create: (data: Partial<Product>) =>
    api.post<Product>("/products/", data).then((r) => r.data),

  update: (id: number, data: Partial<Product>) =>
    api.patch<Product>(`/products/${id}/`, data).then((r) => r.data),

  delete: (id: number) => api.delete(`/products/${id}/`),

  getStock: (id: number) =>
    api.get<Stock[]>(`/products/${id}/stock/`).then((r) => r.data),

  getFinancials: (id: number) =>
    api.get<ProductFinancials>(`/products/${id}/financials/`).then((r) => r.data),
};
