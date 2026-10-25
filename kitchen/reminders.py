"""Compose and send the same consent-aware digest from the admin button or manual CLI."""
import hashlib
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from .models import ReminderDelivery
from .services import alerts_for, profile_for

SUBJECT = 'A little fridge heads-up · Fridgewise'
FILE_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
SMTP_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
MEMORY_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'


class ReminderUnavailable(Exception):
    pass


class ReminderDeliveryFailed(Exception):
    pass


def prepare_reminder(user):
    profile = profile_for(user)
    items = list(alerts_for(user))
    preview = settings.EMAIL_BACKEND == FILE_BACKEND
    channel = 'preview' if preview else 'email'
    recipient = user.email.strip()
    lines = []
    for item in items:
        days = item.days_left
        note = 'PAST ITS DATE — check and discard if needed' if days < 0 else 'expires today' if days == 0 else f'expires in {days} day{"s" if days != 1 else ""}'
        lines.append(f'- {item.name}: {item.quantity} {item.unit} — {note} ({item.expires_on})')
    body = f'Hi {user.first_name or user.username},\n\nA little heads-up from your fridge:\n\n' + '\n'.join(lines) + '\n\nOpen Fridgewise to find recipe ideas and update your inventory.\nDates are reminders: check food condition before cooking.\n\nYour Fridgewise kitchen'
    reason = ''
    if not user.is_active:
        reason = 'This account is inactive.'
    elif not profile.email_reminders:
        reason = 'This user has not enabled email reminders. They can allow them in Settings.'
    else:
        try:
            validate_email(recipient)
        except ValidationError:
            reason = 'Add a valid email address to this user’s account before sending.'
    if not reason and not items:
        reason = 'No ingredients fall within this user’s expiry reminder window.'
    if not reason and settings.EMAIL_BACKEND == SMTP_BACKEND:
        if not all([settings.EMAIL_HOST, settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD]):
            reason = 'Email is not configured. Restart with start-gmail.ps1 to enter the sender Gmail address and App Password.'
        elif recipient.rsplit('@', 1)[-1].lower() in {'example.com', 'example.net', 'example.org', 'localhost'} or recipient.lower().endswith(('.test', '.invalid')):
            reason = 'This is a demo email address. Set the user’s real email address in Admin → Users.'
    if not reason and settings.EMAIL_BACKEND not in {FILE_BACKEND, SMTP_BACKEND, MEMORY_BACKEND}:
        reason = 'This email backend is unsupported. Choose local previews or Gmail SMTP.'
    receipt = ReminderDelivery.objects.filter(user=user, sent_on=timezone.localdate(), channel=channel).first()
    if not reason and receipt:
        reason = 'A local preview has already been saved for this user today.' if preview else 'An email reminder has already been sent to this user today.'
    snapshot = [user.pk, recipient, user.is_active, profile.email_reminders, profile.reminder_days,
                timezone.localdate().isoformat(), settings.EMAIL_BACKEND, settings.EMAIL_HOST,
                settings.EMAIL_HOST_USER, settings.DEFAULT_FROM_EMAIL, body]
    fingerprint = hashlib.sha256(json.dumps(snapshot, ensure_ascii=False).encode()).hexdigest()
    return {'recipient': recipient, 'subject': SUBJECT, 'body': body, 'items': items,
            'is_preview': preview, 'channel': channel, 'reason': reason,
            'fingerprint': fingerprint, 'receipt': receipt, 'reminder_days': profile.reminder_days,
            'sender': settings.DEFAULT_FROM_EMAIL}


def deliver_reminder(user, requested_by=None, expected_fingerprint=None):
    try:
        with transaction.atomic():
            prepared = prepare_reminder(user)
            if expected_fingerprint is not None and expected_fingerprint != prepared['fingerprint']:
                raise ReminderUnavailable('The recipient, fridge, or email settings changed. Review the updated message before sending.')
            if prepared['reason']:
                raise ReminderUnavailable(prepared['reason'])
            receipt, created = ReminderDelivery.objects.get_or_create(
                user=user, sent_on=timezone.localdate(), channel=prepared['channel'],
                defaults={'ingredient_count': len(prepared['items']), 'recipient': prepared['recipient'], 'requested_by': requested_by},
            )
            if not created:
                raise ReminderUnavailable('This user’s reminder was already processed today.')
            sent = send_mail(prepared['subject'], prepared['body'], prepared['sender'], [prepared['recipient']], fail_silently=False)
            if sent != 1:
                raise ReminderDeliveryFailed('The mail backend did not accept the message. No successful delivery was recorded.')
            return receipt
    except (ReminderUnavailable, ReminderDeliveryFailed):
        raise
    except Exception as error:
        # Never expose SMTP replies, credentials, or message contents in the UI/logs.
        raise ReminderDeliveryFailed('Could not send the reminder. Check the Gmail App Password, sender settings, and network connection, then try again. No successful delivery was recorded.') from error
