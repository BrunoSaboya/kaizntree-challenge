import api from "./client";
import type { ReorderRecommendation } from "@/types/forecasting";

export const forecastingApi = {
  reorderRecommendations: () =>
    api.get<ReorderRecommendation[]>("/forecasting/reorder-recommendations/").then((r) => r.data),
};
