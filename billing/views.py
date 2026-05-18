from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from .models import Invoice, Payment
from .serializers import InvoiceSerializer, PaymentSerializer

class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    filterset_fields = ['status', 'customer']
    
    @action(detail=False, methods=['get'])
    def debtors(self, request):
        """Get list of customers with outstanding debts"""
        from clinic.models import Customer
        from clinic.serializers import CustomerSerializer
        
        # Get all customers with unpaid or partial invoices
        debtors_ids = Invoice.objects.filter(
            status__in=['UNPAID', 'PARTIAL']
        ).values_list('customer_id', flat=True).distinct()
        
        debtors = Customer.objects.filter(id__in=debtors_ids)
        serializer = CustomerSerializer(debtors, many=True)
        
        # The debt_amount is already calculated in CustomerSerializer
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_payment(self, request, pk=None):
        """Add payment to an invoice"""
        from decimal import Decimal
        
        invoice = self.get_object()
        amount = request.data.get('amount')
        method = request.data.get('method', 'CASH')
        
        if not amount:
            return Response({"error": "To'lov summasi kiritilishi shart"}, status=400)
        
        try:
            amount = Decimal(str(amount))
        except:
            return Response({"error": "Noto'g'ri summa formati"}, status=400)
        
        if amount <= 0:
            return Response({"error": "Summa 0 dan katta bo'lishi kerak"}, status=400)
        
        # Create payment
        payment = Payment.objects.create(
            invoice=invoice,
            amount=amount,
            method=method
        )
        
        # Update invoice status
        total_paid = invoice.payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        remaining = invoice.total_amount - total_paid
        
        if remaining <= 0:
            invoice.status = 'PAID'
        elif total_paid > 0:
            invoice.status = 'PARTIAL'
        invoice.save()
        
        return Response({
            "success": True,
            "payment_id": payment.id,
            "invoice_status": invoice.status,
            "total_paid": float(total_paid),
            "remaining": float(remaining) if remaining > 0 else 0,
            "message": f"{float(amount):,.0f} so'm to'lov qabul qilindi"
        })

class PaymentViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filterset_fields = ['invoice', 'method', 'date']
