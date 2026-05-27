import axios from "axios";
import { useAuthStore } from "@/store/authStore";

let _refreshPromise: Promise<string> | null = null;

/**
 * Calls /auth/refresh/ at most once at a time.
 *
 * Any caller that arrives while a refresh is already in flight receives the
 * same Promise — no second HTTP request is made and no duplicate JTI is
 * inserted into token_blacklist_outstandingtoken.
 *
 * This prevents the race between:
 *  - App.tsx session-restore on mount (and React StrictMode's double-invoke)
 *  - client.ts 401 interceptor firing concurrently
 */
export function getOrStartRefresh(): Promise<string> {
  if (!_refreshPromise) {
    _refreshPromise = axios
      .post<{ access: string }>("/api/v1/auth/refresh/", {}, { withCredentials: true })
      .then(({ data }) => {
        useAuthStore.getState().setAccessToken(data.access);
        return data.access;
      })
      .finally(() => {
        _refreshPromise = null;
      });
  }
  return _refreshPromise;
}
