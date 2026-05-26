from django.urls import path

from .views import FinancialSummaryView, ProductFinancialsView

urlpatterns = [
    path("financials/summary/", FinancialSummaryView.as_view(), name="financials-summary"),
    path("financials/products/", ProductFinancialsView.as_view(), name="financials-products"),
]
