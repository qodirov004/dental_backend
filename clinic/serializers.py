from rest_framework import serializers
from .models import Customer, Pet, MedicalRecord, Visit, VaccineSchedule, FollowUp, VisitFeedback
from users.serializers import UserSerializer

class VaccineScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = VaccineSchedule
        fields = '__all__'

class PetSerializer(serializers.ModelSerializer):
    vaccines = VaccineScheduleSerializer(many=True, read_only=True)
    age = serializers.ReadOnlyField()
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = Pet
        fields = '__all__'
        extra_kwargs = {'customer': {'required': False}}

class CustomerSerializer(serializers.ModelSerializer):
    pets = PetSerializer(many=True, required=False)
    has_telegram = serializers.SerializerMethodField()
    debt_amount = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = '__all__'
    
    def get_has_telegram(self, obj):
        return bool(obj.telegram_id)
    
    def get_debt_amount(self, obj):
        from billing.models import Invoice
        from django.db.models import Sum, F
        
        # Calculate total unpaid and partial invoices
        unpaid_invoices = Invoice.objects.filter(
            customer=obj,
            status__in=['UNPAID', 'PARTIAL']
        )
        
        total_debt = 0
        for invoice in unpaid_invoices:
            paid = invoice.payments.aggregate(Sum('amount'))['amount__sum'] or 0
            total_debt += float(invoice.total_amount) - float(paid)
        
        return round(total_debt, 2)

    referred_by_name = serializers.CharField(source='referred_by.name', read_only=True)
    referral_count = serializers.SerializerMethodField()

    def get_referral_count(self, obj):
        return obj.referrals.count()

    def create(self, validated_data):
        pets_data = validated_data.pop('pets', [])
        customer = Customer.objects.create(**validated_data)
        for pet_data in pets_data:
            Pet.objects.create(customer=customer, **pet_data)
        return customer

class MedicalRecordSerializer(serializers.ModelSerializer):
    vet_name = serializers.CharField(source='veterinarian.username', read_only=True)

    class Meta:
        model = MedicalRecord
        fields = '__all__'

class FollowUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUp
        fields = '__all__'

class VisitFeedbackSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='visit.pet.customer.name', read_only=True)
    pet_name = serializers.CharField(source='visit.pet.name', read_only=True)
    visit_date = serializers.DateTimeField(source='visit.arrived_at', read_only=True)

    class Meta:
        model = VisitFeedback
        fields = '__all__'

class VisitSerializer(serializers.ModelSerializer):
    pet_name = serializers.CharField(source='pet.name', read_only=True)
    customer_name = serializers.CharField(source='pet.customer.name', read_only=True)
    veterinarian_name = serializers.CharField(source='veterinarian.username', read_only=True)
    veterinarian_first_name = serializers.CharField(source='veterinarian.first_name', read_only=True)
    veterinarian_last_name = serializers.CharField(source='veterinarian.last_name', read_only=True)
    veterinarian_room = serializers.CharField(source='veterinarian.room_number', read_only=True)
    queue_number_str = serializers.SerializerMethodField()
    follow_up = FollowUpSerializer(read_only=True)
    feedback = VisitFeedbackSerializer(read_only=True)

    class Meta:
        model = Visit
        fields = '__all__'

    def get_queue_number_str(self, obj):
        return obj.queue_number or "---"
