import api from "./client";
import { REFRESH_TOKEN_KEY } from "./authRefresh";
import type { AuthTokens, LoginPayload, RegisterPayload, User } from "@/types/auth";

/** Persist the refresh token for the sessionStorage fallback path. */
function storeRefreshToken(data: AuthTokens): AuthTokens {
  if (data.refresh_token) {
    sessionStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
  }
  return data;
}

export const authApi = {
  login: (payload: LoginPayload) =>
    api.post<AuthTokens>("/auth/login/", payload).then((r) => storeRefreshToken(r.data)),

  register: (payload: RegisterPayload) =>
    api.post<AuthTokens>("/auth/register/", payload).then((r) => storeRefreshToken(r.data)),

  logout: () => {
    // Clear the sessionStorage fallback token before the server-side blacklist
    sessionStorage.removeItem(REFRESH_TOKEN_KEY);
    return api.post("/auth/logout/");
  },

  me: () => api.get<User>("/auth/me/").then((r) => r.data),
};
