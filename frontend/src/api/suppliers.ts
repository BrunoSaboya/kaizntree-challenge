import api from "./client";
import type { PaginatedResponse } from "@/types/product";
import type { Supplier } from "@/types/supplier";

export interface SupplierFilters {
  active?: boolean;
  search?: string;
  page?: number;
}

export const suppliersApi = {
  list: (filters: SupplierFilters = {}) =>
    api.get<PaginatedResponse<Supplier>>("/suppliers/", { params: filters }).then((r) => r.data),

  get: (id: number) => api.get<Supplier>(`/suppliers/${id}/`).then((r) => r.data),

  create: (data: Partial<Supplier>) =>
    api.post<Supplier>("/suppliers/", data).then((r) => r.data),

  update: (id: number, data: Partial<Supplier>) =>
    api.patch<Supplier>(`/suppliers/${id}/`, data).then((r) => r.data),

  delete: (id: number) => api.delete(`/suppliers/${id}/`),
};
