import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Center, Loader } from "@mantine/core";

import { authApi } from "@/api/auth";
import { getOrStartRefresh } from "@/api/authRefresh";
import { useAuthStore } from "@/store/authStore";
import { AppShellLayout } from "@/components/layout/AppShellLayout";
import LoginPage from "@/pages/auth/LoginPage";
import RegisterPage from "@/pages/auth/RegisterPage";
import DashboardPage from "@/pages/dashboard/DashboardPage";
import ProductListPage from "@/pages/products/ProductListPage";
import ProductDetailPage from "@/pages/products/ProductDetailPage";
import StockPage from "@/pages/stock/StockPage";
import PurchaseOrderListPage from "@/pages/purchase-orders/PurchaseOrderListPage";
import SalesOrderListPage from "@/pages/sales-orders/SalesOrderListPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated ? <Navigate to="/" replace /> : <>{children}</>;
}

export default function App() {
  const { setAuth } = useAuthStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let savedToken = "";
    getOrStartRefresh()
      .then((token) => {
        savedToken = token;
        // token is already in Zustand store via getOrStartRefresh
        return authApi.me();
      })
      .then((user) => {
        setAuth(savedToken, user);
      })
      .catch(() => {
        // Cookie absent or expired
      })
      .finally(() => setLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return (
      <Center style={{ height: "100vh" }}>
        <Loader size="lg" />
      </Center>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            <PublicRoute>
              <LoginPage />
            </PublicRoute>
          }
        />
        <Route
          path="/register"
          element={
            <PublicRoute>
              <RegisterPage />
            </PublicRoute>
          }
        />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AppShellLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="products" element={<ProductListPage />} />
          <Route path="products/:id" element={<ProductDetailPage />} />
          <Route path="stock" element={<StockPage />} />
          <Route path="purchase-orders" element={<PurchaseOrderListPage />} />
          <Route path="sales-orders" element={<SalesOrderListPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
