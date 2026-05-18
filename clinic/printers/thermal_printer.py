import win32print
import win32ui
import win32con

class WindowsThermalPrinter:
    """
    Windows GDI yordamida skrinshotdagi dizaynni 100% qayta yaratish.
    """
    
    def __init__(self, printer_name_keyword="GEZHI"):
        self.printer_name_keyword = printer_name_keyword
        self.printer_name = self._find_printer()

    def _find_printer(self):
        try:
            printers = [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
            for p in printers:
                if self.printer_name_keyword.lower() in p.lower() or "micro-printer" in p.lower():
                    return p
            return win32print.GetDefaultPrinter()
        except Exception as e:
            print(f"Printer topishda xatolik: {e}")
            return None

    def print_ticket_gdi(self, data):
        """
        Skrinshotdagi dizaynni chizib beradi.
        """
        if not self.printer_name:
            return False
            
        try:
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(self.printer_name)
            hdc.StartDoc("Dental Ticket")
            hdc.StartPage()
            
            # Shriftlar (Skrinshotga mos)
            f_header = win32ui.CreateFont({"name": "Courier New", "height": 60, "weight": 700})
            f_sub = win32ui.CreateFont({"name": "Courier New", "height": 40, "weight": 400})
            f_number = win32ui.CreateFont({"name": "Courier New", "height": 160, "weight": 800})
            f_info = win32ui.CreateFont({"name": "Courier New", "height": 45, "weight": 400})
            f_info_bold = win32ui.CreateFont({"name": "Courier New", "height": 45, "weight": 700})
            f_footer = win32ui.CreateFont({"name": "Courier New", "height": 35, "weight": 400})
            f_dev = win32ui.CreateFont({"name": "Courier New", "height": 30, "weight": 400})

            y = 30
            
            # 1. Header: DENTAL CLINIC PRO
            hdc.SelectObject(f_header)
            hdc.TextOut(40, y, "  DENTAL CLINIC PRO")
            y += 70
            
            # 2. Separator
            hdc.SelectObject(f_sub)
            hdc.TextOut(20, y, "--------------------------------")
            y += 40
            
            # 3. NAVBT CHEKI
            hdc.TextOut(80, y, "      NAVBT CHEKI")
            y += 60
            
            # 4. A-001 (Katta raqam)
            hdc.SelectObject(f_number)
            hdc.TextOut(60, y, data['q'])
            y += 180
            
            # 5. Ma'lumotlar
            hdc.SelectObject(f_info)
            hdc.TextOut(20, y, f"Bemor:    {data['p']}")
            y += 55
            hdc.TextOut(20, y, f"Shifokor: {data['d']}")
            y += 55
            hdc.TextOut(20, y, f"Sana:     {data['t']}")
            y += 70
            
            # 6. Separator
            hdc.SelectObject(f_sub)
            hdc.TextOut(20, y, "--------------------------------")
            y += 50
            
            # 7. ILTIMOS NAVBATINGIZNI KUTING
            hdc.SelectObject(f_footer)
            hdc.TextOut(40, y, "  ILTIMOS NAVBATINGIZNI KUTING")
            y += 60
            
            # 8. Dev Info
            hdc.SelectObject(f_dev)
            hdc.TextOut(80, y, "      ArdentSoft Systems")
            y += 35
            hdc.TextOut(80, y, "    Dasturchi: Q. Shahzodbek")
            y += 35
            hdc.TextOut(80, y, "      Tel: +998 91 860 34 43")
            
            y += 200 # Qog'ozni chiqarish uchun joy

            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()
            return True
        except Exception as e:
            print(f"GDI Print Error: {e}")
            return False
