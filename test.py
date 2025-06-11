from escpos.printer import Usb

try:
    # Printerning Vendor ID va Product ID sini kiritish kerak
    # Bu qiymatlarni printer hujjatlaridan yoki `lsusb` buyrug'i orqali topish mumkin
    # Misol uchun, XPrinter uchun umumiy ID lar:
    printer = Usb(idVendor=0x0483, idProduct=0x5743)

    # Chop etish
    printer.text("Salom, XPrinter!\n")
    printer.text("Bu test chop etish.\n")
    printer.cut()  # Qog'ozni kesish
    printer.close()  # Printerni yopish

    print("Chop etish muvaffaqiyatli yakunlandi!")
except Exception as e:
    print(f"Xato yuz berdi: {e}")