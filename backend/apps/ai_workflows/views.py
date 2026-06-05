from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .services import AIServiceUnavailableError, parse_purchase_order_document


class AIWorkflowThrottle(UserRateThrottle):
    scope = "ai_workflow"


class ParsePurchaseOrderView(APIView):
    throttle_classes = [AIWorkflowThrottle]

    def post(self, request):
        text = request.data.get("text", "").strip()
        if not text:
            return Response({"error": "text is required"}, status=400)

        try:
            result = parse_purchase_order_document(text, request.user)
        except AIServiceUnavailableError:
            return Response(
                {"error": "AI service is not available. Contact your administrator."},
                status=503,
            )

        return Response(result)
