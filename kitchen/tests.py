import csv
import io
import json
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from .models import Favorite, Ingredient, Profile, Recipe, RecipeIngredient, ReminderDelivery, ShoppingItem
from .services import alerts_for, normalize, recipe_suggestions

class KitchenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alex = User.objects.create_user('alex', 'alex@example.com', 'TestKitchen!2026', first_name='Alex')
        cls.bob = User.objects.create_user('bob', 'bob@example.com', 'Different!2026')
        cls.admin = User.objects.create_superuser('admin', 'admin@example.com', 'AdminTest!2026')
        Profile.objects.create(user=cls.alex)
        Profile.objects.create(user=cls.bob)
        cls.recipe = Recipe.objects.create(title='Tomato eggs',description='Simple breakfast',category='vegetarian',minutes=10,servings=2,instructions=['Cook fully.'])
        RecipeIngredient.objects.create(recipe=cls.recipe,name='egg',amount='2')
        RecipeIngredient.objects.create(recipe=cls.recipe,name='tomato',amount='2')

    def setUp(self):
        self.client.force_login(self.alex)

    def item(self, name='tomatoes', days=2, owner=None, quantity=2):
        return Ingredient.objects.create(owner=owner or self.alex,name=name,category='vegetables',quantity=quantity,unit='pcs',expires_on=timezone.localdate()+timedelta(days=days))

    def post_json(self, url, payload):
        return self.client.post(url,json.dumps(payload),content_type='application/json')

    def test_new_account_gets_private_empty_kitchen(self):
        self.client.logout()
        response = self.client.post('/signup/',{'first_name':'Taylor','username':'taylor','email':'taylor@example.com','password1':'MyNewKitchen!774','password2':'MyNewKitchen!774'})
        self.assertRedirects(response,'/')
        user = User.objects.get(username='taylor')
        self.assertTrue(user.check_password('MyNewKitchen!774'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(self.client.get('/api/state/').json()['ingredients'],[])
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_duplicate_email_rejected(self):
        self.client.logout()
        response=self.client.post('/signup/',{'first_name':'Other','username':'other','email':'ALEX@example.com','password1':'MyNewKitchen!774','password2':'MyNewKitchen!774'})
        self.assertContains(response,'An account already uses this email address.')
        self.assertFalse(User.objects.filter(username='other').exists())

    def test_auth_required(self):
        self.client.logout()
        self.assertEqual(self.client.get('/api/state/').status_code,401)
        self.assertEqual(self.client.get('/').status_code,302)
        self.assertEqual(self.post_json('/api/ingredients/',{}).status_code,401)

    def test_login_and_post_only_logout(self):
        self.client.logout()
        self.assertRedirects(self.client.post('/login/',{'username':'alex','password':'TestKitchen!2026'}),'/')
        self.assertEqual(self.client.get('/logout/').status_code,405)
        self.assertRedirects(self.client.post('/logout/'),'/login/')

    def test_login_throttling(self):
        self.client.logout()
        for _ in range(10):
            self.client.post('/login/',{'username':'alex','password':'wrong'})
        response=self.client.post('/login/',{'username':'alex','password':'TestKitchen!2026'})
        self.assertContains(response,'Too many sign-in attempts.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_private_inventory_and_no_foreign_modifications(self):
        own=self.item()
        other=self.item(owner=self.bob)
        state=self.client.get('/api/state/').json()
        self.assertEqual([i['id'] for i in state['ingredients']],[own.pk])
        self.assertEqual(self.client.delete(f'/api/ingredients/{other.pk}/').status_code,404)
        self.assertEqual(self.client.put(f'/api/ingredients/{other.pk}/',json.dumps({}),content_type='application/json').status_code,404)
        self.assertTrue(Ingredient.objects.filter(pk=other.pk).exists())

    def test_ingredient_create_edit_and_delete(self):
        payload={'name':'  Cherry   Tomatoes  ','category':'vegetables','quantity':'200','unit':'g','expires_on':timezone.localdate().isoformat()}
        response=self.post_json('/api/ingredients/',payload)
        self.assertEqual(response.status_code,201)
        item=Ingredient.objects.get(pk=response.json()['id'])
        self.assertEqual(item.name,'cherry tomatoes')
        self.assertEqual(item.owner,self.alex)
        payload['quantity']='300'
        self.assertEqual(self.client.put(f'/api/ingredients/{item.pk}/',json.dumps(payload),content_type='application/json').status_code,200)
        item.refresh_from_db()
        self.assertEqual(item.quantity,300)
        self.assertEqual(self.client.delete(f'/api/ingredients/{item.pk}/').status_code,200)
        self.assertFalse(Ingredient.objects.filter(pk=item.pk).exists())

    def test_invalid_ingredient_rejected(self):
        payload={'name':'milk','category':'dairy','quantity':'0','unit':'ml','expires_on':'not-a-date'}
        response=self.post_json('/api/ingredients/',payload)
        self.assertEqual(response.status_code,400)
        self.assertIn('quantity',response.json()['errors'])
        self.assertIn('expires_on',response.json()['errors'])
        self.assertFalse(Ingredient.objects.exists())

    def test_smallest_supported_quantity_is_valid(self):
        payload={'name':'saffron','category':'pantry','quantity':'0.01','unit':'g','expires_on':timezone.localdate().isoformat()}
        self.assertEqual(self.post_json('/api/ingredients/',payload).status_code,201)

    def test_recipe_instructions_reject_invalid_shapes(self):
        for invalid in [{},[''],[4],'Cook food']:
            self.recipe.instructions=invalid
            with self.assertRaises(ValidationError):
                self.recipe.full_clean()
        self.recipe.instructions=['Cook fully and serve.']
        self.recipe.full_clean()

    def test_bad_json_and_wrong_http_methods(self):
        self.assertEqual(self.client.post('/api/ingredients/','{',content_type='application/json').status_code,400)
        self.assertEqual(self.post_json('/api/ingredients/',[]).status_code,400)
        self.assertEqual(self.client.get('/api/ingredients/').status_code,405)

    def test_matching_normalizes_aliases_and_excludes_expired(self):
        self.item('cherry tomatoes',days=1)
        eggs=self.item('eggs',days=-1)
        result=recipe_suggestions(self.alex)[0]
        self.assertEqual(result['matched'],1)
        self.assertFalse(result['ready'])
        self.assertEqual(result['missing'],['egg'])
        eggs.expires_on=timezone.localdate()
        eggs.save()
        result=recipe_suggestions(self.alex)[0]
        self.assertEqual(result['match'],100)
        self.assertTrue(result['ready'])
        self.assertIn('tomato',result['use_soon'])

    def test_foreign_ingredients_do_not_match(self):
        self.item('eggs',owner=self.bob)
        self.item('tomatoes',owner=self.bob)
        self.assertEqual(recipe_suggestions(self.alex)[0]['matched'],0)

    def test_expiry_threshold_boundary(self):
        expired=self.item('old',days=-1)
        today=self.item('today',days=0)
        edge=self.item('edge',days=3)
        self.item('fresh',days=4)
        self.assertEqual(set(alerts_for(self.alex).values_list('id',flat=True)),{expired.pk,today.pk,edge.pk})

    def test_favorites_toggle_and_are_private(self):
        url=f'/api/recipes/{self.recipe.pk}/favorite/'
        self.assertTrue(self.post_json(url,{}).json()['favorite'])
        self.assertEqual(Favorite.objects.filter(user=self.alex).count(),1)
        self.client.force_login(self.bob)
        self.assertFalse(self.client.get('/api/state/').json()['recipes'][0]['favorite'])
        self.client.force_login(self.alex)
        self.assertFalse(self.post_json(url,{}).json()['favorite'])

    def test_shopping_list_deduplicates_and_is_private(self):
        self.assertEqual(self.post_json('/api/shopping/',{'names':['Tomatoes','tomato']}).status_code,201)
        self.assertEqual(ShoppingItem.objects.filter(owner=self.alex).count(),1)
        item=ShoppingItem.objects.get(owner=self.alex)
        self.client.force_login(self.bob)
        self.assertEqual(self.client.get('/api/state/').json()['shopping'],[])
        self.assertEqual(self.client.delete(f'/api/shopping/{item.pk}/').status_code,404)
        self.client.force_login(self.alex)
        self.assertEqual(self.client.put(f'/api/shopping/{item.pk}/',json.dumps({'checked':True}),content_type='application/json').status_code,200)
        item.refresh_from_db()
        self.assertTrue(item.checked)

    def test_shopping_validation(self):
        for names in ['',[],[None],['x'*81]]:
            self.assertEqual(self.post_json('/api/shopping/',{'names':names}).status_code,400)

    def test_settings_validation_and_persistence(self):
        url='/api/settings/'
        self.assertEqual(self.client.put(url,json.dumps({'reminder_days':0,'email_reminders':True}),content_type='application/json').status_code,400)
        self.assertEqual(self.client.put(url,json.dumps({'reminder_days':7,'email_reminders':True}),content_type='application/json').status_code,200)
        self.assertEqual(self.client.get('/api/state/').json()['settings'],{'reminder_days':7,'email_reminders':True})

    def test_csv_is_private_and_neutralizes_formula(self):
        self.item('=HYPERLINK("evil")')
        self.item('private_bob',owner=self.bob)
        response=self.client.get('/api/export/')
        text=response.content.decode()
        rows=list(csv.reader(io.StringIO(text)))
        self.assertTrue(rows[1][0].startswith("'="))
        self.assertNotIn('private_bob',text)

    def test_csrf_protects_mutations(self):
        client=Client(enforce_csrf_checks=True)
        client.force_login(self.alex)
        self.assertEqual(client.post('/api/ingredients/',json.dumps({}),content_type='application/json').status_code,403)

    def test_regular_user_denied_admin_and_superuser_can_manage_all(self):
        self.item(owner=self.bob)
        self.assertEqual(self.client.get('/admin/').status_code,302)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/admin/').status_code,200)
        self.assertContains(self.client.get('/admin/kitchen/ingredient/'),'tomatoes')
        self.assertEqual(self.client.get('/admin/auth/user/').status_code,200)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_daily_digest_is_opt_in_and_deduplicated(self):
        self.item('tomatoes',days=1)
        self.item('eggs',days=10)
        call_command('send_expiry_reminders',stdout=io.StringIO())
        self.assertEqual(len(mail.outbox),0)
        Profile.objects.filter(user=self.alex).update(email_reminders=True)
        call_command('send_expiry_reminders',stdout=io.StringIO())
        call_command('send_expiry_reminders',stdout=io.StringIO())
        self.assertEqual(len(mail.outbox),1)
        self.assertIn('tomatoes',mail.outbox[0].body)
        self.assertNotIn('eggs',mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to,['alex@example.com'])
        self.assertEqual(ReminderDelivery.objects.count(),1)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_failed_email_can_be_retried(self):
        self.item()
        Profile.objects.filter(user=self.alex).update(email_reminders=True)
        with patch('kitchen.reminders.send_mail',side_effect=ConnectionError):
            call_command('send_expiry_reminders',stdout=io.StringIO(),stderr=io.StringIO())
        self.assertFalse(ReminderDelivery.objects.exists())
        call_command('send_expiry_reminders',stdout=io.StringIO())
        self.assertEqual(len(mail.outbox),1)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_inactive_users_receive_no_emails(self):
        self.item()
        Profile.objects.filter(user=self.alex).update(email_reminders=True)
        User.objects.filter(pk=self.alex.pk).update(is_active=False)
        call_command('send_expiry_reminders',stdout=io.StringIO())
        self.assertEqual(len(mail.outbox),0)

    def test_demo_seed_is_safe_to_repeat(self):
        output=io.StringIO()
        call_command('seed_demo',stdout=output)
        demo=User.objects.get(username='demo')
        count=demo.ingredients.count()
        demo.set_password('KeepMyPassword!2026')
        demo.save()
        call_command('seed_demo',stdout=io.StringIO())
        demo.refresh_from_db()
        self.assertTrue(demo.check_password('KeepMyPassword!2026'))
        self.assertEqual(demo.ingredients.count(),count)
        self.assertEqual(Recipe.objects.count(),13)
