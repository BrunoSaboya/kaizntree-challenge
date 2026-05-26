from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.financials.services import get_product_financials

from .models import Product, Stock
from .serializers import ProductSerializer, StockSerializer


class OwnedModelMixin:
    """Filters every queryset to the requesting user."""

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ProductViewSet(OwnedModelMixin, viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["unit_type"]
    search_fields = ["name", "sku", "description"]
    ordering_fields = ["name", "sku", "created_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return (
            Product.objects.filter(owner=self.request.user)
            .annotate(total_stock=Sum("stock_entries__quantity"))
        )

    @action(detail=True, methods=["get"])
    def stock(self, request, pk=None):
        product = self.get_object()
        entries = Stock.objects.filter(owner=request.user, product=product)
        serializer = StockSerializer(entries, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def financials(self, request, pk=None):
        product = self.get_object()
        data = get_product_financials(request.user, product_id=product.pk)
        return Response(data)


class StockViewSet(OwnedModelMixin, viewsets.ModelViewSet):
    serializer_class = StockSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["product"]
    ordering_fields = ["created_at", "quantity"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Stock.objects.filter(owner=self.request.user).select_related("product")
