from django.db.models import Sum, Count, Avg
from django.utils import timezone
from .models import Visit, VisitFeedback
from users.models import User, DoctorSalary
from datetime import timedelta
from decimal import Decimal

class KPIService:
    @staticmethod
    def get_doctor_stats(doctor_id, period='month'):
        """
        Calculate KPI for a specific doctor.
        Metrics:
        - Total Visits (Count)
        - Total Revenue (Sum of Visit.total_amount)
        - Average Rating (Avg of VisitFeedback.rating)
        - Total Earned (Based on doctor.salary_percentage)
        - Total Withdrawn (Sum of DoctorSalary)
        - Balance (Earned - Withdrawn)
        """
        today = timezone.now().date()
        
        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        else:
            start_date = today - timedelta(days=365) # Year default
            
        # Get visits within the selected period for activity stats (visits count, revenue chart, etc.)
        visits_qs = Visit.objects.filter(
            veterinarian_id=doctor_id,
            status='COMPLETED',
            arrived_at__date__gte=start_date
        )
        
        # Performance metrics for the selected period
        total_visits_period = visits_qs.count()
        total_revenue_period = visits_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
        
        # Calculate Rating for the selected period
        avg_rating = VisitFeedback.objects.filter(
            visit__veterinarian_id=doctor_id,
            created_at__date__gte=start_date
        ).aggregate(Avg('rating'))['rating__avg'] or 0

        # --- FINANCIAL TOTALS (LIFETIME BALANCE) ---
        # We calculate lifetime totals to ensure the balance is always accurate
        all_completed_visits = Visit.objects.filter(
            veterinarian_id=doctor_id,
            status='COMPLETED'
        )
        
        lifetime_revenue = all_completed_visits.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
        
        try:
            doctor = User.objects.get(id=doctor_id)
            percentage = doctor.salary_percentage or Decimal('0')
        except User.DoesNotExist:
            percentage = Decimal('0')
            
        total_earned_lifetime = (lifetime_revenue * percentage) / Decimal('100')
        
        total_withdrawn_lifetime = DoctorSalary.objects.filter(
            doctor_id=doctor_id
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        balance = total_earned_lifetime - total_withdrawn_lifetime

        # Calculate 'Urgency Score' for period
        critical_cases = visits_qs.filter(urgency_level__in=['HIGH', 'CRITICAL']).count()
        
        return {
            "period": period,
            "total_visits": total_visits_period,
            "total_revenue": float(total_revenue_period),
            "total_earned": float(total_earned_lifetime),
            "total_withdrawn": float(total_withdrawn_lifetime),
            "balance": float(balance),
            "avg_rating": round(avg_rating, 1),
            "critical_cases_handled": critical_cases
        }

    @staticmethod
    def get_clinic_overview():
        """Get leaderboard or overview logic"""
        today = timezone.now().date()
        start_date = today - timedelta(days=30)
        
        from django.db.models import Q
        top_doctors = User.objects.filter(role='DOCTOR').annotate(
            monthly_revenue=Sum('visits_conducted__total_amount', filter=Q(visits_conducted__arrived_at__date__gte=start_date, visits_conducted__status='COMPLETED'))
        ).order_by('-monthly_revenue')[:5]
        
        return top_doctors
