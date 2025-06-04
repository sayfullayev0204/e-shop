# core/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Statistics

class StatisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Statistics
        fields = ['date', 'total_sales', 'total_revenue']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password']

from rest_framework import serializers
from .models import Product

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'min_sale_price', 'stock', 'unit_type', 'description', 'category']
