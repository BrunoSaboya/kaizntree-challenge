from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsOrgUser

from .services import get_all_product_financials, get_summary


class FinancialSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsOrgUser]

    def get(self, request):
        return Response(get_summary(request.user.organization))


class ProductFinancialsView(APIView):
    permission_classes = [IsAuthenticated, IsOrgUser]

    def get(self, request):
        return Response(get_all_product_financials(request.user.organization))
