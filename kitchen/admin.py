from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.html import format_html
from .forms import AdminRecipeForm, AdminRecipeIngredientForm
from .models import Favorite, Ingredient, Profile, Recipe, RecipeIngredient, ReminderDelivery, ShoppingItem

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'quantity', 'unit', 'expires_on', 'category']
    list_filter = ['category', 'expires_on', 'owner']
    search_fields = ['name', 'owner__username']
    autocomplete_fields = ['owner']
    list_select_related = ['owner']

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    form = AdminRecipeIngredientForm
    extra = 1
    min_num = 1

    def get_formset(self, request, obj=None, **kwargs):
        kwargs['validate_min'] = True
        return super().get_formset(request, obj, **kwargs)

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    form = AdminRecipeForm
    list_display = ['title', 'category', 'minutes', 'servings']
    list_filter = ['category']
    search_fields = ['title']
    inlines = [RecipeIngredientInline]
    fieldsets = [
        ('Recipe details', {'fields': ['title', 'description', 'category', ('minutes', 'servings'), 'art']}),
        ('How to cook it', {'fields': ['instructions']}),
    ]
    save_on_top = True


admin.site.unregister(User)

@admin.register(User)
class KitchenUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'is_staff', 'is_active', 'view_fridge']
    readonly_fields = [*UserAdmin.readonly_fields, 'view_fridge']
    fieldsets = (*UserAdmin.fieldsets, ('Kitchen', {'fields': ['view_fridge']}))

    @admin.display(description='Fridge')
    def view_fridge(self, obj):
        return format_html('<a href="{}">View fridge</a>', reverse('admin:kitchen_fridge', args=[obj.pk]))

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'reminder_days', 'email_reminders']

@admin.register(ShoppingItem)
class ShoppingAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'checked']
    list_filter = ['checked', 'owner']

@admin.register(ReminderDelivery)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ['user', 'sent_on', 'channel', 'recipient', 'ingredient_count', 'requested_by']
    list_filter = ['channel', 'sent_on']
    readonly_fields = ['user', 'sent_on', 'channel', 'recipient', 'ingredient_count', 'requested_by', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

admin.site.register(Favorite)
