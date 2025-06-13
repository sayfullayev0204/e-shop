from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image
import os
import random


class Category(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"


class Product(models.Model):
    UNIT_TYPES = (
        ('piece', 'Dona'),
        ('kg', 'Kilogram'),
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    min_sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    unit_type = models.CharField(max_length=10, choices=UNIT_TYPES, default='piece')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.min_sale_price and self.cost_price:
            if self.min_sale_price < self.cost_price:
                raise ValidationError({'min_sale_price': 'Minimal narx kelgan narxdan kam bo\'lmasligi kerak.'})
        
        if self.sale_price and self.min_sale_price:
            if self.sale_price < self.min_sale_price:
                raise ValidationError({'sale_price': 'Sotish narxi minimal narxdan kam bo\'lmasligi kerak.'})
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        if not self.qr_code:
            self.generate_qr_code()
            super().save(update_fields=['qr_code'])
    
    def generate_qr_code(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_data = f"https://phoenix-rapid-factually.ngrok-free.app/products/{self.id}/"
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        filename = f'product_{self.id}_qr.png'
        self.qr_code.save(filename, File(buffer), save=False)


# Yangi model: Sotuv cheki
class SaleReceipt(models.Model):
    receipt_id = models.CharField(max_length=6, unique=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sale_receipts')
    timestamp = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_items = models.IntegerField(default=0)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Chek #{self.receipt_id} - {self.user.username} - {self.timestamp.strftime('%d.%m.%Y %H:%M')}"
    
    def generate_receipt_id(self):
        """6 xonali unique chek ID yaratish"""
        while True:
            receipt_id = str(random.randint(100000, 999999))
            if not SaleReceipt.objects.filter(receipt_id=receipt_id).exists():
                return receipt_id
    
    def save(self, *args, **kwargs):
        if not self.receipt_id:
            self.receipt_id = self.generate_receipt_id()
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-timestamp']


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
    )
    
    # Unique 6 xonali ID (faqat individual tranzaksiyalar uchun)
    transaction_id = models.CharField(max_length=6, unique=True, blank=True, null=True)
    # Sotuv cheki bilan bog'lanish (faqat sotuvlar uchun)
    sale_receipt = models.ForeignKey(SaleReceipt, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='transactions')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=3, choices=TRANSACTION_TYPES)
    sold_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        if self.sale_receipt:
            return f"Chek #{self.sale_receipt.receipt_id} - {self.product.name} ({self.quantity} {self.product.unit_type})"
        else:
            return f"{self.transaction_id} - {self.transaction_type} - {self.product.name} ({self.quantity} {self.product.unit_type})"
    
    def generate_transaction_id(self):
        """6 xonali unique ID yaratish (faqat individual tranzaksiyalar uchun)"""
        while True:
            transaction_id = str(random.randint(100000, 999999))
            if not Transaction.objects.filter(transaction_id=transaction_id).exists():
                return transaction_id
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.transaction_type == 'OUT' and self.sold_price:
            if self.sold_price <= self.product.min_sale_price:
                raise ValidationError({
                    'sold_price': f'Sotilgan narx {self.product.min_sale_price} so\'mdan yuqori bo\'lishi kerak! Bu narxda sotolmaysiz.'
                })
    
    def save(self, *args, **kwargs):
        # Transaction ID yaratish (faqat individual tranzaksiyalar uchun)
        if not self.sale_receipt and not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
            
        if self.transaction_type == 'OUT':
            if self.sold_price is None:
                raise ValueError("Sotilgan narx 'Stock Out' tranzaksiyasi uchun kiritilishi shart.")
            if self.sold_price <= self.product.min_sale_price:
                raise ValueError(f"Sotilgan narx {self.product.min_sale_price} so'mdan yuqori bo'lishi kerak! Bu narxda sotolmaysiz.")
            if self.quantity > self.product.stock:
                raise ValueError(f"{self.product.name} uchun yetarli zaxira yo'q.")
        
        self.full_clean()
        super().save(*args, **kwargs)
        
        if self.transaction_type == 'IN':
            self.product.stock += self.quantity
        elif self.transaction_type == 'OUT':
            self.product.stock -= self.quantity
        self.product.save()


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Cart for {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    sold_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.sold_price and self.product:
            if self.sold_price <= self.product.min_sale_price:
                raise ValidationError({
                    'sold_price': f'Sotilgan narx {self.product.min_sale_price} so\'mdan yuqori bo\'lishi kerak! Bu narxda sotolmaysiz.'
                })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_total(self):
        """CartItem uchun jami summani qaytarish"""
        return self.quantity * self.sold_price
    
    def __str__(self):
        return f"{self.quantity} {self.product.unit_type} of {self.product.name}"


class TelegramUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='telegram_accounts')
    chat_id = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.chat_id}"


class Statistics(models.Model):
    date = models.DateField(default=timezone.now)
    total_sales = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    
    def __str__(self):
        return f"Stats for {self.date}"
    
    class Meta:
        verbose_name_plural = "Statistics"
