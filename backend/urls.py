from django.contrib import admin
from django.urls import path, include

from .dashboard.views import DashboardStatsView

urlpatterns = [
    path('api/dashboard/stats/', DashboardStatsView.as_view()),
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('roles.urls')),
    path('api/', include('accounts.api_urls')),
    path('api/', include('audit.urls')),
]
