from django.urls import path

from .views import ReorderRecommendationsView

urlpatterns = [
    path("forecasting/reorder-recommendations/", ReorderRecommendationsView.as_view(), name="reorder-recommendations"),
]
