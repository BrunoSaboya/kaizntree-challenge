import api from "./client";
import type { PaginatedResponse } from "@/types/product";
import type { PurchaseOrder, SalesOrder } from "@/types/orders";

export interface OrderFilters {
  product?: number;
  status?: string;
  page?: number;
}

export const purchaseOrdersApi = {
  list: (filters: OrderFilters = {}) =>
    api.get<PaginatedResponse<PurchaseOrder>>("/purchase-orders/", { params: filters }).then((r) => r.data),

  get: (id: number) => api.get<PurchaseOrder>(`/purchase-orders/${id}/`).then((r) => r.data),

  create: (data: Partial<PurchaseOrder>) =>
    api.post<PurchaseOrder>("/purchase-orders/", data).then((r) => r.data),

  update: (id: number, data: Partial<PurchaseOrder>) =>
    api.patch<PurchaseOrder>(`/purchase-orders/${id}/`, data).then((r) => r.data),

  delete: (id: number) => api.delete(`/purchase-orders/${id}/`),

  confirm: (id: number, stockIdentifier: string) =>
    api.post<PurchaseOrder>(`/purchase-orders/${id}/confirm/`, { stock_identifier: stockIdentifier }).then((r) => r.data),

  cancel: (id: number) =>
    api.post<PurchaseOrder>(`/purchase-orders/${id}/cancel/`).then((r) => r.data),
};

export const salesOrdersApi = {
  list: (filters: OrderFilters = {}) =>
    api.get<PaginatedResponse<SalesOrder>>("/sales-orders/", { params: filters }).then((r) => r.data),

  get: (id: number) => api.get<SalesOrder>(`/sales-orders/${id}/`).then((r) => r.data),

  create: (data: Partial<SalesOrder>) =>
    api.post<SalesOrder>("/sales-orders/", data).then((r) => r.data),

  update: (id: number, data: Partial<SalesOrder>) =>
    api.patch<SalesOrder>(`/sales-orders/${id}/`, data).then((r) => r.data),

  delete: (id: number) => api.delete(`/sales-orders/${id}/`),

  confirm: (id: number) =>
    api.post<SalesOrder>(`/sales-orders/${id}/confirm/`).then((r) => r.data),

  cancel: (id: number) =>
    api.post<SalesOrder>(`/sales-orders/${id}/cancel/`).then((r) => r.data),
};
