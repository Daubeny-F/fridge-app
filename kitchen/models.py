from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

CATEGORIES = [('vegetables', 'Vegetables'), ('fruit', 'Fruit'), ('dairy', 'Dairy & eggs'),
              ('protein', 'Meat & protein'), ('grains', 'Grains & pasta'), ('pantry', 'Pantry')]
UNITS = [('g', 'g'), ('kg', 'kg'), ('ml', 'ml'), ('l', 'l'), ('pcs', 'pcs'), ('pack', 'pack')]

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    reminder_days = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(14)])
    email_reminders = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

class Ingredient(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ingredients')
    name = models.CharField(max_length=80)
    category = models.CharField(max_length=15, choices=CATEGORIES, default='vegetables')
    quantity = models.DecimalField(max_digits=9, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    unit = models.CharField(max_length=5, choices=UNITS, default='g')
    expires_on = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['expires_on', 'name']
        indexes = [models.Index(fields=['owner', 'expires_on'])]
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0), name='positive_ingredient_quantity')]

    @property
    def days_left(self):
        return (self.expires_on - timezone.localdate()).days

    def __str__(self):
        return f'{self.name} ({self.owner.username})'

class Recipe(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=250)
    category = models.CharField(max_length=20, choices=[('vegetarian', 'Vegetarian'), ('vegan', 'Vegan'), ('protein', 'High protein')])
    minutes = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    servings = models.PositiveSmallIntegerField(default=2, validators=[MinValueValidator(1)])
    art = models.CharField(max_length=20, default='salad', choices=[('salad', 'Salad'), ('pasta', 'Pasta'), ('bowl', 'Bowl'), ('toast', 'Toast'), ('soup', 'Soup'), ('eggs', 'Eggs')])
    instructions = models.JSONField(default=list, help_text='JSON list of cooking steps, e.g. ["Chop vegetables.", "Cook for 10 minutes."]')

    def clean(self):
        super().clean()
        if not isinstance(self.instructions, list) or not self.instructions or any(not isinstance(step, str) or not step.strip() for step in self.instructions):
            raise ValidationError({'instructions': 'Enter a nonempty JSON list of cooking step strings.'})

    def __str__(self):
        return self.title

class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    name = models.CharField(max_length=80, help_text='Use a singular ingredient name, for example tomato.')
    amount = models.CharField(max_length=60, help_text='For example: 200 g or 2 pieces')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['recipe', 'name'], name='unique_recipe_ingredient')]

    def __str__(self):
        return f'{self.name} — {self.amount}'

class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'recipe'], name='unique_favorite')]

class ShoppingItem(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shopping_items')
    name = models.CharField(max_length=80)
    checked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['checked', '-created_at']
        constraints = [models.UniqueConstraint(fields=['owner', 'name'], name='unique_shopping_item')]

class ReminderDelivery(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    sent_on = models.DateField(default=timezone.localdate)
    ingredient_count = models.PositiveIntegerField()
    channel = models.CharField(max_length=7, choices=[('email', 'Email'), ('preview', 'Local preview')], default='email')
    recipient = models.EmailField(blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='requested_reminders')
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name_plural = 'reminder deliveries'
        constraints = [models.UniqueConstraint(fields=['user', 'sent_on', 'channel'], name='one_digest_per_channel_per_day')]

class LoginAttempt(models.Model):
    key = models.CharField(max_length=64, unique=True)
    failures = models.PositiveIntegerField(default=0)
    window_started = models.DateTimeField(default=timezone.now)
