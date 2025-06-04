import json
from datetime import datetime
from django.conf import settings
import socket
import struct

class XPrinterManager:
    """Xprinter bilan ishlash uchun klass"""
    
    def __init__(self, printer_ip='192.168.1.100', printer_port=9100):
        self.printer_ip = printer_ip
        self.printer_port = printer_port
        
    def format_receipt(self, receipt_data):
        """Chekni ESC/POS formatida tayyorlash"""
        # ESC/POS komandalar
        ESC = b'\x1B'
        INIT = ESC + b'@'  # Printerni boshlang'ich holatga keltirish
        CENTER = ESC + b'a\x01'  # Markazga joylashtirish
        LEFT = ESC + b'a\x00'  # Chapga joylashtirish
        BOLD_ON = ESC + b'E\x01'  # Qalin matn
        BOLD_OFF = ESC + b'E\x00'  # Oddiy matn
        DOUBLE_WIDTH = ESC + b'!\x20'  # Ikki marta keng
        NORMAL_WIDTH = ESC + b'!\x00'  # Oddiy kenglik
        CUT = ESC + b'd\x03'  # Qog'ozni kesish
        FEED = b'\n'
        
        receipt = INIT
        
        # Logo va sarlavha
        receipt += CENTER
        receipt += BOLD_ON + DOUBLE_WIDTH
        receipt += "SAVDO CHEKI".encode('utf-8') + FEED
        receipt += NORMAL_WIDTH + BOLD_OFF
        receipt += "=" * 32 + FEED
        
        # Chek ma'lumotlari
        receipt += LEFT
        receipt += f"Chek №: {receipt_data['receipt_id']}".encode('utf-8') + FEED
        receipt += f"Sana: {receipt_data['date']}".encode('utf-8') + FEED
        receipt += f"Vaqt: {receipt_data['time']}".encode('utf-8') + FEED
        receipt += f"Kassir: {receipt_data['cashier']}".encode('utf-8') + FEED
        receipt += "=" * 32 + FEED + FEED
        
        # Mahsulotlar jadvali
        receipt += "Mahsulot           Soni  Narx   Jami".encode('utf-8') + FEED
        receipt += "-" * 32 + FEED
        
        for item in receipt_data['items']:
            # Mahsulot nomini qisqartirish (15 belgi)
            name = item['name'][:15].ljust(15)
            qty = f"{item['quantity']:.0f}".rjust(4)
            price = f"{item['price']:.0f}".rjust(6)
            total = f"{item['total']:.0f}".rjust(7)
            
            line = f"{name} {qty} {price} {total}".encode('utf-8') + FEED
            receipt += line
        
        receipt += "-" * 32 + FEED
        
        # Jami summa
        receipt += BOLD_ON
        receipt += f"JAMI: {receipt_data['total']:.0f} so'm".encode('utf-8') + FEED
        receipt += BOLD_OFF + FEED
        
        # Pastki qism
        receipt += CENTER
        receipt += "Xaridingiz uchun rahmat!".encode('utf-8') + FEED
        receipt += "Yana tashrif buyuring!".encode('utf-8') + FEED + FEED + FEED
        
        # Qog'ozni kesish
        receipt += CUT
        
        return receipt
    
    def print_receipt(self, receipt_data):
        """Chekni printerga yuborish"""
        try:
            # Chekni formatga keltirish
            formatted_receipt = self.format_receipt(receipt_data)
            
            # Printerga ulanish
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5 soniya timeout
            sock.connect((self.printer_ip, self.printer_port))
            
            # Ma'lumotlarni yuborish
            sock.send(formatted_receipt)
            sock.close()
            
            return {'success': True, 'message': 'Chek muvaffaqiyatli chop etildi'}
            
        except socket.timeout:
            return {'success': False, 'error': 'Printerga ulanish vaqti tugadi'}
        except socket.error as e:
            return {'success': False, 'error': f'Printer bilan bog\'lanishda xatolik: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Noma\'lum xatolik: {str(e)}'}

    def test_connection(self):
        """Printer bilan aloqani tekshirish"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((self.printer_ip, self.printer_port))
            sock.close()
            return result == 0
        except:
            return False
