import re
from datetime import timedelta
from django.utils import timezone
from .models import Favorite, Profile, Recipe

ALIASES = {
    'tomatoes': 'tomato', 'cherry tomatoes': 'tomato', 'cherry tomato': 'tomato',
    'eggs': 'egg', 'potatoes': 'potato', 'onions': 'onion', 'red onion': 'onion',
    'carrots': 'carrot', 'bell peppers': 'pepper', 'bell pepper': 'pepper', 'peppers': 'pepper',
    'chicken breast': 'chicken', 'chicken breasts': 'chicken', 'chickpeas': 'chickpea',
    'canned chickpeas': 'chickpea', 'rolled oats': 'oats', 'bananas': 'banana',
    'lemons': 'lemon', 'avocados': 'avocado', 'mushrooms': 'mushroom', 'lentils': 'lentil',
    'greek yogurt': 'yogurt', 'feta cheese': 'feta', 'fresh spinach': 'spinach',
    'garlic cloves': 'garlic', 'cucumbers': 'cucumber', 'zucchini': 'courgette',
}

def normalize(name):
    name = re.sub(r'\s+', ' ', name.strip().lower())
    return ALIASES.get(name, name)

def profile_for(user):
    return Profile.objects.get_or_create(user=user)[0]

def alerts_for(user):
    profile = profile_for(user)
    return user.ingredients.filter(expires_on__lte=timezone.localdate() + timedelta(days=profile.reminder_days))

def ingredient_data(item):
    return {'id': item.pk, 'name': item.name, 'category': item.category,
            'quantity': format(item.quantity.normalize(), 'f'), 'unit': item.unit,
            'expires_on': item.expires_on.isoformat(), 'days_left': item.days_left}

def recipe_suggestions(user):
    today = timezone.localdate()
    inventory = list(user.ingredients.filter(expires_on__gte=today))
    available = {normalize(i.name) for i in inventory}
    soon = {normalize(i.name) for i in inventory if i.days_left <= profile_for(user).reminder_days}
    favorites = set(Favorite.objects.filter(user=user).values_list('recipe_id', flat=True))
    result = []
    for recipe in Recipe.objects.prefetch_related('ingredients'):
        ingredients = list(recipe.ingredients.all())
        matched = [i for i in ingredients if normalize(i.name) in available]
        missing = [i.name for i in ingredients if normalize(i.name) not in available]
        urgent = [i.name for i in matched if normalize(i.name) in soon]
        result.append({
            'id': recipe.pk, 'title': recipe.title, 'description': recipe.description,
            'category': recipe.category, 'minutes': recipe.minutes, 'servings': recipe.servings,
            'art': recipe.art, 'instructions': recipe.instructions, 'favorite': recipe.pk in favorites,
            'ingredients': [{'name': i.name, 'amount': i.amount, 'available': normalize(i.name) in available} for i in ingredients],
            'matched': len(matched), 'total': len(ingredients), 'missing': missing,
            'match': round(len(matched) / len(ingredients) * 100) if ingredients else 0,
            'use_soon': urgent, 'ready': bool(ingredients) and not missing,
        })
    return sorted(result, key=lambda r: (r['ready'], r['match'], len(r['use_soon']), -r['minutes']), reverse=True)
