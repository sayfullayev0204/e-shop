from django.urls import path
from . import views
from .authen import register, user_list, user_edit, user_delete
from . import bot_api
urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    
    # Stock Management
    
    path('products/<int:pk>/stock/add/', views.stock_add, name='stock_add'),
    path('products/<int:pk>/stock/remove/', views.stock_remove, name='stock_remove'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    # Transactions
    path('transactions/', views.transaction_list, name='transaction_list'),
    
    # Statistics
    path('statistics/', views.statistics, name='statistics'),
    
    # QR Code
    path('products/<int:pk>/qr/', views.product_qr, name='product_qr'),
    path('scanner/', views.qr_scanner, name='qr_scanner'),
    path('qr-scanner/', views.qr_scanner, name='qr_scanner'),
    path('qr-test/', views.qr_test, name='qr_test'),  # Test sahifasi
    
    # API endpoints
    path('api/products/', views.api_products, name='api_products'),
    path('api/products/<int:pk>/', views.api_product_detail, name='api_product_detail'),
    path('api/stock/update/', views.api_stock_update, name='api_stock_update'),
    

    path('cart/', views.cart_view, name='cart_view'),
    path('api/cart/add/', views.cart_add, name='cart_add'),
    path('api/cart/update/<int:cart_item_id>/', views.cart_update, name='cart_update'),
    path('api/cart/remove/<int:cart_item_id>/', views.cart_remove, name='cart_remove'),
    path('api/cart/confirm/', views.cart_confirm, name='cart_confirm'),

    path('api/cart/count/', views.api_cart_count, name='api_cart_count'),

    path('register/', register, name='register'),
    path('users/', user_list, name='user_list'),
    path('users/<int:pk>/edit/', user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', user_delete, name='user_delete'),



    path('api/auth/login/', bot_api.AuthLoginView.as_view(), name='api_auth_login'),
    path('api/auth/check/<str:chat_id>/', bot_api.AuthCheckView.as_view(), name='api_auth_check'),
    
    # Statistics
    path('api/statistics/<str:period>/', bot_api.StatisticsView.as_view(), name='api_statistics'),
    
    # Reports
    path('api/reports/sales/', bot_api.SalesReportView.as_view(), name='api_sales_report'),
    path('api/reports/products/', bot_api.ProductsReportView.as_view(), name='api_products_report'),
    path('api/reports/revenue/', bot_api.RevenueReportView.as_view(), name='api_revenue_report'),
    path('api/reports/detailed/', bot_api.DetailedReportView.as_view(), name='api_detailed_report'),


    path('mobile/products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),

    
    path('api/printer/test/', views.test_printer, name='test_printer'),
    path('api/printer/status/', views.printer_status, name='printer_status'),
]



