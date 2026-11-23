

from rest_framework.routers import DefaultRouter


from .views import RoleViewSet, PermissionViewSet, ModuleViewSet



router = DefaultRouter()



router.register('roles', RoleViewSet)



router.register('permissions', PermissionViewSet)



router.register('modules', ModuleViewSet)


urlpatterns = router.urls
