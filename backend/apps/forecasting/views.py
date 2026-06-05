from rest_framework.response import Response
from rest_framework.views import APIView

from .services import get_reorder_recommendations


class ReorderRecommendationsView(APIView):
    def get(self, request):
        data = get_reorder_recommendations(request.user)
        return Response(data)
