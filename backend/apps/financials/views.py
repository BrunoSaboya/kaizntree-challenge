from rest_framework.response import Response
from rest_framework.views import APIView

from .services import get_all_product_financials, get_summary


class FinancialSummaryView(APIView):
    def get(self, request):
        return Response(get_summary(request.user))


class ProductFinancialsView(APIView):
    def get(self, request):
        return Response(get_all_product_financials(request.user))
