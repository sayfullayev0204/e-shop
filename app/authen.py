from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .forms import UserRegisterForm  # Yangi forma yaratiladi
from django.shortcuts import get_object_or_404, redirect, render  # Import for get_object_or_404, redirect, and render

@login_required
@user_passes_test(lambda u: u.is_staff, login_url='product_list')
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password']
            
            # Username mavjudligini tekshirish
            if User.objects.filter(username=username).exists():
                messages.error(request, "Bu foydalanuvchi nomi allaqachon mavjud. Iltimos, boshqa nom tanlang.")
                return redirect('register')
            
            # Yangi foydalanuvchi yaratish
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                password=password
            )
            
            messages.success(request, f"Foydalanuvchi {username} muvaffaqiyatli qo'shildi!")
            return redirect('user_list')  # Foydalanuvchilar ro'yxati sahifasiga yo'naltirish
    else:
        form = UserRegisterForm()
    
    return render(request, 'inventory_app/auth/register.html', {'form': form, 'title': 'Yangi foydalanuvchi qo\'shish'})

@login_required
@user_passes_test(lambda u: u.is_staff, login_url='product_list')
def user_list(request):
    users = User.objects.all()
    return render(request, 'inventory_app/auth/user_list.html', {'users': users})

@login_required
@user_passes_test(lambda u: u.is_staff, login_url='product_list')
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user.username = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            if form.cleaned_data['password']:
                user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, f"Foydalanuvchi {user.username} muvaffaqiyatli yangilandi!")
            return redirect('user_list')
    else:
        form = UserRegisterForm(initial={
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        })
    return render(request, 'inventory_app/auth/user_form.html', {'form': form, 'user': user, 'title': 'Foydalanuvchini tahrirlash'})

@login_required
@user_passes_test(lambda u: u.is_staff, login_url='product_list')
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"Foydalanuvchi {username} muvaffaqiyatli o'chirildi!")
        return redirect('user_list')
    return render(request, 'inventory_app/auth/user_confirm_delete.html', {'user': user})