import api from "./client";
import type { CreateOrgPayload, Organization, PaginatedResponse, ProvisionOrgPayload } from "@/types/auth";

export const orgsApi = {
  list: () => api.get<PaginatedResponse<Organization>>("/organizations/").then((r) => r.data.results),

  provision: (payload: ProvisionOrgPayload) =>
    api.post<Organization>("/organizations/provision/", payload).then((r) => r.data),

  create: (payload: CreateOrgPayload) =>
    api.post<Organization>("/organizations/", payload).then((r) => r.data),

  update: (id: number, payload: Partial<CreateOrgPayload>) =>
    api.patch<Organization>(`/organizations/${id}/`, payload).then((r) => r.data),
};
