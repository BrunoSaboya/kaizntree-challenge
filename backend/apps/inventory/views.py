from datetime import date, timedelta

from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.financials.services import get_product_financials
from apps.users.permissions import IsOrgUser

from .models import Product, Stock, StockMovement
from .serializers import ProductSerializer, StockMovementSerializer, StockSerializer


class OrgScopedMixin:
    """Filters every queryset to the requesting user's organization."""
    permission_classes = [IsAuthenticated, IsOrgUser]

    def get_queryset(self):
        return super().get_queryset().filter(organization=self.request.user.organization)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class ProductViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["unit_type"]
    search_fields = ["name", "sku", "description"]
    ordering_fields = ["name", "sku", "created_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return (
            Product.objects.filter(organization=self.request.user.organization)
            .annotate(total_stock=Sum("stock_entries__quantity"))
        )

    @action(detail=True, methods=["get"])
    def stock(self, request, pk=None):
        product = self.get_object()
        entries = Stock.objects.filter(organization=request.user.organization, product=product)
        serializer = StockSerializer(entries, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def financials(self, request, pk=None):
        product = self.get_object()
        data = get_product_financials(request.user.organization, product_id=product.pk)
        return Response(data)

    @action(detail=True, methods=["get"])
    def movements(self, request, pk=None):
        product = self.get_object()
        qs = StockMovement.objects.filter(
            organization=request.user.organization, product=product
        ).select_related("stock")
        serializer = StockMovementSerializer(qs, many=True)
        return Response(serializer.data)


class StockViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    serializer_class = StockSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["product"]
    ordering_fields = ["created_at", "quantity", "expiry_date"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Stock.objects.filter(
            organization=self.request.user.organization
        ).select_related("product")

    @action(detail=True, methods=["get"])
    def movements(self, request, pk=None):
        stock = self.get_object()
        qs = StockMovement.objects.filter(organization=request.user.organization, stock=stock)
        serializer = StockMovementSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def expiring_soon(self, request):
        days = int(request.query_params.get("days", 30))
        cutoff = date.today() + timedelta(days=days)
        qs = self.get_queryset().filter(
            expiry_date__isnull=False,
            expiry_date__lte=cutoff,
            quantity__gt=0,
        ).order_by("expiry_date")
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
