from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from clinic.models import Visit, Pet, Customer
from billing.models import Invoice

class AnalyticsSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)

        total_visits = Visit.objects.count()
        visits_last_30 = Visit.objects.filter(arrived_at__date__gte=thirty_days_ago).count()
        
        total_pets = Pet.objects.count()
        total_customers = Customer.objects.count()

        from shop.models import Order
        
        # Revenue from Clinic (Invoices)
        clinic_revenue = Invoice.objects.filter(status='PAID').aggregate(total=Sum('total_amount'))['total'] or 0
        clinic_revenue_30 = Invoice.objects.filter(
            status='PAID', 
            created_at__date__gte=thirty_days_ago
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        # Revenue from Shop (Orders)
        shop_revenue = Order.objects.filter(status='DELIVERED').aggregate(total=Sum('total_price'))['total'] or 0
        shop_revenue_30 = Order.objects.filter(
            status='DELIVERED',
            created_at__date__gte=thirty_days_ago
        ).aggregate(total=Sum('total_price'))['total'] or 0

        total_revenue = clinic_revenue + shop_revenue
        revenue_last_30 = clinic_revenue_30 + shop_revenue_30

        # Visit statuses
        status_counts = Visit.objects.values('status').annotate(count=Count('id'))

        return Response({
            "summary": {
                "total_visits": total_visits,
                "visits_last_30": visits_last_30,
                "total_pets": total_pets,
                "total_customers": total_customers,
                "total_revenue": total_revenue,
                "revenue_last_30": revenue_last_30,
            },
            "status_distribution": status_counts
        })

class RevenueChartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)

        revenue_data = Invoice.objects.filter(
            status='PAID',
            created_at__date__gte=start_date
        ).annotate(date=TruncDate('created_at')).values('date').annotate(
            amount=Sum('total_amount')
        ).order_by('date')

        visit_data = Visit.objects.filter(
            arrived_at__date__gte=start_date
        ).annotate(date=TruncDate('arrived_at')).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        return Response({
            "revenue": list(revenue_data),
            "visits": list(visit_data)
        })
