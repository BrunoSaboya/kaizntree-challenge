from rest_framework.routers import DefaultRouter

from .views import PurchaseOrderViewSet, SalesOrderViewSet

router = DefaultRouter()
router.register("purchase-orders", PurchaseOrderViewSet, basename="purchase-order")
router.register("sales-orders", SalesOrderViewSet, basename="sales-order")

urlpatterns = router.urls
