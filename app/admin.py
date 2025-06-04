from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Category, Product, Transaction, TelegramUser, Statistics

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'stock', 'created_at', 'updated_at')
    list_filter = ('category', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'transaction_type', 'timestamp', 'user')
    list_filter = ('transaction_type', 'timestamp', 'user')
    search_fields = ('product__name', 'notes')
    readonly_fields = ('timestamp',)

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'chat_id', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'chat_id')

@admin.register(Statistics)
class StatisticsAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_sales', 'total_revenue')
    list_filter = ('date',)
    readonly_fields = ('date',)
