import csv
import hashlib
import json
from datetime import timedelta
from functools import wraps
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from .forms import IngredientForm, ProfileForm, SignUpForm
from .models import Favorite, Ingredient, LoginAttempt, Recipe, ShoppingItem
from .services import ingredient_data, normalize, profile_for, recipe_suggestions

def api(methods):
    def decorate(view):
        @wraps(view)
        @require_http_methods(methods)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Please sign in again.'}, status=401)
            try:
                request.payload = json.loads(request.body) if request.body else {}
                if not isinstance(request.payload, dict):
                    raise ValueError
            except (ValueError, UnicodeDecodeError):
                return JsonResponse({'error': 'Invalid JSON request.'}, status=400)
            return view(request, *args, **kwargs)
        return wrapped
    return decorate

@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST':
        key = hashlib.sha256((request.META.get('REMOTE_ADDR', '') + ':' + request.POST.get('username', '').lower()).encode()).hexdigest()
        attempt, _ = LoginAttempt.objects.get_or_create(key=key)
        if timezone.now() - attempt.window_started > timedelta(minutes=15):
            attempt.failures = 0
            attempt.window_started = timezone.now()
        if attempt.failures >= 10:
            form.add_error(None, 'Too many sign-in attempts. Please wait 15 minutes.')
        elif form.is_valid():
            attempt.delete()
            login(request, form.get_user())
            return redirect('dashboard')
        else:
            attempt.failures += 1
        if attempt.pk:
            attempt.save()
    return render(request, 'auth.html', {'form': form, 'signup': False})

@require_http_methods(['GET', 'POST'])
def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            user = form.save()
            profile_for(user)
        login(request, user)
        return redirect('dashboard')
    return render(request, 'auth.html', {'form': form, 'signup': True})

@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

@api(['GET'])
def state(request):
    profile = profile_for(request.user)
    return JsonResponse({
        'user': {'name': request.user.first_name or request.user.username, 'username': request.user.username,
                 'email': request.user.email, 'is_staff': request.user.is_staff},
        'ingredients': [ingredient_data(i) for i in request.user.ingredients.all()],
        'recipes': recipe_suggestions(request.user),
        'shopping': list(request.user.shopping_items.values('id', 'name', 'checked')),
        'settings': {'reminder_days': profile.reminder_days, 'email_reminders': profile.email_reminders},
        'today': timezone.localdate().isoformat(),
    })

@api(['POST'])
def ingredients(request):
    form = IngredientForm(request.payload)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors}, status=400)
    item = form.save(commit=False)
    item.owner = request.user
    item.save()
    return JsonResponse(ingredient_data(item), status=201)

@api(['PUT', 'DELETE'])
def ingredient_detail(request, pk):
    item = get_object_or_404(Ingredient, pk=pk, owner=request.user)
    if request.method == 'DELETE':
        item.delete()
        return JsonResponse({'ok': True})
    form = IngredientForm(request.payload, instance=item)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors}, status=400)
    return JsonResponse(ingredient_data(form.save()))

@api(['POST'])
def favorite(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    fav, created = Favorite.objects.get_or_create(user=request.user, recipe=recipe)
    if not created:
        fav.delete()
    return JsonResponse({'favorite': created})

@api(['POST'])
def shopping(request):
    names = request.payload.get('names', [])
    if not isinstance(names, list) or not 1 <= len(names) <= 50 or any(not isinstance(n, str) or not 1 <= len(n.strip()) <= 80 for n in names):
        return JsonResponse({'error': 'Enter 1–50 ingredient names, each up to 80 characters.'}, status=400)
    for name in names:
        ShoppingItem.objects.get_or_create(owner=request.user, name=normalize(name))
    return JsonResponse({'ok': True}, status=201)

@api(['PUT', 'DELETE'])
def shopping_detail(request, pk):
    item = get_object_or_404(ShoppingItem, pk=pk, owner=request.user)
    if request.method == 'DELETE':
        item.delete()
    else:
        checked = request.payload.get('checked')
        if not isinstance(checked, bool):
            return JsonResponse({'error': 'checked must be true or false.'}, status=400)
        item.checked = checked
        item.save(update_fields=['checked'])
    return JsonResponse({'ok': True})

@api(['PUT'])
def settings_view(request):
    form = ProfileForm(request.payload, instance=profile_for(request.user))
    if not form.is_valid():
        return JsonResponse({'errors': form.errors}, status=400)
    if form.cleaned_data['email_reminders'] and not request.user.email:
        return JsonResponse({'error': 'Your account needs an email address before enabling email reminders. An administrator can add it.'}, status=400)
    form.save()
    return JsonResponse({'ok': True})

@login_required
def export_inventory(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="fridgewise-inventory.csv"'
    writer = csv.writer(response)
    writer.writerow(['Ingredient', 'Category', 'Quantity', 'Unit', 'Expiry date'])
    for item in request.user.ingredients.all():
        name = item.name
        if name.lstrip().startswith(('=', '+', '-', '@')):
            name = "'" + name
        writer.writerow([name, item.get_category_display(), item.quantity, item.unit, item.expires_on])
    return response
