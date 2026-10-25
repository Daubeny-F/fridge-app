import tempfile
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core import mail
from django.core.management import call_command, CommandError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Ingredient, Profile, ReminderDelivery
from .reminders import FILE_BACKEND, SMTP_BACKEND, deliver_reminder


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ManualReminderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('admin', 'admin@example.com', 'TestAdmin!2026')
        cls.user = User.objects.create_user('alex', 'alex@example.com', 'TestUser!2026', first_name='Alex')
        cls.staff = User.objects.create_user('viewer', password='TestStaff!2026', is_staff=True)
        cls.staff.user_permissions.add(Permission.objects.get(codename='view_ingredient'))
        Profile.objects.create(user=cls.user, email_reminders=True, reminder_days=3)
        Ingredient.objects.create(owner=cls.user, name='tomatoes', category='vegetables', quantity=200, unit='g', expires_on=timezone.localdate()+timedelta(days=1))
        Ingredient.objects.create(owner=cls.user, name='milk', category='dairy', quantity=1, unit='l', expires_on=timezone.localdate()+timedelta(days=9))
        Ingredient.objects.create(owner=cls.admin, name='private_admin_food', category='pantry', quantity=1, unit='pcs', expires_on=timezone.localdate())

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse('admin:kitchen_fridge_reminder', args=[self.user.pk])

    def confirmation(self):
        return self.client.get(self.url).context['confirmation']

    def test_preview_get_never_sends_and_only_includes_target_due_food(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'alex@example.com')
        self.assertContains(response, 'tomatoes')
        self.assertNotContains(response, 'milk')
        self.assertNotContains(response, 'private_admin_food')
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(ReminderDelivery.objects.exists())

    def test_manual_send_tracks_recipient_actor_and_daily_deduplication(self):
        token = self.confirmation()
        response = self.client.post(self.url, {'confirmation': token})
        self.assertRedirects(response, reverse('admin:kitchen_fridge', args=[self.user.pk]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['alex@example.com'])
        receipt = ReminderDelivery.objects.get()
        self.assertEqual(receipt.requested_by, self.admin)
        self.assertEqual(receipt.recipient, 'alex@example.com')
        self.assertEqual(receipt.channel, 'email')
        self.assertEqual(receipt.ingredient_count, 1)
        self.client.post(self.url, {'confirmation': token})
        self.assertEqual(len(mail.outbox), 1)

    def test_send_ignores_payload_recipient(self):
        self.client.post(self.url, {'confirmation': self.confirmation(), 'recipient': 'someoneelse@example.com'})
        self.assertEqual(mail.outbox[0].to, ['alex@example.com'])

    def test_normal_users_and_staff_viewers_cannot_send_or_preview(self):
        for user in [self.user, self.staff]:
            self.client.force_login(user)
            expected = 302 if user == self.user else 403
            self.assertEqual(self.client.get(self.url).status_code, expected)
            self.assertEqual(self.client.post(self.url, {}).status_code, expected)
        self.assertEqual(len(mail.outbox), 0)

    def test_post_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(self.url, {'confirmation': self.confirmation()}).status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_and_expired_confirmation_do_not_send(self):
        response = self.client.post(self.url, {'confirmation': 'tampered'}, follow=True)
        self.assertContains(response, 'preview expired or is invalid')
        token = self.confirmation()
        future = time.time()+601
        with patch('django.core.signing.time.time', return_value=future):
            response = self.client.post(self.url, {'confirmation': token}, follow=True)
            self.assertContains(response, 'preview expired or is invalid')
        self.assertEqual(len(mail.outbox), 0)

    def test_confirmation_cannot_target_another_user(self):
        token = self.confirmation()
        url = reverse('admin:kitchen_fridge_reminder', args=[self.admin.pk])
        self.client.post(url, {'confirmation': token})
        self.assertEqual(len(mail.outbox), 0)

    def test_changed_recipient_requires_a_new_preview(self):
        token = self.confirmation()
        User.objects.filter(pk=self.user.pk).update(email='updated@example.com')
        response = self.client.post(self.url, {'confirmation': token}, follow=True)
        self.assertContains(response, 'changed. Review the updated message')
        self.assertEqual(len(mail.outbox), 0)

    def test_changed_fridge_requires_a_new_preview(self):
        token = self.confirmation()
        Ingredient.objects.filter(owner=self.user, name='tomatoes').update(quantity=400)
        response = self.client.post(self.url, {'confirmation': token}, follow=True)
        self.assertContains(response, 'changed. Review the updated message')
        self.assertEqual(len(mail.outbox), 0)

    def test_opted_out_inactive_and_missing_email_are_blocked(self):
        cases = [('opt_out', 'has not enabled'), ('inactive', 'inactive'), ('email', 'valid email')]
        for kind, reason in cases:
            with self.subTest(kind=kind):
                Profile.objects.filter(user=self.user).update(email_reminders=(kind != 'opt_out'))
                User.objects.filter(pk=self.user.pk).update(is_active=(kind != 'inactive'), email='' if kind == 'email' else 'alex@example.com')
                response = self.client.get(self.url)
                self.assertContains(response, reason)
                self.client.post(self.url, {'confirmation': response.context['confirmation']})
        self.assertEqual(len(mail.outbox), 0)

    def test_no_due_food_is_blocked(self):
        Ingredient.objects.filter(owner=self.user).update(expires_on=timezone.localdate()+timedelta(days=30))
        response = self.client.get(self.url)
        self.assertContains(response, 'No ingredients fall within')
        self.client.post(self.url, {'confirmation': response.context['confirmation']})
        self.assertEqual(len(mail.outbox), 0)

    def test_failure_is_sanitized_and_can_be_retried(self):
        token = self.confirmation()
        with patch('kitchen.reminders.send_mail', side_effect=ConnectionError('SECRET_PROVIDER_REPLY')):
            response = self.client.post(self.url, {'confirmation': token}, follow=True)
        self.assertContains(response, 'Could not send the reminder')
        self.assertNotContains(response, 'SECRET_PROVIDER_REPLY')
        self.assertFalse(ReminderDelivery.objects.exists())
        self.client.post(self.url, {'confirmation': self.confirmation()})
        self.assertEqual(len(mail.outbox), 1)

    def test_zero_backend_count_is_not_success(self):
        with patch('kitchen.reminders.send_mail', return_value=0):
            response = self.client.post(self.url, {'confirmation': self.confirmation()}, follow=True)
        self.assertContains(response, 'did not accept')
        self.assertFalse(ReminderDelivery.objects.exists())

    def test_local_preview_has_separate_receipt_and_does_not_block_email(self):
        # Use an explicitly workspace-local temporary path on restricted Windows hosts.
        root = Path(__file__).resolve().parent.parent / 'artifacts'
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            with override_settings(EMAIL_BACKEND=FILE_BACKEND, EMAIL_FILE_PATH=directory):
                response = self.client.post(self.url, {'confirmation': self.confirmation()}, follow=True)
                self.assertContains(response, 'No email was sent')
                self.assertEqual(len(list(Path(directory).glob('*.log'))), 1)
                self.assertEqual(ReminderDelivery.objects.get().channel, 'preview')
        self.client.post(self.url, {'confirmation': self.confirmation()})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(ReminderDelivery.objects.count(), 2)

    @override_settings(EMAIL_BACKEND=SMTP_BACKEND, EMAIL_HOST='', EMAIL_HOST_USER='', EMAIL_HOST_PASSWORD='')
    def test_unconfigured_smtp_shows_setup_instructions(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'start-gmail.ps1')
        self.assertContains(response, 'Email is not configured')

    @override_settings(EMAIL_BACKEND=SMTP_BACKEND, EMAIL_HOST='smtp.gmail.com', EMAIL_HOST_USER='sender@gmail.com', EMAIL_HOST_PASSWORD='test-only-placeholder')
    def test_smtp_rejects_demo_recipient_without_connecting(self):
        with patch('kitchen.reminders.send_mail') as sending:
            response = self.client.get(self.url)
            self.assertContains(response, 'demo email address')
            self.client.post(self.url, {'confirmation': response.context['confirmation']})
            sending.assert_not_called()

    def test_background_watch_option_removed(self):
        with self.assertRaises(CommandError):
            call_command('send_expiry_reminders', '--watch')
