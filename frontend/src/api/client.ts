import axios from "axios";
import { useAuthStore } from "@/store/authStore";
import { getOrStartRefresh } from "@/api/authRefresh";

// In development, VITE_API_URL is empty so the relative "/api/v1" path
// falls through to Vite's dev-server proxy (vite.config.ts).
// In production (Vercel), VITE_API_URL is the Railway backend URL so
// every request goes directly to the correct origin.
const API_ORIGIN = import.meta.env.VITE_API_URL ?? "";

const api = axios.create({
  baseURL: `${API_ORIGIN}/api/v1`,
  withCredentials: true, // send cookies for refresh
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let pendingRequests: Array<(token: string) => void> = [];

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          pendingRequests.push((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(api(originalRequest));
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const newToken = await getOrStartRefresh();
        // setAccessToken is handled inside getOrStartRefresh

        pendingRequests.forEach((cb) => cb(newToken));
        pendingRequests = [];

        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      } catch {
        useAuthStore.getState().clearAuth();
        pendingRequests = [];
        return Promise.reject(error);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
