import axios from "axios";
import { useAuthStore } from "@/store/authStore";

/**
 * sessionStorage key for the refresh token fallback.
 * Exported so auth.ts can write/clear it on login and logout.
 */
export const REFRESH_TOKEN_KEY = "kz_refresh_token";

let _refreshPromise: Promise<string> | null = null;

/**
 * Calls /auth/refresh/ at most once at a time.
 *
 * Two-phase refresh strategy:
 *
 * Phase 1 — cookie-based (primary):
 *   The backend sets an httpOnly refresh cookie on login. When the Vercel proxy
 *   correctly forwards Set-Cookie headers this works transparently.
 *
 * Phase 2 — sessionStorage fallback:
 *   When the cookie is absent (Brave Shields, Safari ITP, or Vercel stripping
 *   Set-Cookie from proxied responses), the stored token is sent in the request
 *   body instead. The backend accepts either source.
 *
 * On every successful refresh the backend returns the NEW rotated refresh token
 * in the response body (`refresh_token` field). We always update sessionStorage
 * so it stays in sync with the latest token.
 */
export function getOrStartRefresh(): Promise<string> {
  if (!_refreshPromise) {
    const apiOrigin = import.meta.env.VITE_API_URL ?? "";
    const url = `${apiOrigin}/api/v1/auth/refresh/`;

    // Phase 1: try the httpOnly cookie (no body payload needed)
    _refreshPromise = axios
      .post<{ access: string; refresh_token?: string }>(url, {}, { withCredentials: true })
      .then(({ data }) => {
        // Keep sessionStorage in sync with the rotated token
        if (data.refresh_token) {
          sessionStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
        }
        useAuthStore.getState().setAccessToken(data.access);
        return data.access;
      })
      .catch(() => {
        // Phase 2: cookie unavailable — try the sessionStorage copy
        const stored = sessionStorage.getItem(REFRESH_TOKEN_KEY);
        if (!stored) throw new Error("No refresh token available");

        return axios
          .post<{ access: string; refresh_token?: string }>(
            url,
            { refresh: stored },
            { withCredentials: true },
          )
          .then(({ data }) => {
            if (data.refresh_token) {
              sessionStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
            }
            useAuthStore.getState().setAccessToken(data.access);
            return data.access;
          })
          .catch((err) => {
            // Token is expired or blacklisted — clear it so we don't retry
            sessionStorage.removeItem(REFRESH_TOKEN_KEY);
            throw err;
          });
      })
      .finally(() => {
        _refreshPromise = null;
      });
  }
  return _refreshPromise;
}
