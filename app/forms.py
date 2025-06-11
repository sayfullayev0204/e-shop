from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from .models import Product, Transaction, Category, CartItem
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'cost_price', 'min_sale_price', 'sale_price', 'stock', 'unit_type', 'category', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_sale_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit_type': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'cost_price': 'Kelgan Narx (so\'m)',
            'min_sale_price': 'Minimal Narx (so\'m)',
            'sale_price': 'Sotish Narxi (so\'m)',
        }
    
    def clean_min_sale_price(self):
        min_sale_price = self.cleaned_data.get('min_sale_price')
        cost_price = self.cleaned_data.get('cost_price')
        
        if min_sale_price and cost_price:
            if min_sale_price < cost_price:
                raise ValidationError('Minimal narx kelgan narxdan kam bo\'lmasligi kerak.')
        
        return min_sale_price
    
    def clean_sale_price(self):
        sale_price = self.cleaned_data.get('sale_price')
        min_sale_price = self.cleaned_data.get('min_sale_price')
        
        if sale_price and min_sale_price:
            if sale_price < min_sale_price:
                raise ValidationError('Sotish narxi minimal narxdan kam bo\'lmasligi kerak.')
        
        return sale_price


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class TransactionForm(forms.ModelForm):
    sold_price = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        label='Sotilgan Narx (so\'m)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Sotilgan narxi (so\'m)', 'step': '0.01'})
    )
    
    class Meta:
        model = Transaction
        fields = ['product', 'quantity', 'transaction_type', 'sold_price', 'notes']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get('transaction_type')
        sold_price = cleaned_data.get('sold_price')
        product = cleaned_data.get('product')
        
        if transaction_type == 'OUT':
            if sold_price is None:
                self.add_error('sold_price', 'Sotilgan narx "Stock Out" tranzaksiyasi uchun kiritilishi shart.')
            elif product and sold_price:
                if sold_price <= product.min_sale_price:
                    self.add_error('sold_price', f'Sotilgan narx {product.min_sale_price} so\'mdan yuqori bo\'lishi kerak! Bu narxda sotolmaysiz.')
        
        if transaction_type == 'IN' and sold_price is not None:
            self.add_error('sold_price', 'Sotilgan narx "Stock In" tranzaksiyasi uchun kiritilmasligi kerak.')
        
        return cleaned_data


class CartItemForm(forms.ModelForm):
    quantity = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label='Miqdor',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'})
    )
    sold_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label='Sotilgan Narx (so\'m)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    
    class Meta:
        model = CartItem
        fields = ['quantity', 'sold_price']
    
    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
    
    def clean_sold_price(self):
        sold_price = self.cleaned_data.get('sold_price')
        
        if self.product and sold_price:
            if sold_price <= self.product.min_sale_price:
                raise ValidationError(f'Sotilgan narx {self.product.min_sale_price} so\'mdan yuqori bo\'lishi kerak! Bu narxda sotolmaysiz.')
        
        return sold_price


class StockUpdateForm(forms.Form):
    quantity = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label='Miqdor',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'})
    )
    sold_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label='Sotilgan Narx (so\'m)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Sotilgan narxi (so\'m)', 'step': '0.01'})
    )
    notes = forms.CharField(
        required=False,
        label='Eslatmalar',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )


class ProductSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mahsulot izlash...'})
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="Barcha Kategoriyalar",
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class UserRegisterForm(forms.Form):
    first_name = forms.CharField(max_length=30, required=True, label="Ism")
    last_name = forms.CharField(max_length=30, required=True, label="Familiya")
    username = forms.CharField(max_length=150, required=True, label="Foydalanuvchi nomi")
    password = forms.CharField(widget=forms.PasswordInput, required=True, label="Parol")



class TransactionFilterForm(forms.Form):
    TRANSACTION_TYPE_CHOICES = [
        ('', 'Barcha turlar'),
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Transaction ID, mahsulot nomi yoki foydalanuvchi...'
        })
    )
    
    transaction_type = forms.ChoiceField(
        choices=TRANSACTION_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label="Barcha foydalanuvchilar",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
