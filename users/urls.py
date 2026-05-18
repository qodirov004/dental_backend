from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, SystemSettingsViewSet, DoctorSalaryViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'settings', SystemSettingsViewSet)
router.register(r'salaries', DoctorSalaryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
