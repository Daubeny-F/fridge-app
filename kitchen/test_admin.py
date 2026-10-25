from datetime import timedelta

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import AdminRecipeForm
from .models import Ingredient, Recipe
from .services import recipe_suggestions


class AdminPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('admin', 'admin@example.com', 'TestAdmin!2026')
        cls.alex = User.objects.create_user('alex', first_name='Alex', password='TestAlex!2026')
        cls.bob = User.objects.create_user('bob', first_name='Bob', password='TestBob!2026')
        cls.staff = User.objects.create_user('staff', password='TestStaff!2026', is_staff=True)
        for user, name, days in [(cls.alex, 'tomatoes', 2), (cls.bob, 'broccoli', -1)]:
            Ingredient.objects.create(owner=user, name=name, quantity=200, unit='g', category='vegetables', expires_on=timezone.localdate()+timedelta(days=days))

    def setUp(self):
        self.client.force_login(self.admin)

    def recipe_payload(self, ingredient_count=1):
        payload = {
            'title': 'Simple tomato salad', 'description': 'A bright kitchen staple.',
            'category': 'vegan', 'minutes': 10, 'servings': 2, 'art': 'salad',
            'instructions': 'Wash the tomatoes.\n\nSlice, season, and serve.',
            'ingredients-TOTAL_FORMS': str(ingredient_count), 'ingredients-INITIAL_FORMS': '0',
            'ingredients-MIN_NUM_FORMS': '1', 'ingredients-MAX_NUM_FORMS': '1000', '_save': 'Save',
        }
        if ingredient_count:
            payload.update({'ingredients-0-name': 'Tomatoes', 'ingredients-0-amount': '200 g'})
        return payload

    def test_dashboard_links_to_fridges_and_recipe_creation(self):
        response = self.client.get(reverse('admin:index'))
        self.assertContains(response, 'Browse users’ fridges')
        self.assertContains(response, reverse('admin:kitchen_recipe_add'))
        self.assertContains(response, 'Ingredients in all fridges')

    def test_admin_can_browse_search_and_open_each_fridge(self):
        response = self.client.get(reverse('admin:kitchen_fridges'))
        self.assertContains(response, reverse('admin:kitchen_fridge', args=[self.alex.pk]))
        self.assertContains(response, reverse('admin:kitchen_fridge', args=[self.bob.pk]))
        self.assertEqual(response.context['page_obj'].paginator.count, 4)
        filtered = self.client.get(reverse('admin:kitchen_fridges'), {'q': 'Alex'})
        self.assertEqual([u.username for u in filtered.context['page_obj']], ['alex'])
        detail = self.client.get(reverse('admin:kitchen_fridge', args=[self.alex.pk]))
        self.assertContains(detail, 'tomatoes')
        self.assertNotContains(detail, 'broccoli')
        self.assertEqual(detail.context['summary']['total'], 1)
        expired = self.client.get(reverse('admin:kitchen_fridge', args=[self.bob.pk]))
        self.assertContains(expired, 'Past its date')

    def test_empty_fridge_and_missing_user(self):
        response = self.client.get(reverse('admin:kitchen_fridge', args=[self.admin.pk]))
        self.assertContains(response, 'This user’s fridge is empty.')
        self.assertEqual(self.client.get(reverse('admin:kitchen_fridge', args=[99999])).status_code, 404)

    def test_fridges_require_staff_and_ingredient_permission(self):
        urls = [reverse('admin:kitchen_fridges'), reverse('admin:kitchen_fridge', args=[self.alex.pk])]
        self.client.force_login(self.alex)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.staff)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.staff.user_permissions.add(Permission.objects.get(codename='view_ingredient'))
        response = self.client.get(urls[1])
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Edit ingredient →')
        self.assertNotContains(response, 'Add ingredient for this user')

    def test_admin_adds_recipe_with_plain_text_steps_and_it_matches(self):
        response = self.client.post(reverse('admin:kitchen_recipe_add'), self.recipe_payload())
        self.assertRedirects(response, reverse('admin:kitchen_recipe_changelist'))
        recipe = Recipe.objects.get(title='Simple tomato salad')
        self.assertEqual(recipe.instructions, ['Wash the tomatoes.', 'Slice, season, and serve.'])
        self.assertEqual(recipe.ingredients.get().name, 'tomato')
        self.assertTrue(recipe_suggestions(self.alex)[0]['ready'])
        self.assertFalse(recipe_suggestions(self.bob)[0]['ready'])
        form = AdminRecipeForm(instance=recipe)
        self.assertEqual(form.initial['instructions'], 'Wash the tomatoes.\nSlice, season, and serve.')

    def test_recipe_requires_at_least_one_ingredient(self):
        response = self.client.post(reverse('admin:kitchen_recipe_add'), self.recipe_payload(ingredient_count=0))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please submit at least 1 form.')
        self.assertFalse(Recipe.objects.exists())

    def test_duplicate_ingredient_aliases_are_rejected(self):
        payload = self.recipe_payload(ingredient_count=2)
        payload.update({'ingredients-1-name': 'tomato', 'ingredients-1-amount': '300 g'})
        response = self.client.post(reverse('admin:kitchen_recipe_add'), payload)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Recipe.objects.exists())

    def test_regular_user_cannot_create_recipe(self):
        self.client.force_login(self.alex)
        response = self.client.post(reverse('admin:kitchen_recipe_add'), self.recipe_payload())
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Recipe.objects.exists())
