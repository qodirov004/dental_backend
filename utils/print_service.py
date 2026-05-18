import os
import sys

def print_pdf_windows(pdf_content, printer_name="GEZHI micro-printer"):
    """
    Fallback function for backward compatibility.
    """
    return print_ticket_direct(None, printer_name)

def print_ticket_direct(visit_data, printer_name="GEZHI micro-printer"):
    """
    Sends raw text commands to the thermal printer.
    This is much more reliable for POS/Micro printers.
    """
    try:
        import win32print
        
        # 1. Printer nomini aniqlash
        all_printers = [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
        target_printer = None
        for p in all_printers:
            if "gezhi" in p.lower() or "micro-printer" in p.lower():
                target_printer = p
                break
        
        if not target_printer:
            target_printer = win32print.GetDefaultPrinter()

        # 2. Matnli chek tayyorlash (ESC/POS formatida emas, oddiy RAW text)
        if visit_data:
            q_num = visit_data.get('queue_number', '???')
            doc = visit_data.get('doctor', 'Shifokor')
            patient = visit_data.get('patient', 'Bemor')
            date_str = visit_data.get('date', '')
        else:
            # Test ma'lumotlari
            q_num = "TEST"
            doc = "Doktor"
            patient = "Bemor"
            date_str = ""

        # Printer uchun oddiy matn (Windows Driver orqali)
        raw_data = f"\n" \
                   f"      DentalClinic Pro\n" \
                   f"------------------------------\n" \
                   f"        NAVBT CHEKI\n\n" \
                   f"           {q_num}\n\n" \
                   f"------------------------------\n" \
                   f"Shifokor: {doc}\n" \
                   f"Bemor:    {patient}\n" \
                   f"Sana:     {date_str}\n" \
                   f"------------------------------\n" \
                   f"        ArdentSoft\n" \
                   f"  Dasturchi: Q. Shahzodbek\n" \
                   f"    Tel: +998918603443\n\n\n\n\n\x1dva\x01" # Oxirida qog'ozni kesish buyrug'i (ba'zi printerlar uchun)

        # 3. Printerni ochish va RAW yozish
        hPrinter = win32print.OpenPrinter(target_printer)
        try:
            job = win32print.StartDocPrinter(hPrinter, 1, ("Navbat Cheki", None, "RAW"))
            win32print.StartPagePrinter(hPrinter)
            win32print.WritePrinter(hPrinter, raw_data.encode('utf-8'))
            win32print.EndPagePrinter(hPrinter)
            win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)
            
        print(f"SUCCESS: '{target_printer}' printeriga MATN yuborildi.")
        return True
    except Exception as e:
        print(f"PRINTER XATOLIGI: {e}")
        return False
