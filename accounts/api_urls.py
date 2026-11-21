from rest_framework.routers import DefaultRouter
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, MeView

router = DefaultRouter()
router.register('users', UserViewSet)

urlpatterns = [
    path('me/', MeView.as_view()),
] + router.urls
