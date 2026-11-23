from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .dashboard.views import DashboardStatsView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/dashboard/stats/', DashboardStatsView.as_view()),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('roles.urls')),
    path('api/', include('accounts.api_urls')),
    path('api/', include('audit.urls')),
    path('api/', include('shop.urls')),
]
