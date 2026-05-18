from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User, SystemSettings, DoctorSalary
from .serializers import UserSerializer, SystemSettingsSerializer, DoctorSalarySerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated] # Allow all authenticated users to see staff, but restrict sensitive actions if needed

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'me']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

class DoctorSalaryViewSet(viewsets.ModelViewSet):
    queryset = DoctorSalary.objects.all().order_by('-date')
    serializer_class = DoctorSalarySerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()
        doctor_id = self.request.query_params.get('doctor_id')
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)
        return qs

class SystemSettingsViewSet(viewsets.ModelViewSet):
    queryset = SystemSettings.objects.all()
    serializer_class = SystemSettingsSerializer
    lookup_field = 'key'
    permission_classes = [permissions.AllowAny] # In prod, restrict this
