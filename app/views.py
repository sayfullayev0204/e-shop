from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout
from django.http import JsonResponse, HttpResponse
from django.db import models
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
import json
import datetime
from .receipt_printer import XPrinterManager
from .models import Product, Category, Transaction, TelegramUser, Statistics, Cart, CartItem, SaleReceipt
from .forms import (
    CustomLoginForm, ProductForm, CategoryForm, 
    TransactionForm, StockUpdateForm, ProductSearchForm
)


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('dashboard')
        else:
            return redirect('product_list')  # Oddiy foydalanuvchilar uchun
    
    if request.method == 'POST':
        form = CustomLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.is_staff:
                return redirect('dashboard')
            else:
                return redirect('product_list')  # Oddiy foydalanuvchilar uchun
    else:
        form = CustomLoginForm()
    
    return render(request, 'inventory_app/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
@user_passes_test(lambda u: u.is_staff)
def dashboard(request):
    # Get recent transactions
    recent_transactions = Transaction.objects.select_related('product', 'user').order_by('-timestamp')[:10]
    
    # Get low stock products (less than or equal to 5)
    low_stock_products = Product.objects.filter(stock__lte=5).select_related('category')
    
    # Get total products count
    total_products = Product.objects.count()
    
    # Get today's sales
    today = timezone.now().date()
    today_sales = Transaction.objects.filter(
        transaction_type='OUT',
        timestamp__date=today
    ).aggregate(
        count=Count('id'),
        total=Sum('quantity')
    )
    
    # Get this week's sales
    week_start = today - datetime.timedelta(days=today.weekday())
    week_sales = Transaction.objects.filter(
        transaction_type='OUT',
        timestamp__date__gte=week_start,
        timestamp__date__lte=today
    ).aggregate(
        count=Count('id'),
        total=Sum('quantity')
    )
    
    context = {
        'recent_transactions': recent_transactions,
        'low_stock_products': low_stock_products,
        'total_products': total_products,
        'today_sales': today_sales,
        'week_sales': week_sales,
    }
    
    return render(request, 'inventory_app/dashboard.html', context)


@login_required
def product_list(request):
    form = ProductSearchForm(request.GET)
    products = Product.objects.select_related('category').all()
    
    if form.is_valid():
        query = form.cleaned_data.get('query')
        category = form.cleaned_data.get('category')
        
        if query:
            products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
        
        if category:
            products = products.filter(category=category)
    
    # Pagination
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
    }
    
    return render(request, 'inventory_app/product_list.html', context)


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related('category'), pk=pk)
    
    # Staff userlar uchun tranzaksiyalar ko'rsatiladi
    transactions = []
    if request.user.is_staff:
        transactions = Transaction.objects.filter(product=product).select_related('user').order_by('-timestamp')[:10]
    
    context = {
        'product': product,
        'transactions': transactions,
    }
    
    return render(request, 'inventory_app/product_detail.html', context)




@login_required
@user_passes_test(lambda u: u.is_staff)
def product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            
            # Create a stock-in transaction
            if product.stock > 0:
                Transaction.objects.create(
                    product=product,
                    quantity=product.stock,
                    transaction_type='IN',
                    user=request.user,
                    notes='Initial stock'
                )
            
            messages.success(request, f'Product "{product.name}" has been added successfully.')
            return redirect('product_list')
    else:
        form = ProductForm()
    
    return render(request, 'inventory_app/product_form.html', {
        'form': form,
        'title': 'Add Product'
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    old_stock = product.stock
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            
            # Create a transaction if stock has changed
            new_stock = product.stock
            if new_stock != old_stock:
                if new_stock > old_stock:
                    # Stock increased
                    Transaction.objects.create(
                        product=product,
                        quantity=new_stock - old_stock,
                        transaction_type='IN',
                        user=request.user,
                        notes='Stock updated during product edit'
                    )
                else:
                    # Stock decreased
                    Transaction.objects.create(
                        product=product,
                        quantity=old_stock - new_stock,
                        transaction_type='OUT',
                        user=request.user,
                        notes='Stock updated during product edit'
                    )
            
            messages.success(request, f'Product "{product.name}" has been updated successfully.')
            return redirect('product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'inventory_app/product_form.html', {
        'form': form,
        'product': product,
        'title': 'Edit Product'
    })





@login_required
@user_passes_test(lambda u: u.is_staff)
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    old_stock = product.stock
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            
            # Create a transaction if stock has changed
            new_stock = product.stock
            if new_stock != old_stock:
                if new_stock > old_stock:
                    # Stock increased
                    Transaction.objects.create(
                        product=product,
                        quantity=new_stock - old_stock,
                        transaction_type='IN',
                        user=request.user,
                        notes='Stock updated during product edit'
                    )
                else:
                    # Stock decreased
                    Transaction.objects.create(
                        product=product,
                        quantity=old_stock - new_stock,
                        transaction_type='OUT',
                        user=request.user,
                        notes='Stock updated during product edit'
                    )
            
            messages.success(request, f'Product "{product.name}" has been updated successfully.')
            return redirect('product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'inventory_app/product_form.html', {
        'form': form,
        'product': product,
        'title': 'Edit Product'
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Product "{product_name}" has been deleted successfully.')
        return redirect('product_list')
    
    return render(request, 'inventory_app/product_confirm_delete.html', {'product': product})



@login_required
@user_passes_test(lambda u: u.is_staff)
def stock_add(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = StockUpdateForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']
            
            # Update product stock
            product.stock += quantity
            product.save()
            
            # Create transaction
            Transaction.objects.create(
                product=product,
                quantity=quantity,
                transaction_type='IN',
                user=request.user,
                notes=notes
            )
            
            messages.success(request, f'Added {quantity} units to "{product.name}" stock.')
            return redirect('product_detail', pk=product.pk)
    else:
        form = StockUpdateForm()
    
    return render(request, 'inventory_app/stock_form.html', {
        'form': form,
        'product': product,
        'action': 'add',
        'title': f'Add Stock - {product.name}'
    })



@login_required
@user_passes_test(lambda u: u.is_staff)
def stock_remove(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = StockUpdateForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            sold_price = form.cleaned_data['sold_price']
            notes = form.cleaned_data['notes'] or 'Zaxiradan olib tashlash'
            
            if quantity > product.stock:
                messages.error(request, f'Zaxirada faqat {product.stock} {product.unit_type} mavjud.')
                return redirect('stock_remove', pk=pk)
            
            if sold_price is None or sold_price <= product.min_sale_price:
                messages.error(request, f'Sotilgan narx {product.min_sale_price} so\'mdan yuqori bo\'lishi kerak!')
                return redirect('stock_remove', pk=pk)
            
            # Create a stock-out transaction
            Transaction.objects.create(
                product=product,
                quantity=quantity,
                transaction_type='OUT',
                sold_price=sold_price,
                user=request.user,
                notes=notes
            )
            
            # Update product stock
            product.stock -= quantity
            product.save()
            
            messages.success(request, f'{quantity} {product.unit_type} zaxiradan olib tashlandi.')
            return redirect('product_list')
    else:
        form = StockUpdateForm()
    
    return render(request, 'inventory_app/stock_update.html', {
        'form': form,
        'product': product,
        'action': 'remove',
        'title': 'Zaxirani Olib Tashlash'
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def category_list(request):
    categories = Category.objects.annotate(product_count=Count('products'))
    return render(request, 'inventory_app/category_list.html', {'categories': categories})


@login_required
@user_passes_test(lambda u: u.is_staff)
def category_add(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" has been added successfully.')
            return redirect('category_list')
    else:
        form = CategoryForm()
    
    return render(request, 'inventory_app/category_form.html', {
        'form': form,
        'title': 'Add Category'
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" has been updated successfully.')
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    
    return render(request, 'inventory_app/category_form.html', {
        'form': form,
        'category': category,
        'title': 'Edit Category'
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f'Category "{category_name}" has been deleted successfully.')
        return redirect('category_list')
    
    return render(request, 'inventory_app/category_confirm_delete.html', {'category': category})

from .forms import TransactionFilterForm
from django.db.models import Q
# Transaction list view ni yangilash
@login_required
@user_passes_test(lambda u: u.is_staff)
def transaction_list(request):
    form = TransactionFilterForm(request.GET)
    transactions = Transaction.objects.select_related('product', 'user').order_by('-timestamp')
    
    if form.is_valid():
        search = form.cleaned_data.get('search')
        transaction_type = form.cleaned_data.get('transaction_type')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        user = form.cleaned_data.get('user')
        
        if search:
            transactions = transactions.filter(
                Q(transaction_id__icontains=search) |
                Q(product__name__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(notes__icontains=search)
            )
        
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        
        if start_date:
            transactions = transactions.filter(timestamp__date__gte=start_date)
        
        if end_date:
            transactions = transactions.filter(timestamp__date__lte=end_date)
        
        if user:
            transactions = transactions.filter(user=user)
    
    # Calculate total amount for OUT transactions
    total_amount = transactions.filter(transaction_type='OUT').aggregate(
        total=Sum(models.F('quantity') * models.F('sold_price'))
    )['total'] or 0
    
    # Pagination
    paginator = Paginator(transactions, 20)  # Show 20 transactions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'inventory_app/transaction_list.html', {
        'page_obj': page_obj,
        'form': form,
        'total_count': transactions.count(),
        'total_amount': total_amount  # Pass total_amount to template
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def statistics(request):
    # Get date range
    end_date = timezone.now().date()
    start_date = end_date - datetime.timedelta(days=30)  # Last 30 days by default
    
    # Get date range from request if provided
    if request.GET.get('start_date') and request.GET.get('end_date'):
        try:
            start_date = datetime.datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format. Using default date range.')
    
    # Get daily statistics
    daily_stats = Statistics.objects.filter(date__gte=start_date, date__lte=end_date).order_by('date')
    
    # Get top selling products
    top_products = Product.objects.annotate(
        total_sold=Sum('transactions__quantity', filter=Q(transactions__transaction_type='OUT'))
    ).filter(total_sold__gt=0).order_by('-total_sold')[:10]
    
    # Get category distribution
    category_stats = Category.objects.annotate(
        total_sold=Sum('products__transactions__quantity', 
                      filter=Q(products__transactions__transaction_type='OUT'))
    ).filter(total_sold__gt=0).order_by('-total_sold')
    
    context = {
        'daily_stats': daily_stats,
        'top_products': top_products,
        'category_stats': category_stats,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'inventory_app/statistics.html', context)


@login_required
def product_qr(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'inventory_app/product_qr.html', {'product': product})


@login_required
def qr_scanner(request):
    """QR kod skanerlash sahifasi"""
    # Get cart count for the current user
    try:
        cart = Cart.objects.get(user=request.user)
        cart_count = cart.items.count()
    except Cart.DoesNotExist:
        cart_count = 0
    
    return render(request, 'inventory_app/qr_scanner.html', {
        'cart_count': cart_count
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def qr_test(request):
    """QR kodlarni test qilish uchun sahifa"""
    products = Product.objects.all()[:5]  # Birinchi 5 ta mahsulot
    
    # Har bir mahsulot uchun QR kod ma'lumotlarini tayyorlash
    qr_data = []
    for product in products:
        qr_info = {
            'product': product,
            'qr_url': f"/products/{product.id}/",
            'qr_data_variants': [
                f"/products/{product.id}/",
                f"/products/{product.id}",
                f"products/{product.id}",
                str(product.id),
                f"http://localhost:8000/products/{product.id}/",
            ]
        }
        qr_data.append(qr_info)
    
    return render(request, 'inventory_app/qr_test.html', {'qr_data': qr_data})


# API endpoints

@login_required
def api_cart_count(request):
    """Cart dagi mahsulotlar sonini qaytarish"""
    try:
        cart = Cart.objects.get(user=request.user)
        count = cart.items.count()
        return JsonResponse({'success': True, 'count': count})
    except Cart.DoesNotExist:
        return JsonResponse({'success': True, 'count': 0})

# API endpoints
@login_required
def api_products(request):
    query = request.GET.get('query', '')
    category_id = request.GET.get('category')
    
    products = Product.objects.select_related('category').all()
    
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    products = products[:10]
    
    data = [{
        'id': product.id,
        'name': product.name,
        'description': product.description or '',
        'cost_price': float(product.cost_price),
        'min_sale_price': float(product.min_sale_price),
        'sale_price': float(product.sale_price),
        'stock': float(product.stock),
        'unit_type': product.unit_type,
        'category': product.category.name,
        'category_id': product.category.id,
        'image_url': product.image.url if product.image else None,
    } for product in products]
    
    return JsonResponse({'products': data})


@login_required
def api_product_detail(request, pk):
    try:
        product = Product.objects.select_related('category').get(pk=pk)
        data = {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'cost_price': float(product.cost_price),
            'min_sale_price': float(product.min_sale_price),
            'sale_price': float(product.sale_price),
            'stock': product.stock,
            'category': product.category.name,
            'category_id': product.category.id,
            'image_url': product.image.url if product.image else None,
            'created_at': product.created_at.isoformat(),
            'updated_at': product.updated_at.isoformat(),
        }
        return JsonResponse(data)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)


@login_required
@user_passes_test(lambda u: u.is_staff)
def api_stock_update(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = float(data.get('quantity', 0))
            transaction_type = data.get('transaction_type')
            sold_price = data.get('sale_price') if transaction_type == 'OUT' else None
            notes = data.get('notes', '')
            
            product = get_object_or_404(Product, pk=product_id)
            
            if transaction_type == 'OUT':
                if quantity > product.stock:
                    return JsonResponse({'success': False, 'error': f'Zaxirada faqat {product.stock} {product.unit_type} mavjud.'})
                
                if sold_price is None or float(sold_price) <= float(product.min_sale_price):
                    return JsonResponse({'success': False, 'error': f'Sotilgan narx {product.min_sale_price} so\'mdan yuqori bo\'lishi kerak!'})
            
            # Create transaction
            Transaction.objects.create(
                product=product,
                quantity=quantity,
                transaction_type=transaction_type,
                sold_price=sold_price if transaction_type == 'OUT' else None,
                user=request.user,
                notes=notes
            )
            
            # Update product stock
            if transaction_type == 'IN':
                product.stock += quantity
            else:  # OUT
                product.stock -= quantity
            product.save()
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Faqat POST so\'rovlari qabul qilinadi'})

# Cart views - barcha userlar uchun ruxsat etilgan

# Cart views
@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    total_price = sum(item.quantity * item.sold_price for item in cart_items)
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'cart': cart
    }
    return render(request, 'inventory_app/cart_view.html', context)


@login_required
def cart_add(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = data.get('quantity')
            sold_price = data.get('sold_price')

            # Ma'lumotlarni tekshirish
            if not product_id:
                return JsonResponse({'success': False, 'error': 'Mahsulot ID kiritilmagan'})
            
            if not quantity:
                return JsonResponse({'success': False, 'error': 'Miqdor kiritilmagan'})
            
            if not sold_price:
                return JsonResponse({'success': False, 'error': 'Sotilgan narx kiritilmagan'})

            # Ma'lumotlarni float ga o'tkazish
            try:
                quantity = float(quantity)
                sold_price = float(sold_price)
            except (ValueError, TypeError):
                return JsonResponse({'success': False, 'error': 'Noto\'g\'ri raqamli ma\'lumotlar'})

            product = get_object_or_404(Product, pk=product_id)

            # Minimal narxni tekshirish
            if sold_price <= float(product.min_sale_price):
                return JsonResponse({
                    'success': False, 
                    'error': f'Sotilgan narx {product.min_sale_price} so\'mdan yuqori bo\'lishi kerak! Bu narxda sotolmaysiz.'
                })

            # Zaxirani tekshirish
            if quantity > float(product.stock):
                return JsonResponse({'success': False, 'error': 'Zaxirada yetarli mahsulot yo\'q!'})

            # Savatni olish yoki yaratish
            cart, created = Cart.objects.get_or_create(user=request.user)

            # Savatda mahsulotni yangilash yoki qo'shish
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity, 'sold_price': sold_price}
            )

            if not created:
                cart_item.quantity += quantity
                cart_item.sold_price = sold_price
                cart_item.save()

            cart_count = cart.items.count()
            return JsonResponse({'success': True, 'cart_count': cart_count})

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Noto\'g\'ri JSON format'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Server xatosi: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'Faqat POST so\'rovlari qabul qilinadi'})


@login_required
def cart_update(request, cart_item_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            quantity = data.get('quantity')
            sold_price = data.get('sold_price')

            # Ma'lumotlarni tekshirish
            if not quantity:
                return JsonResponse({'success': False, 'error': 'Miqdor kiritilmagan'})
            
            if not sold_price:
                return JsonResponse({'success': False, 'error': 'Sotilgan narx kiritilmagan'})

            # Ma'lumotlarni float ga o'tkazish
            try:
                quantity = float(quantity)
                sold_price = float(sold_price)
            except (ValueError, TypeError):
                return JsonResponse({'success': False, 'error': 'Noto\'g\'ri raqamli ma\'lumotlar'})

            cart_item = get_object_or_404(CartItem, pk=cart_item_id, cart__user=request.user)
            product = cart_item.product

            # Minimal narxni tekshirish
            if sold_price <= float(product.min_sale_price):
                return JsonResponse({
                    'success': False, 
                    'error': f'Sotilgan narx {product.min_sale_price} so\'mdan yuqori bo\'lishi kerak! Bu narxda sotolmaysiz.'
                })

            # Zaxirani tekshirish
            if quantity > float(product.stock):
                return JsonResponse({'success': False, 'error': 'Zaxirada yetarli mahsulot yo\'q!'})

            # Savatdagi mahsulotni yangilash
            cart_item.quantity = quantity
            cart_item.sold_price = sold_price
            cart_item.save()

            cart_count = cart_item.cart.items.count()
            return JsonResponse({'success': True, 'cart_count': cart_count})

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Noto\'g\'ri JSON format'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Server xatosi: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'Faqat POST so\'rovlari qabul qilinadi'})


@login_required
def cart_remove(request, cart_item_id):
    if request.method == 'POST':
        try:
            cart_item = get_object_or_404(CartItem, pk=cart_item_id, cart__user=request.user)
            cart = cart_item.cart
            cart_item.delete()

            cart_count = cart.items.count()
            return JsonResponse({
                'success': True,
                'cart_count': cart_count
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Server xatosi: {str(e)}'
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': 'Faqat POST so\'rovlari qabul qilinadi'
    }, status=405)


# views.py dagi cart_confirm funksiyasini yangilash

@login_required
def cart_confirm(request):
    if request.method == 'POST':
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = cart.items.all()

        if not cart_items:
            return JsonResponse({'success': False, 'error': 'Savat bo\'sh!'})

        total_quantity = 0
        total_revenue = 0
        receipt_items = []

        # Birinchi navbatda barcha mahsulotlarni tekshirish
        for cart_item in cart_items:
            product = cart_item.product
            quantity = cart_item.quantity
            sold_price = cart_item.sold_price

            if quantity > float(product.stock):
                return JsonResponse({
                    'success': False, 
                    'error': f'{product.name} uchun zaxirada yetarli mahsulot yo\'q!'
                })

        # Sotuv chekini yaratish
        sale_receipt = SaleReceipt.objects.create(
            user=request.user,
            notes='Savatdan tasdiqlangan sotuv'
        )

        # Har bir mahsulot uchun tranzaksiya yaratish
        for cart_item in cart_items:
            product = cart_item.product
            quantity = cart_item.quantity
            sold_price = cart_item.sold_price

            total_quantity += quantity
            item_total = quantity * sold_price
            total_revenue += item_total

            # Tranzaksiya yaratish (sale_receipt bilan bog'langan)
            Transaction.objects.create(
                sale_receipt=sale_receipt,
                product=product,
                user=request.user,
                quantity=quantity,
                transaction_type='OUT',
                sold_price=sold_price,
                notes=f'Chek #{sale_receipt.receipt_id} orqali sotuv'
            )

            # Zaxirani yangilash
            product.stock -= quantity
            product.save()

            # Chek uchun mahsulot ma'lumotlarini saqlash
            receipt_items.append({
                'name': product.name,
                'quantity': float(quantity),
                'price': float(sold_price),
                'total': float(item_total)
            })

        # Sotuv cheki ma'lumotlarini yangilash
        sale_receipt.total_amount = total_revenue
        sale_receipt.total_items = len(cart_items)
        sale_receipt.save()

        # Statistikani yangilash
        today = timezone.now().date()
        stats, created = Statistics.objects.get_or_create(date=today)
        stats.total_sales += total_quantity
        stats.total_revenue += total_revenue
        stats.save()

        # Savatni tozalash
        cart_items.delete()
        cart_count = cart.items.count()

        response_data = {
            'success': True,
            'cart_count': cart_count,
            'message': f'Sotuv tasdiqlandi! Chek #{sale_receipt.receipt_id}',
            'receipt_id': sale_receipt.receipt_id,
            'receipt': {
                'receipt_id': sale_receipt.receipt_id,
                'date': sale_receipt.timestamp.strftime('%d.%m.%Y'),
                'time': sale_receipt.timestamp.strftime('%H:%M:%S'),
                'cashier': request.user.get_full_name() or request.user.username,
                'items': receipt_items,
                'total': float(total_revenue)
            }
        }

        return JsonResponse(response_data)

    return JsonResponse({'success': False, 'error': 'Faqat POST so\'rovlari qabul qilinadi'})


# Yangi view: Chek tafsilotlarini ko'rish
@login_required
def sale_receipt_detail(request, receipt_id):
    try:
        sale_receipt = SaleReceipt.objects.get(receipt_id=receipt_id)
        transactions = sale_receipt.transactions.all()
        
        receipt_data = {
            'receipt_id': sale_receipt.receipt_id,
            'date': sale_receipt.timestamp.strftime('%d.%m.%Y'),
            'time': sale_receipt.timestamp.strftime('%H:%M:%S'),
            'cashier': sale_receipt.user.get_full_name() or sale_receipt.user.username,
            'total_amount': float(sale_receipt.total_amount),
            'total_items': sale_receipt.total_items,
            'notes': sale_receipt.notes,
            'items': []
        }
        
        for transaction in transactions:
            receipt_data['items'].append({
                'product_name': transaction.product.name,
                'category': transaction.product.category.name,
                'quantity': float(transaction.quantity),
                'unit_type': transaction.product.get_unit_type_display(),
                'sold_price': float(transaction.sold_price),
                'total': float(transaction.quantity * transaction.sold_price)
            })
        
        return JsonResponse({'success': True, 'receipt': receipt_data})
        
    except SaleReceipt.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Chek topilmadi'})


@login_required
def test_printer(request):
    """Printerni test qilish uchun view"""
    if request.method == 'POST':
        printer = XPrinterManager()
        
        # Test chek ma'lumotlari
        test_receipt = {
            'receipt_id': 'TEST001',
            'date': datetime.datetime.now().strftime('%d.%m.%Y'),
            'time': datetime.datetime.now().strftime('%H:%M:%S'),
            'cashier': request.user.get_full_name() or request.user.username,
            'items': [
                {'name': 'Test mahsulot', 'quantity': 1, 'price': 10000, 'total': 10000}
            ],
            'total': 10000
        }
        
        result = printer.print_receipt(test_receipt)
        return JsonResponse(result)
    
    return JsonResponse({'success': False, 'error': 'Faqat POST so\'rovlari qabul qilinadi'})


@login_required
def printer_status(request):
    """Printer holatini tekshirish"""
    printer = XPrinterManager()
    is_connected = printer.test_connection()
    
    return JsonResponse({
        'success': True,
        'connected': is_connected,
        'message': 'Printer ulangan' if is_connected else 'Printer ulanmagan'
    })
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Product
from .serializers import ProductSerializer

class ProductDetailView(APIView):
    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
            serializer = ProductSerializer(product)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)