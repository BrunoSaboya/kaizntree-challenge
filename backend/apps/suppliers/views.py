from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from apps.inventory.views import OwnedModelMixin

from .models import Supplier
from .serializers import SupplierSerializer


class SupplierViewSet(OwnedModelMixin, viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["active"]
    search_fields = ["name", "email", "phone"]
    ordering_fields = ["name", "lead_time_days", "created_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Supplier.objects.filter(owner=self.request.user)
