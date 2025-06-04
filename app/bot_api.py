from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import json
import pandas as pd
from io import BytesIO
import openpyxl
from django.core.files.storage import default_storage
from django.conf import settings
import os

from .models import Product, Transaction, Statistics, TelegramUser, Category

@method_decorator(csrf_exempt, name='dispatch')
class AuthLoginView(View):
    def post(self, request):
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        chat_id = data.get('chat_id')
        
        user = authenticate(username=username, password=password)
        
        if user and user.is_staff:  # Faqat admin foydalanuvchilar
            # Telegram foydalanuvchini saqlash yoki yangilash
            telegram_user, created = TelegramUser.objects.get_or_create(
                chat_id=chat_id,
                defaults={'user': user}
            )
            if not created:
                telegram_user.user = user
                telegram_user.is_active = True
                telegram_user.save()
            
            return JsonResponse({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                }
            })
        
        return JsonResponse({'success': False, 'error': 'Invalid credentials'})

class AuthCheckView(View):
    def get(self, request, chat_id):
        try:
            telegram_user = TelegramUser.objects.get(chat_id=chat_id, is_active=True)
            return JsonResponse({'authenticated': True, 'user_id': telegram_user.user.id})
        except TelegramUser.DoesNotExist:
            return JsonResponse({'authenticated': False})

class StatisticsView(View):
    def get(self, request, period):
        today = timezone.now().date()
        
        if period == 'today':
            start_date = today
            end_date = today
        elif period == 'week':
            start_date = today - timedelta(days=7)
            end_date = today
        elif period == 'month':
            start_date = today - timedelta(days=30)
            end_date = today
        elif period == 'year':
            start_date = today - timedelta(days=365)
            end_date = today
        else:
            return JsonResponse({'error': 'Invalid period'}, status=400)
        
        # Asosiy statistika
        transactions = Transaction.objects.filter(
            timestamp__date__range=[start_date, end_date],
            transaction_type='OUT'
        )
        
        total_revenue = transactions.aggregate(
            total=Sum('sale_price')
        )['total'] or 0
        
        total_sales = transactions.count()
        
        products_sold = transactions.aggregate(
            total=Sum('quantity')
        )['total'] or 0
        
        average_sale = total_revenue / total_sales if total_sales > 0 else 0
        
        # Top mahsulotlar
        top_products = transactions.values('product__name').annotate(
            sold=Sum('quantity'),
            revenue=Sum('sale_price')
        ).order_by('-sold')[:10]
        
        # Kunlik daromad (grafik uchun)
        daily_revenue = []
        current_date = start_date
        while current_date <= end_date:
            day_revenue = Transaction.objects.filter(
                timestamp__date=current_date,
                transaction_type='OUT'
            ).aggregate(total=Sum('sale_price'))['total'] or 0
            
            daily_revenue.append({
                'date': current_date.strftime('%d.%m'),
                'revenue': float(day_revenue)
            })
            current_date += timedelta(days=1)
        
        return JsonResponse({
            'statistics': {
                'total_revenue': float(total_revenue),
                'total_sales': total_sales,
                'products_sold': float(products_sold),
                'average_sale': float(average_sale),
                'top_products': [
                    {
                        'name': item['product__name'],
                        'sold': float(item['sold']),
                        'revenue': float(item['revenue'])
                    } for item in top_products
                ],
                'daily_revenue': daily_revenue
            }
        })

class SalesReportView(View):
    def get(self, request):
        recent_sales = Transaction.objects.filter(
            transaction_type='OUT'
        ).select_related('product').order_by('-timestamp')[:20]
        
        sales_data = []
        for sale in recent_sales:
            sales_data.append({
                'product_name': sale.product.name,
                'quantity': float(sale.quantity),
                'unit_type': sale.product.unit_type,
                'sale_price': float(sale.sale_price),
                'date': sale.timestamp.strftime('%d.%m.%Y %H:%M'),
                'user': sale.user.username
            })
        
        return JsonResponse({'recent_sales': sales_data})

class ProductsReportView(View):
    def get(self, request):
        total_products = Product.objects.count()
        in_stock = Product.objects.filter(stock__gt=0).count()
        out_of_stock = Product.objects.filter(stock=0).count()
        
        # Kam qolgan mahsulotlar (10 dan kam)
        low_stock = Product.objects.filter(stock__lt=10, stock__gt=0).values(
            'name', 'stock', 'unit_type'
        )[:10]
        
        return JsonResponse({
            'total_products': total_products,
            'in_stock': in_stock,
            'out_of_stock': out_of_stock,
            'low_stock': [
                {
                    'name': item['name'],
                    'stock': float(item['stock']),
                    'unit_type': item['unit_type']
                } for item in low_stock
            ]
        })

class RevenueReportView(View):
    def get(self, request):
        today = timezone.now().date()
        
        # Bugungi daromad
        today_revenue = Transaction.objects.filter(
            timestamp__date=today,
            transaction_type='OUT'
        ).aggregate(total=Sum('sale_price'))['total'] or 0
        
        # Haftalik daromad
        week_start = today - timedelta(days=7)
        week_revenue = Transaction.objects.filter(
            timestamp__date__range=[week_start, today],
            transaction_type='OUT'
        ).aggregate(total=Sum('sale_price'))['total'] or 0
        
        # Oylik daromad
        month_start = today - timedelta(days=30)
        month_revenue = Transaction.objects.filter(
            timestamp__date__range=[month_start, today],
            transaction_type='OUT'
        ).aggregate(total=Sum('sale_price'))['total'] or 0
        
        # Yillik daromad
        year_start = today - timedelta(days=365)
        year_revenue = Transaction.objects.filter(
            timestamp__date__range=[year_start, today],
            transaction_type='OUT'
        ).aggregate(total=Sum('sale_price'))['total'] or 0
        
        # Xarajatlar va foyda
        total_cost = Transaction.objects.filter(
            timestamp__date__range=[month_start, today],
            transaction_type='OUT'
        ).aggregate(
            total=Sum('product__cost_price')
        )['total'] or 0
        
        net_profit = month_revenue - total_cost
        profit_margin = (net_profit / month_revenue * 100) if month_revenue > 0 else 0
        
        return JsonResponse({
            'today_revenue': float(today_revenue),
            'week_revenue': float(week_revenue),
            'month_revenue': float(month_revenue),
            'year_revenue': float(year_revenue),
            'total_cost': float(total_cost),
            'net_profit': float(net_profit),
            'profit_margin': float(profit_margin)
        })

class DetailedReportView(View):
    def get(self, request):
        # Excel hisobot yaratish
        today = timezone.now().date()
        month_start = today - timedelta(days=30)
        
        # Ma'lumotlarni olish
        transactions = Transaction.objects.filter(
            timestamp__date__range=[month_start, today]
        ).select_related('product', 'user')
        
        products = Product.objects.all().select_related('category')
        
        # Excel fayl yaratish
        wb = openpyxl.Workbook()
        
        # Sotuvlar varaqasi
        ws_sales = wb.active
        ws_sales.title = "Sotuvlar"
        ws_sales.append(['Sana', 'Mahsulot', 'Miqdor', 'Birlik', 'Narx', 'Foydalanuvchi', 'Turi'])
        
        for transaction in transactions:
            ws_sales.append([
                transaction.timestamp.strftime('%d.%m.%Y %H:%M'),
                transaction.product.name,
                float(transaction.quantity),
                transaction.product.unit_type,
                float(transaction.sale_price) if transaction.sale_price else 0,
                transaction.user.username,
                transaction.get_transaction_type_display()
            ])
        
        # Mahsulotlar varaqasi
        ws_products = wb.create_sheet("Mahsulotlar")
        ws_products.append(['Nomi', 'Kategoriya', 'Zaxira', 'Birlik', 'Kelgan narx', 'Min sotish narx'])
        
        for product in products:
            ws_products.append([
                product.name,
                product.category.name,
                float(product.stock),
                product.unit_type,
                float(product.cost_price),
                float(product.min_sale_price)
            ])
        
        # Faylni saqlash
        filename = f"hisobot_{today.strftime('%d_%m_%Y')}.xlsx"
        file_path = os.path.join(settings.MEDIA_ROOT, 'reports', filename)
        
        # Papka yaratish
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        wb.save(file_path)
        
        # Fayl URL ni qaytarish
        file_url = request.build_absolute_uri(settings.MEDIA_URL + f'reports/{filename}')
        
        return JsonResponse({
            'file_url': file_url,
            'filename': filename
        })