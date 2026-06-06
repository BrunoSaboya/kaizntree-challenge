from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsOrgUser

from .services import get_reorder_recommendations


class ReorderRecommendationsView(APIView):
    permission_classes = [IsAuthenticated, IsOrgUser]

    def get(self, request):
        data = get_reorder_recommendations(request.user.organization)
        return Response(data)
