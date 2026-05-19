from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, PetViewSet, MedicalRecordViewSet, VisitViewSet, VaccineScheduleViewSet, VisitFeedbackViewSet, PetTimelineView, DoctorKPIView, TTSProxyView, QueueEventsView

from .analytics_views import AnalyticsSummaryView, RevenueChartView

router = DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'pets', PetViewSet)
router.register(r'medical-records', MedicalRecordViewSet)
router.register(r'visits', VisitViewSet)
router.register(r'vaccines', VaccineScheduleViewSet)
router.register(r'feedback', VisitFeedbackViewSet)

from .staff_views import StaffPerformanceView

urlpatterns = [
    path('visits/events/', QueueEventsView.as_view(), name='queue-events'),
    path('', include(router.urls)),
    path('analytics/summary/', AnalyticsSummaryView.as_view(), name='analytics-summary'),
    path('analytics/charts/', RevenueChartView.as_view(), name='analytics-charts'),
    path('analytics/staff/', StaffPerformanceView.as_view(), name='staff-performance'),
    path('kpi/doctor_stats/', DoctorKPIView.as_view(), name='doctor-kpi'),
    path('pets/timeline/<uuid:timeline_uuid>/', PetTimelineView.as_view(), name='pet-timeline'),
    path('tts/', TTSProxyView.as_view(), name='tts-proxy'),
]
