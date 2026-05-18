from rest_framework import viewsets, views, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.db.models import F, Q, Count
from .models import GamePrize, UserWallet, GameSession, GameSettings
from clinic.models import Customer
from django.utils import timezone

from .serializers import (
    GamePrizeSerializer, UserWalletSerializer, GameSessionSerializer, 
    LeaderboardSerializer, GameSettingsSerializer, ReferralStatsSerializer
)
import random
from django.contrib.auth import get_user_model

User = get_user_model()

class GamePrizeViewSet(viewsets.ModelViewSet):
    # queryset logic handled in get_queryset
    serializer_class = GamePrizeSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()] 

    def get_queryset(self):
        if self.request.user.is_staff:
            return GamePrize.objects.all().order_by('-is_active', '-coefficient')
        return GamePrize.objects.filter(is_active=True).order_by('coefficient')

class GameSessionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GameSession.objects.all().order_by('-created_at')
    serializer_class = GameSessionSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['user', 'customer', 'prize', 'is_win']

class UserWalletView(views.APIView):
    permission_classes = [permissions.AllowAny] # DISABLED AUTH FOR DEMO

    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            user = User.objects.first()
            
        wallet, created = UserWallet.objects.get_or_create(user=user)
        
        # Sync with Customer spins
        try:
            # Fallback logic to find customer (same as MyReferralsView)
            customer = Customer.objects.filter(name=user.first_name).first()
            if not customer:
                 customer = Customer.objects.first()
            
            if customer:
                wallet.spins = customer.spins
                wallet.save()
        except Exception as e:
            print(f"Error syncing spins: {e}")

        serializer = UserWalletSerializer(wallet)
        return Response(serializer.data)

class SpinView(views.APIView):
    permission_classes = [permissions.AllowAny] # DISABLED AUTH FOR DEMO

    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            user = User.objects.first()

        wallet, _ = UserWallet.objects.get_or_create(user=user)
        
        # Find Customer to verify/deduct spins
        customer = None
        try:
            customer = Customer.objects.filter(name=user.first_name).first()
            if not customer:
                 customer = Customer.objects.first()
        except:
            pass

        # Check balance (Prioritize Customer record if exists)
        current_spins = customer.spins if customer else wallet.spins
        
        if current_spins <= 0:
            # Check price if we enable paid spins later, but for now strict 0 logic
            if wallet.balance < 500: # Assuming 500 coin fallback cost
                 return Response({"error": "Spinlar yetarli emas!"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                 # Paid spin
                 wallet.balance -= 500
                 wallet.save()
        else:
             # Free spin
             if customer:
                 customer.spins = F('spins') - 1
                 customer.save()
                 customer.refresh_from_db()
                 wallet.spins = customer.spins
                 wallet.save()
             else:
                 wallet.spins = F('spins') - 1
                 wallet.save()
                 wallet.refresh_from_db()

        # Update stats
        wallet.total_spins = F('total_spins') + 1
        wallet.save()

        # Select Prize
        prizes = GamePrize.objects.filter(is_active=True).order_by('coefficient')
        if not prizes.exists():
            return Response({"error": "Sovg'alar topilmadi"}, status=500)
            
        # Weighted random selection
        # Simple algorithm: expand list based on coefficient (or inverse of rarety)
        # Here we use coefficient as "weight" directly? 
        # Low coefficient = Rare? Or High = Rare?
        # Usually coefficient implies multiplier. Let's assume Higher = More likely for now OR check model def.
        # Model says "Probability weight".
        
        total_weight = sum(p.coefficient for p in prizes)
        pick = random.uniform(0, total_weight)
        current = 0
        selected_prize = prizes.first()
        
        for p in prizes:
            current += p.coefficient
            if pick <= current:
                selected_prize = p
                break
        
        # Record Session
        session = GameSession.objects.create(
            user=user,
            customer=customer, # Link to customer
            prize=selected_prize,
            is_win=True # For now all are wins, even "Try Again" is a result
        )

        return Response({
            "prize": GamePrizeSerializer(selected_prize).data,
            "wallet": UserWalletSerializer(wallet).data,
            "coupon": session.coupon_code
        })

        # Deduct cost (DISABLED FOR DEMO)
        with transaction.atomic():
            pass
            
            # Weighted Random Selection
            prizes = GamePrize.objects.filter(is_active=True)
            if not prizes.exists():
                return Response({"error": "No prizes available"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            total_weight = sum([p.coefficient for p in prizes])
            random_val = random.uniform(0, total_weight)
            
            current_weight = 0
            selected_prize = None
            for prize in prizes:
                current_weight += prize.coefficient
                if random_val <= current_weight:
                    selected_prize = prize
                    break
            
            # Record Session
            session = GameSession.objects.create(
                user=user,
                prize=selected_prize,
                is_win=True
            )
            
            # Update Total Spins for Leaderboard
            wallet.total_spins = F('total_spins') + 1
            wallet.save()
            
            return Response({
                "prize": GamePrizeSerializer(selected_prize).data,
                "wallet": UserWalletSerializer(wallet).data,
                "coupon_code": session.coupon_code
            })

class MyPrizesView(views.APIView):
    permission_classes = [permissions.AllowAny] 

    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            user = User.objects.first()
            
        sessions = GameSession.objects.filter(user=user, is_win=True).exclude(
            Q(prize__name__icontains="qayta") | 
            Q(prize__name__icontains="try again")
        ).order_by('-created_at')
        serializer = GameSessionSerializer(sessions, many=True)
        return Response(serializer.data)

class ValidateCouponView(views.APIView):
    permission_classes = [permissions.AllowAny] 

    def post(self, request):
        code = request.data.get('code')
        if not code:
            return Response({"error": "Code is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            session = GameSession.objects.get(coupon_code=code)
        except GameSession.DoesNotExist:
             return Response({"error": "Invalid coupon code"}, status=status.HTTP_404_NOT_FOUND)
             
        if session.is_used:
            return Response({"error": "Coupon already used"}, status=status.HTTP_400_BAD_REQUEST)
            
        prize = session.prize
        return Response({
            "valid": True,
            "prize": {
                "name": prize.name,
                "description": prize.description,
                "discount_percent": 0, 
                "raw_data": GamePrizeSerializer(prize).data
            },
            "session_id": session.id
        })

class LeaderboardView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        top_spinners = UserWallet.objects.order_by('-total_spins')[:10]
        return Response({
            "top_spinners": LeaderboardSerializer(top_spinners, many=True).data,
            "top_referrers": [] 
        })

# --- Admin Panel Views ---

class GameSettingsView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        settings = GameSettings.get_settings()
        serializer = GameSettingsSerializer(settings)
        return Response(serializer.data)

    def post(self, request):
        settings = GameSettings.get_settings()
        serializer = GameSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ReferralStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View to list customers with their referral stats for the Admin Panel.
    Includes filtering/searching by phone.
    """
    permission_classes = [permissions.IsAdminUser]
    serializer_class = ReferralStatsSerializer
    
    def get_queryset(self):
        # We want to see people who have referred others, or maybe everyone?
        # Let's show everyone who has at least 1 referral, OR filter by search.
        queryset = Customer.objects.annotate(referral_count=Count('referrals')).order_by('-referral_count', '-created_at')
        
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(phone__icontains=search))
            
        return queryset
class MyReferralsView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            user = User.objects.first()
            
        try:
            # Try to find linked customer
            # For demo, assuming user -> customer link via phone or just finding customer that matches user (conceptually)
            # In real bot webapp, auth is via Query Param or Headers. 
            # For now, let's look for a Customer with same phone/name or just return empty/mock if no link.
            
            # IMPROVEMENT: Use the Telegram ID if passed in headers, or default customer
            customer = Customer.objects.filter(name=user.first_name).first() # Fallback
            if not customer:
                 # Demo: Just pick the first customer with referrals for visualization if we can't identify 'me'
                 # Or actually, let's just use the first customer in DB as 'me' for the demo phone layout
                 customer = Customer.objects.first()

            if not customer:
                return Response([])

            referrals = Customer.objects.filter(referred_by=customer).order_by('-created_at')
            data = []
            for ref in referrals:
                data.append({
                    "id": ref.id,
                    "name": ref.name,
                    "joined": ref.created_at.strftime("%d.%m.%Y"), # Simple date
                    "reward": 1 # Fixed 1 spin
                })
            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
