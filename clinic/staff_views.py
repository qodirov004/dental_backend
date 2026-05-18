from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .kpi_service import KPIService

User = get_user_model()

class StaffPerformanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get all users with roles that conduct visits (DOCTOR, ASSISTANT)
        staff = User.objects.filter(
            role__in=['ADMIN', 'DOCTOR', 'ASSISTANT']
        ).distinct()

        period = request.query_params.get('period', 'month')
        performance_data = []
        
        for member in staff:
            stats = KPIService.get_doctor_stats(member.id, period)
            
            role_labels = {
                "ADMIN": "Admin",
                "DOCTOR": "Shifokor",
                "RECEPTIONIST": "Registrator",
                "ASSISTANT": "Yordamchi"
            }

            performance_data.append({
                "id": member.id,
                "name": member.get_full_name() or member.username,
                "role": role_labels.get(member.role, member.role),
                "salary_percentage": float(member.salary_percentage),
                **stats
            })

        return Response(performance_data)
