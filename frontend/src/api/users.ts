import api from "./client";
import type { CreateUserPayload, OrgMember, PaginatedResponse, User } from "@/types/auth";

export interface UserUpdatePayload {
  first_name?: string;
  last_name?: string;
  role?: string;
  organization?: number | null;
  is_active?: boolean;
}

export const usersApi = {
  list: () => api.get<PaginatedResponse<User>>("/users/").then((r) => r.data.results),

  create: (payload: CreateUserPayload) =>
    api.post<User>("/users/", payload).then((r) => r.data),

  update: (id: number, payload: UserUpdatePayload) =>
    api.patch<User>(`/users/${id}/`, payload).then((r) => r.data),

  deactivate: (id: number) => api.delete(`/users/${id}/`),

  hardDelete: (id: number) => api.delete(`/users/${id}/hard-delete/`),

  reactivate: (id: number) =>
    api.patch<User>(`/users/${id}/`, { is_active: true }).then((r) => r.data),
};

export const membersApi = {
  list: () => api.get<PaginatedResponse<OrgMember>>("/org/members/").then((r) => r.data.results),

  create: (payload: { email: string; username: string; first_name?: string; last_name?: string; password: string }) =>
    api.post<OrgMember>("/org/members/", payload).then((r) => r.data),

  update: (id: number, payload: { first_name?: string; last_name?: string; password?: string }) =>
    api.patch<OrgMember>(`/org/members/${id}/`, payload).then((r) => r.data),

  deactivate: (id: number) => api.delete(`/org/members/${id}/`),
};
