from django.urls import path

from .views import ParsePurchaseOrderView

urlpatterns = [
    path("ai/parse-purchase-order/", ParsePurchaseOrderView.as_view(), name="parse-purchase-order"),
]
