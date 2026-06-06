from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.inventory.views import OrgScopedMixin

from .models import PurchaseOrder, SalesOrder
from .serializers import ConfirmPurchaseOrderSerializer, PurchaseOrderSerializer, SalesOrderSerializer
from .services import (
    cancel_purchase_order,
    cancel_sales_order,
    confirm_purchase_order,
    confirm_sales_order,
)


class PurchaseOrderViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    serializer_class = PurchaseOrderSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["product", "status"]
    ordering_fields = ["order_date", "created_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return (
            PurchaseOrder.objects.filter(organization=self.request.user.organization)
            .select_related("product", "stock")
        )

    def destroy(self, request, *args, **kwargs):
        from rest_framework.exceptions import ValidationError
        po = self.get_object()
        if po.status != "draft":
            raise ValidationError("Only draft orders can be deleted.")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        po = self.get_object()
        serializer = ConfirmPurchaseOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_po = confirm_purchase_order(
            po,
            serializer.validated_data["stock_identifier"],
            expiry_date=serializer.validated_data.get("expiry_date"),
            stock_notes=serializer.validated_data.get("stock_notes", ""),
        )
        return Response(PurchaseOrderSerializer(updated_po, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        po = self.get_object()
        updated_po = cancel_purchase_order(po)
        return Response(PurchaseOrderSerializer(updated_po, context={"request": request}).data)


class SalesOrderViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    serializer_class = SalesOrderSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["product", "status"]
    ordering_fields = ["order_date", "created_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return (
            SalesOrder.objects.filter(organization=self.request.user.organization)
            .select_related("product", "stock")
        )

    def destroy(self, request, *args, **kwargs):
        from rest_framework.exceptions import ValidationError
        so = self.get_object()
        if so.status != "draft":
            raise ValidationError("Only draft orders can be deleted.")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        so = self.get_object()
        updated_so = confirm_sales_order(so)
        return Response(SalesOrderSerializer(updated_so, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        so = self.get_object()
        updated_so = cancel_sales_order(so)
        return Response(SalesOrderSerializer(updated_so, context={"request": request}).data)
