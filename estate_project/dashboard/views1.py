from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services import get_dashboard_stats


@api_view(["GET"])
def dashboard_stats(request):
    return Response(get_dashboard_stats())