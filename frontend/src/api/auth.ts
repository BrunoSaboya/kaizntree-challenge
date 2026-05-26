import api from "./client";
import type { AuthTokens, LoginPayload, RegisterPayload, User } from "@/types/auth";

export const authApi = {
  login: (payload: LoginPayload) =>
    api.post<AuthTokens>("/auth/login/", payload).then((r) => r.data),

  register: (payload: RegisterPayload) =>
    api.post<AuthTokens>("/auth/register/", payload).then((r) => r.data),

  logout: () => api.post("/auth/logout/"),

  me: () => api.get<User>("/auth/me/").then((r) => r.data),
};
