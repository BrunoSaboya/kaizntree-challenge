import { lazy, Suspense, useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Center, Loader } from "@mantine/core";

import { authApi } from "@/api/auth";
import { getOrStartRefresh } from "@/api/authRefresh";
import { useAuthStore } from "@/store/authStore";
import { useRole } from "@/hooks/useRole";
import { AppShellLayout } from "@/components/layout/AppShellLayout";
import LoginPage from "@/pages/auth/LoginPage";
import DashboardPage from "@/pages/dashboard/DashboardPage";
import ProductListPage from "@/pages/products/ProductListPage";
import ProductDetailPage from "@/pages/products/ProductDetailPage";
import StockPage from "@/pages/stock/StockPage";
import PurchaseOrderListPage from "@/pages/purchase-orders/PurchaseOrderListPage";
import SalesOrderListPage from "@/pages/sales-orders/SalesOrderListPage";
import SuppliersPage from "@/pages/suppliers/SuppliersPage";
import ForecastingPage from "@/pages/forecasting/ForecastingPage";
import AIAssistPage from "@/pages/ai-assist/AIAssistPage";
import IntegrationsPage from "@/pages/integrations/IntegrationsPage";

const AdminUsersPage = lazy(() => import("@/pages/admin/AdminUsersPage"));
const AdminOrgsPage = lazy(() => import("@/pages/admin/AdminOrgsPage"));
const OrgMembersPage = lazy(() => import("@/pages/org/OrgMembersPage"));

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated ? <Navigate to="/" replace /> : <>{children}</>;
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { isAdmin } = useRole();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!isAdmin) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function BusinessRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { isAdmin } = useRole();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (isAdmin) return <Navigate to="/admin/users" replace />;
  return <>{children}</>;
}

function OwnerRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { isOwner } = useRole();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!isOwner) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  const { setAuth } = useAuthStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let savedToken = "";
    getOrStartRefresh()
      .then((token) => {
        savedToken = token;
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
          path="/"
          element={
            <ProtectedRoute>
              <AppShellLayout />
            </ProtectedRoute>
          }
        >
          {/* Business routes — owners and members only */}
          <Route
            index
            element={
              <BusinessRoute>
                <DashboardPage />
              </BusinessRoute>
            }
          />
          <Route
            path="products"
            element={
              <BusinessRoute>
                <ProductListPage />
              </BusinessRoute>
            }
          />
          <Route
            path="products/:id"
            element={
              <BusinessRoute>
                <ProductDetailPage />
              </BusinessRoute>
            }
          />
          <Route
            path="stock"
            element={
              <BusinessRoute>
                <StockPage />
              </BusinessRoute>
            }
          />
          <Route
            path="purchase-orders"
            element={
              <BusinessRoute>
                <PurchaseOrderListPage />
              </BusinessRoute>
            }
          />
          <Route
            path="sales-orders"
            element={
              <BusinessRoute>
                <SalesOrderListPage />
              </BusinessRoute>
            }
          />
          <Route
            path="suppliers"
            element={
              <BusinessRoute>
                <SuppliersPage />
              </BusinessRoute>
            }
          />
          <Route
            path="forecasting"
            element={
              <BusinessRoute>
                <ForecastingPage />
              </BusinessRoute>
            }
          />
          <Route
            path="ai-assist"
            element={
              <BusinessRoute>
                <AIAssistPage />
              </BusinessRoute>
            }
          />
          <Route
            path="integrations"
            element={
              <BusinessRoute>
                <IntegrationsPage />
              </BusinessRoute>
            }
          />

          {/* Owner routes */}
          <Route
            path="org/members"
            element={
              <OwnerRoute>
                <Suspense fallback={<Center style={{ height: "100%" }}><Loader /></Center>}>
                  <OrgMembersPage />
                </Suspense>
              </OwnerRoute>
            }
          />

          {/* Admin routes */}
          <Route
            path="admin/users"
            element={
              <AdminRoute>
                <Suspense fallback={<Center style={{ height: "100%" }}><Loader /></Center>}>
                  <AdminUsersPage />
                </Suspense>
              </AdminRoute>
            }
          />
          <Route
            path="admin/organizations"
            element={
              <AdminRoute>
                <Suspense fallback={<Center style={{ height: "100%" }}><Loader /></Center>}>
                  <AdminOrgsPage />
                </Suspense>
              </AdminRoute>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
