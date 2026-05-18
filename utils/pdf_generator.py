import os
from django.template.loader import render_to_string
from django.http import HttpResponse
from io import BytesIO
from xhtml2pdf import pisa
from django.conf import settings

def generate_visit_receipt_pdf(visit):
    """Generate PDF receipt for clinic visit using xhtml2pdf (Windows friendly)"""
    
    from clinic.models import MedicalRecord
    latest_record = MedicalRecord.objects.filter(pet=visit.pet).order_by('-date').first()
    
    # Generate QR Code for Pet Timeline
    import qrcode
    import base64
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    timeline_url = f"https://vettakhirov.uz/timeline/{visit.pet.timeline_uuid}" 
    qr.add_data(timeline_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()

    # Prepare context data
    context = {
        'visit': visit,
        'customer': visit.pet.customer,
        'pet': visit.pet,
        'diagnosis': latest_record.diagnosis if latest_record else '',
        'treatment': latest_record.treatment if latest_record else '',
        'additional_conditions': latest_record.additional_conditions if latest_record else '',
        'total_amount': visit.total_amount if hasattr(visit, 'total_amount') else 0,
        'qr_code': qr_code_base64,
    }
    
    # HTML template
    html_string = render_to_string('receipts/visit_receipt.html', context)
    
    # Generate PDF
    result = BytesIO()
    pisa_status = pisa.CreatePDF(html_string, dest=result)
    
    if pisa_status.err:
        raise Exception("PDF generation failed via xhtml2pdf")
        
    result.seek(0)
    return result

def generate_order_receipt_pdf(order):
    """Generate PDF receipt for shop order using xhtml2pdf"""
    
    items_total = sum(item.price * item.quantity for item in order.items.all())
    subtotal = items_total + order.delivery_fee
    discount = 0
    if subtotal > order.total_price:
        discount = subtotal - order.total_price
    
    context = {
        'order': order,
        'items': order.items.all(),
        'items_total': items_total,
        'delivery_fee': order.delivery_fee,
        'discount': discount,
        'grand_total': order.total_price,
    }

    # Generate Barcode (optional, xhtml2pdf handles images)
    try:
        import barcode
        from barcode.writer import ImageWriter
        import base64
        
        code128 = barcode.get_barcode_class('code128')
        rv = BytesIO()
        code = code128(str(order.id), writer=ImageWriter())
        code.write(rv)
        barcode_base64 = base64.b64encode(rv.getvalue()).decode('utf-8')
        context['barcode_base64'] = barcode_base64
    except:
        context['barcode_base64'] = None
    
    html_string = render_to_string('receipts/order_receipt.html', context)
    result = BytesIO()
    pisa.CreatePDF(html_string, dest=result)
    result.seek(0)
    return result

def pdf_response(pdf_file, filename, inline=False):
    """Create HTTP response for PDF preview or download"""
    response = HttpResponse(pdf_file, content_type='application/pdf')
    disposition = 'inline' if inline else 'attachment'
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response

def generate_analysis_pdf(record):
    """Generate PDF for Medical Analysis Results using xhtml2pdf"""
    results = []
    data = record.analysis_data or {}
    
    for key, value in data.items():
        results.append({
            "label": key.upper(),
            "value": value,
            "unit": "unit",
            "min": "?",
            "max": "?",
            "status": "NORMAL"
        })
        
    context = {
        'pet': record.pet,
        'date': record.date,
        'doctor_name': record.veterinarian.full_name if record.veterinarian else "DentalClinic Pro",
        'results': results
    }
    
    html_string = render_to_string('reports/analysis_report.html', context)
    result = BytesIO()
    pisa.CreatePDF(html_string, dest=result)
    result.seek(0)
    return result

def generate_prescription_pdf(prescription):
    """Generate PDF for E-Prescription using xhtml2pdf"""
    items = prescription.items.all()
    context = {
        'pet': prescription.medical_record.pet,
        'date': prescription.created_at,
        'doctor_name': prescription.medical_record.veterinarian.full_name if prescription.medical_record.veterinarian else "DentalClinic Pro",
        'items': items,
        'notes': prescription.notes
    }
    
    html_string = render_to_string('reports/prescription.html', context)
    result = BytesIO()
    pisa.CreatePDF(html_string, dest=result)
    result.seek(0)
    return result

def generate_queue_ticket_pdf(visit):
    """Generate a small ticket PDF for the queue system"""
    context = {
        'visit': visit,
    }
    html_string = render_to_string('receipts/queue_ticket.html', context)
    result = BytesIO()
    pisa.CreatePDF(html_string, dest=result)
    result.seek(0)
    return result
