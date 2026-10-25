import secrets
from datetime import timedelta
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from kitchen.models import Ingredient, Profile, Recipe, RecipeIngredient
from kitchen.seed_data import DEMO_INVENTORY, RECIPES

class Command(BaseCommand):
    help = 'Add example recipes, a demo kitchen, and an admin account. Existing data and passwords are preserved.'

    @transaction.atomic
    def handle(self, *args, **options):
        for entry in RECIPES:
            values = dict(entry)
            ingredients = values.pop('ingredients')
            recipe, created = Recipe.objects.get_or_create(title=values['title'], defaults=values)
            if created:
                RecipeIngredient.objects.bulk_create([RecipeIngredient(recipe=recipe, name=name, amount=amount) for name, amount in ingredients])
        demo, created = User.objects.get_or_create(username='demo', defaults={'first_name':'Alex', 'email':'demo@example.com'})
        if created:
            demo.set_password('FreshStart!2026')
            demo.save()
            Profile.objects.create(user=demo)
            for name, category, quantity, unit, days in DEMO_INVENTORY:
                Ingredient.objects.create(owner=demo, name=name, category=category, quantity=quantity, unit=unit, expires_on=timezone.localdate()+timedelta(days=days))
            self.stdout.write(self.style.SUCCESS('Demo account: demo / FreshStart!2026'))
        else:
            self.stdout.write('Demo account already exists; its password and inventory were preserved.')
        if not User.objects.filter(username='admin').exists():
            password = 'Fw!' + secrets.token_urlsafe(15)
            User.objects.create_superuser('admin', 'admin@example.com', password)
            self.stdout.write(self.style.SUCCESS(f'Administrator account: admin / {password}'))
            self.stdout.write('Save this password now. To change it later: python manage.py changepassword admin')
        else:
            self.stdout.write('Admin account already exists; its password was preserved.')
        self.stdout.write(self.style.SUCCESS(f'Ready: {Recipe.objects.count()} recipes. Sign in at http://127.0.0.1:8000/'))
