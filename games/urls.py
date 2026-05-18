from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GamePrizeViewSet, GameSessionViewSet, UserWalletView, SpinView, 
    MyPrizesView, ValidateCouponView, LeaderboardView,
    GameSettingsView, ReferralStatsViewSet, MyReferralsView
)

router = DefaultRouter()
router.register(r'prizes', GamePrizeViewSet, basename='prizes')
router.register(r'sessions', GameSessionViewSet)
router.register(r'referrals', ReferralStatsViewSet, basename='referrals')

urlpatterns = [
    path('', include(router.urls)),
    path('wallet/', UserWalletView.as_view(), name='wallet'),
    path('spin/', SpinView.as_view(), name='spin'),
    path('my-prizes/', MyPrizesView.as_view(), name='my-prizes'),
    path('validate-coupon/', ValidateCouponView.as_view(), name='validate-coupon'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
    path('settings/', GameSettingsView.as_view(), name='game-settings'),
    path('my-referrals/', MyReferralsView.as_view(), name='my-referrals'),
]
