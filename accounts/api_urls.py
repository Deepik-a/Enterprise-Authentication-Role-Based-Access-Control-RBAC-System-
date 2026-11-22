from rest_framework.routers import DefaultRouter

from .views import UserViewSet

router = DefaultRouter()
router.register('users', UserViewSet)

# /me lives only at /api/auth/me/.
urlpatterns = router.urls
