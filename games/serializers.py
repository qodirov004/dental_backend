from rest_framework import serializers
from .models import GamePrize, UserWallet, GameSession, GameSettings
from clinic.models import Customer
from django.contrib.auth import get_user_model

User = get_user_model()

class GamePrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GamePrize
        fields = '__all__'

class UserWalletSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = UserWallet
        fields = ['username', 'balance', 'spins', 'total_spins']

class GameSessionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True, allow_null=True)
    prize_name = serializers.CharField(source='prize.name', read_only=True)
    prize_image = serializers.ImageField(source='prize.image', read_only=True)

    class Meta:
        model = GameSession
        fields = ['id', 'user_name', 'customer_name', 'prize_name', 'prize_image', 'is_win', 'created_at', 'coupon_code', 'is_used', 'used_at']

class LeaderboardSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = UserWallet
        fields = ['username', 'total_spins', 'balance']

class GameSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameSettings
        fields = '__all__'

class ReferralStatsSerializer(serializers.ModelSerializer):
    # Serializer for Customer to show referral info
    referrals_count = serializers.IntegerField(source='referrals.count', read_only=True)
    referrals_list = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['id', 'name', 'phone', 'spins', 'referral_code', 'referrals_count', 'referrals_list']

    def get_referrals_list(self, obj):
        # Return list of people referred by this customer
        # Limit to last 20 for performance in table
        refs = obj.referrals.all().order_by('-created_at')[:20]
        return [
            {
                "name": r.name,
                "phone": r.phone,
                "created_at": r.created_at
            }
            for r in refs
        ]
