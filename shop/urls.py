from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import OrderViewSet, ProductViewSet, ReportExportView, ReportSummaryView

router = DefaultRouter()
router.register('products', ProductViewSet)
router.register('orders', OrderViewSet)

urlpatterns = [
    path('reports/summary/', ReportSummaryView.as_view()),
    path('reports/export/', ReportExportView.as_view()),
] + router.urls
