from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import GamePrize, UserWallet, GameSession

@admin.register(GamePrize)
class GamePrizeAdmin(admin.ModelAdmin):
    list_display = ('display_image', 'name', 'coefficient', 'win_probability', 'daily_limit', 'is_active')
    list_editable = ('coefficient', 'daily_limit', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)
    
    fieldsets = (
        ('Yutuq Ma\'lumotlari', {
            'fields': ('name', 'image', 'product')
        }),
        ('Sozlamalar', {
            'fields': ('coefficient', 'daily_limit', 'is_active'),
            'description': "Ehtimollik va cheklovlarni shu yerdan boshqaring."
        }),
    )

    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit:cover; border-radius:5px;" />', obj.image.url)
        return "-"
    display_image.short_description = "Rasm"

    def win_probability(self, obj):
        if not obj.is_active:
            return "0% (Inactive)"
        
        # Calculate total weight of ALL active prizes
        # Note: This runs a query per row. Optimize with get_queryset if list is large.
        # For < 50 items, this is negligible.
        total_weight = GamePrize.objects.filter(is_active=True).aggregate(Sum('coefficient'))['coefficient__sum'] or 0
        
        if total_weight == 0:
            return "0%"
            
        percentage = (obj.coefficient / total_weight) * 100
        return f"{percentage:.1f}%"
    win_probability.short_description = "Yutish Ehtimoli (Win Chance)"

@admin.register(UserWallet)
class UserWalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'spins', 'total_spins')
    search_fields = ('user__username', 'user__first_name')
    list_filter = ('spins',) # Check users with spins vs no spins? Needs custom filter or just simple field filter

@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'prize', 'coupon_code_display', 'is_win', 'is_used', 'created_at')
    list_filter = ('is_win', 'is_used', 'created_at')
    search_fields = ('user__username', 'coupon_code')
    readonly_fields = ('created_at', 'coupon_code')

    def coupon_code_display(self, obj):
        return obj.coupon_code or "-"
    coupon_code_display.short_description = "Kupon Kodi"

