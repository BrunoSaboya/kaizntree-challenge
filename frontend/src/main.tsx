import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "@mantine/charts/styles.css";
import "./index.css";

import { MantineProvider, createTheme, type MantineColorsTuple } from "@mantine/core";

const brandColors: MantineColorsTuple = [
  "#ecf8f0",
  "#c9ebd4",
  "#99d9b2",
  "#66c48e",
  "#38ad6d",
  "#1a9451",
  "#0a7a3c",
  "#045e2a",
  "#003d1a",
  "#002c10",
];

const theme = createTheme({
  primaryColor: "brand",
  colors: { brand: brandColors },
});
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={theme}>
        <Notifications position="top-right" />
        <App />
        <ReactQueryDevtools />
      </MantineProvider>
    </QueryClientProvider>
  </StrictMode>
);
