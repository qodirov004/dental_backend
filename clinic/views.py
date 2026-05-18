from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from django.utils import timezone
from django.db import transaction
from .models import Customer, Pet, MedicalRecord, Visit, VaccineSchedule, FollowUp, VisitFeedback
from .serializers import (
    CustomerSerializer, PetSerializer, MedicalRecordSerializer, 
    VisitSerializer, VaccineScheduleSerializer, FollowUpSerializer, VisitFeedbackSerializer
)
from billing.models import Invoice

class CustomerViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = Customer.objects.all().order_by('-created_at')
    serializer_class = CustomerSerializer
    from django_filters.rest_framework import DjangoFilterBackend
    from rest_framework import filters
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'phone']
    filterset_fields = ['phone', 'telegram_id', 'referral_code']

    @action(detail=False, methods=['get'])
    def stats(self, request):
        today = timezone.now().date()
        total_customers = Customer.objects.count()
        total_pets = Pet.objects.count()
        todays_visits = Visit.objects.filter(arrived_at__date=today).count()
        
        total_debt = Invoice.objects.filter(status__in=['UNPAID', 'PARTIAL']).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        paid_on_debts = Invoice.objects.filter(status='PARTIAL').annotate(paid=Sum('payments__amount')).aggregate(Sum('paid'))['paid__sum'] or 0
        total_debt = float(total_debt) - float(paid_on_debts)

        # New metrics for alerts
        overdue_followups = FollowUp.objects.filter(scheduled_date__lt=today, is_completed=False).count()
        upcoming_vaccinations = VaccineSchedule.objects.filter(next_date__range=[today, today + timezone.timedelta(days=7)]).count()

        return Response({
            "total_customers": total_customers,
            "total_pets": total_pets,
            "todays_visits": todays_visits,
            "total_debt": total_debt,
            "overdue_followups": overdue_followups,
            "upcoming_vaccinations": upcoming_vaccinations,
        })
    
    @action(detail=True, methods=['post'])
    def send_telegram(self, request, pk=None):
        """Send a Telegram message to a customer"""
        from asgiref.sync import async_to_sync
        from .tasks import send_telegram_message
        
        customer = self.get_object()
        message = request.data.get('message', '')
        
        if not message:
            return Response(
                {"error": "Xabar matni kiritilishi shart"},
                status=400
            )
        
        if not customer.telegram_id:
            return Response(
                {"error": f"{customer.name} mijozning Telegram hisobi bog'lanmagan"},
                status=400
            )
        
        try:
            async_to_sync(send_telegram_message)(customer.telegram_id, message)
            return Response({
                "success": True,
                "message": f"{customer.name} ga xabar muvaffaqiyatli yuborildi"
            })
        except Exception as e:
            return Response(
                {"error": f"Xatolik yuz berdi: {str(e)}"},
                status=500
            )

class PetViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = Pet.objects.all()
    serializer_class = PetSerializer
    from django_filters.rest_framework import DjangoFilterBackend
    from rest_framework import filters
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'customer__name']
    filterset_fields = ['species', 'customer']

class MedicalRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = MedicalRecord.objects.all().order_by('-date')
    serializer_class = MedicalRecordSerializer
    filterset_fields = ['pet', 'date']

    @action(detail=True, methods=['get'])
    def download_analysis(self, request, pk=None):
        """Download Analysis Report PDF"""
        from utils.pdf_generator import generate_analysis_pdf, pdf_response
        record = self.get_object()
        
        if not record.analysis_data:
             return Response({"error": "Ushbu yozuvda tahlil natijalari yo'q"}, status=400)
             
        try:
            pdf_file = generate_analysis_pdf(record)
            return pdf_response(pdf_file, f'analysis_{record.id}.pdf', inline=True)
        except Exception as e:
            return Response({"error": f"PDF xatolik: {str(e)}"}, status=500)

    @action(detail=True, methods=['get'])
    def download_prescription(self, request, pk=None):
        """Download E-Prescription PDF"""
        from utils.pdf_generator import generate_prescription_pdf, pdf_response
        record = self.get_object()
        
        if not hasattr(record, 'prescription'):
             return Response({"error": "Ushbu yozuvga retsept biriktirilmagan"}, status=400)
             
        try:
            pdf_file = generate_prescription_pdf(record.prescription)
            return pdf_response(pdf_file, f'prescription_{record.id}.pdf', inline=True)
        except Exception as e:
            return Response({"error": f"PDF xatolik: {str(e)}"}, status=500)

class VisitViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = Visit.objects.all().order_by('-arrived_at')
    serializer_class = VisitSerializer
    filterset_fields = ['status', 'arrived_at']

    @action(detail=True, methods=['get'])
    def download_receipt(self, request, pk=None):
        """Generate and download PDF receipt"""
        from utils.pdf_generator import generate_visit_receipt_pdf, pdf_response
        
        visit = self.get_object()
        try:
            pdf_file = generate_visit_receipt_pdf(visit)
            return pdf_response(pdf_file, f'visit_{visit.id}_receipt.pdf', inline=True)
        except Exception as e:
            return Response(
                {"error": f"PDF yaratishda xatolik: {str(e)}"},
                status=500
            )

    @action(detail=True, methods=['get', 'post'])
    def download_ticket(self, request, pk=None):
        """Create a PrintJob for the thermal printer agent"""
        from .services.printer_service import QueuePrintService
        
        visit = self.get_object()
        try:
            service = QueuePrintService()
            service.print_ticket(visit)
            
            return Response({
                "status": "ok",
                "message": f"Navbat cheki #{visit.queue_number} printerga yuborildi"
            })
        except Exception as e:
            return Response(
                {"error": f"Chek yaratishda xatolik: {str(e)}"},
                status=500
            )

    @action(detail=True, methods=['get'])
    def print_html(self, request, pk=None):
        """Render thermal ticket as HTML for frontend printing"""
        from django.shortcuts import render
        visit = self.get_object()
        context = {
            'visit': visit,
            'q': visit.queue_number,
            'p': visit.pet.name,
            'd': visit.veterinarian.get_full_name() if visit.veterinarian else "Ixtiyoriy",
            't': timezone.now().strftime("%d.%m.%Y %H:%M")
        }
        return render(request, 'receipts/thermal_ticket.html', context)

    @action(detail=False, methods=['get'])
    def poll_print_jobs(self, request):
        """Agent uchun: yangi vazifa bormi?"""
        from .models import PrintJob
        job = PrintJob.objects.filter(status='pending').order_by('created_at').first()
        
        if not job:
            return Response({'job': None})
            
        job.status = 'processing'
        job.save()
        
        return Response({
            'job': {
                'id': job.id,
                'data': job.data
            }
        })

    @action(detail=True, methods=['post'])
    def acknowledge_print_job(self, request, pk=None):
        """Agent tasdiqlaydi: Chek chiqdi"""
        from .models import PrintJob
        try:
            job = PrintJob.objects.get(pk=pk)
            job.status = 'printed'
            job.save()
            return Response({'status': 'ok'})
        except PrintJob.DoesNotExist:
            return Response({'status': 'error', 'message': 'Job not found'}, status=404)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        visit = self.get_object()
        data = request.data
        
        treatment_notes = data.get('treatment_notes') or ''
        diagnosis = data.get('diagnosis') or ''
        additional_conditions = data.get('additional_conditions') or ''
        
        follow_up_date = data.get('follow_up_date')
        if not follow_up_date: # Handle empty string or None
            follow_up_date = None
        
        raw_amount = data.get('total_amount')
        try:
            total_amount = float(raw_amount) if raw_amount else 0
        except (ValueError, TypeError):
            total_amount = 0

        with transaction.atomic():
            # Assign veterinarian if not set
            if not visit.veterinarian:
                visit.veterinarian = request.user
            
            visit.status = 'COMPLETED'
            visit.total_amount = total_amount
            visit.save()

            MedicalRecord.objects.create(
                pet=visit.pet,
                veterinarian=visit.veterinarian,
                record_type='TREATMENT',
                description=treatment_notes,
                diagnosis=diagnosis,
                treatment=treatment_notes,
                additional_conditions=additional_conditions,
                date=timezone.now(),
                follow_up_date=follow_up_date
            )

            if follow_up_date:
                FollowUp.objects.create(
                    visit=visit,
                    scheduled_date=follow_up_date,
                    description=f"Follow up for: {visit.purpose}"
                )
            
            # Create Invoice for billing
            from billing.models import Invoice, Payment
            
            payment_method = data.get('payment_method', 'DEBT')
            invoice_status = 'UNPAID' if payment_method == 'DEBT' else 'PAID'
            
            invoice = Invoice.objects.create(
                customer=visit.pet.customer,
                total_amount=total_amount,
                status=invoice_status
            )
            
            # Create Payment record if not debt and amount > 0
            if invoice_status == 'PAID' and float(total_amount) > 0:
                method_map = {
                    'CASH': 'CASH',
                    'CARD': 'CARD',
                    'CLICK': 'CLICK'
                }
                Payment.objects.create(
                    invoice=invoice,
                    amount=total_amount,
                    method=method_map.get(payment_method, 'CASH'),
                    date=timezone.now()
                )

        # Send Telegram Notification with Feedback Request
        try:
            customer = visit.pet.customer
            if customer.telegram_id:
                import requests
                import os
                
                TOKEN = os.getenv("BOT_TOKEN", "8095862986:AAEQZInhYaJjDS17fQ7I0l8XxwoiM3Mtc-0")
                url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                
                # Feedback Buttons
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "⭐️ 1", "callback_data": f"rate_{visit.id}_1"},
                            {"text": "⭐️ 2", "callback_data": f"rate_{visit.id}_2"},
                            {"text": "⭐️ 3", "callback_data": f"rate_{visit.id}_3"},
                            {"text": "⭐️ 4", "callback_data": f"rate_{visit.id}_4"},
                            {"text": "⭐️ 5", "callback_data": f"rate_{visit.id}_5"},
                        ]
                    ]
                }
                
                msg_text = (
                    f"✅ <b>Qabul yakunlandi!</b>\n\n"
                    f"👤 <b>Bemor:</b> {visit.pet.name}\n"
                    f"📝 <b>Tashxis:</b> {diagnosis}\n"
                    f"💊 <b>Davolash:</b> {treatment_notes}\n"
                    f"💰 <b>Xizmat narxi:</b> {total_amount} UZS\n\n"
                    f"Iltimos, xizmat sifatini baholang:"
                )
                
                requests.post(url, json={
                    "chat_id": customer.telegram_id,
                    "text": msg_text,
                    "parse_mode": "HTML",
                    "reply_markup": keyboard
                })

                # Send PDF Receipt via Telegram
                try:
                    from utils.pdf_generator import generate_visit_receipt_pdf
                    pdf_io = generate_visit_receipt_pdf(visit)
                    doc_url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
                    files = {
                        'document': (f'visit_{visit.id}_receipt.pdf', pdf_io, 'application/pdf')
                    }
                    requests.post(doc_url, data={'chat_id': customer.telegram_id}, files=files)
                except Exception as pdf_err:
                    print(f"Error sending PDF to Telegram: {pdf_err}")
        except Exception as e:
            print(f"Telegram notification error: {e}")

        # Auto-call next waiting patient for this doctor
        next_called = None
        try:
            today = timezone.now().date()
            next_visit = None
            
            if visit.veterinarian:
                # First try to find next waiting patient assigned to same doctor
                next_visit = Visit.objects.filter(
                    status='WAITING',
                    veterinarian=visit.veterinarian,
                    arrived_at__date=today
                ).order_by('arrived_at').first()
            
            if not next_visit:
                # Fallback: find any unassigned waiting patient
                next_visit = Visit.objects.filter(
                    status='WAITING',
                    veterinarian__isnull=True,
                    arrived_at__date=today
                ).order_by('arrived_at').first()
                
                # Assign the completing doctor to this visit
                if next_visit and visit.veterinarian:
                    next_visit.veterinarian = visit.veterinarian
            
            if next_visit:
                next_visit.status = 'CALLED'
                next_visit.save()
                
                # Build response data for frontend voice announcement
                from .serializers import VisitSerializer
                next_called = VisitSerializer(next_visit).data
        except Exception as e:
            print(f"Auto-call next patient error: {e}")

        response_data = {"status": "Visit completed and record created"}
        if next_called:
            response_data["next_called"] = next_called
        
        return Response(response_data)

class FollowUpViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = FollowUp.objects.all()
    serializer_class = FollowUpSerializer
    filterset_fields = ['scheduled_date', 'is_completed']

class VisitFeedbackViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = VisitFeedback.objects.all()
    serializer_class = VisitFeedbackSerializer

class VaccineScheduleViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = VaccineSchedule.objects.all().order_by('next_date')
    serializer_class = VaccineScheduleSerializer
    filterset_fields = ['pet', 'next_date']

class KPIViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def doctor_stats(self, request):
        """Get stats for the currently logged in doctor (or specified via query param if admin)"""
        from .kpi_service import KPIService
        
        user = request.user
        target_id = request.query_params.get('doctor_id')
        
        # Only admin can view others stats, else view own
        if target_id and user.role == 'ADMIN':
            doctor_id = target_id
        else:
            doctor_id = user.id
            
        period = request.query_params.get('period', 'month')
        stats = KPIService.get_doctor_stats(doctor_id, period)
        return Response(stats)

class PetTimelineView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, timeline_uuid):
        try:
            pet = Pet.objects.get(timeline_uuid=timeline_uuid)
        except Pet.DoesNotExist:
            return Response({"error": "Pet not found"}, status=404)

        # Gather events
        events = []
        
        # Medical Records (Visits, Analysis, Vaccines)
        records = MedicalRecord.objects.filter(pet=pet).order_by('-date')
        for r in records:
            event_type = "VISIT"
            if r.analysis_data:
                event_type = "ANALYSIS"
            elif r.record_type == 'VACCINATION':
                event_type = "VACCINE"
            
            events.append({
                "id": f"record_{r.id}",
                "date": r.date,
                "type": event_type,
                "title": r.diagnosis if r.record_type == 'VACCINATION' else r.get_record_type_display(),
                # For vaccine, usually vaccine name is in diagnosis or description
                "description": r.description or r.diagnosis or "No details",
                "details": r.analysis_data,
                "doctor": r.veterinarian.full_name if r.veterinarian else "Unknown"
            })

        # Sort all by date desc
        events.sort(key=lambda x: str(x['date']), reverse=True)

        data = {
            "pet": {
                "name": pet.name,
                "species": pet.species,
                "breed": pet.breed,
                "age": pet.age,
                "owner": pet.customer.name
            },
            "events": events
        }
        return Response(data)

class DoctorKPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .kpi_service import KPIService
        # If user is admin, maybe show all or just their own (which is 0)
        # For demo, if admin, lets pick a random doctor or just return 0
        
        doctor_id = request.user.id
        period = request.query_params.get('period', 'month')
        
        stats = KPIService.get_doctor_stats(doctor_id, period)
        return Response(stats)


class TTSProxyView(APIView):
    """
    TTS endpoint using Microsoft Edge TTS for natural Uzbek voice.
    Uses uz-UZ-SardorNeural (male) or uz-UZ-MadinaNeural (female).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        import asyncio
        import io
        import edge_tts
        from django.http import HttpResponse

        text = request.query_params.get('text', '')
        voice = request.query_params.get('voice', 'uz-UZ-MadinaNeural')

        if not text:
            return Response({"error": "text parameter required"}, status=400)

        if len(text) > 500:
            return Response({"error": "text too long (max 500 chars)"}, status=400)

        try:
            async def generate_audio():
                communicate = edge_tts.Communicate(text, voice, rate="-25%", volume="+30%", pitch="+5Hz")
                audio_data = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data.write(chunk["data"])
                audio_data.seek(0)
                return audio_data

            # Run async edge-tts in sync context
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        audio_data = pool.submit(
                            lambda: asyncio.run(generate_audio())
                        ).result(timeout=15)
                else:
                    audio_data = loop.run_until_complete(generate_audio())
            except RuntimeError:
                audio_data = asyncio.run(generate_audio())

            response = HttpResponse(
                audio_data.read(),
                content_type="audio/mpeg"
            )
            response["Cache-Control"] = "public, max-age=86400"
            return response

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"TTS error: {str(e)}"},
                status=500
            )
