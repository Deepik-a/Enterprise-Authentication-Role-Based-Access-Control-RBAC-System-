# backend/dashboard/views.py
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.db.models import Count
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from roles.models import Role, Module

User = get_user_model()

class DashboardStatsView(APIView):
    """Simple view that returns aggregate counts for the dashboard.
    No custom permission check – any authenticated user can see the numbers.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = {
            "users": User.objects.count(),
            "roles": Role.objects.count(),
            "modules": Module.objects.count(),
        }
        return JsonResponse(data)
