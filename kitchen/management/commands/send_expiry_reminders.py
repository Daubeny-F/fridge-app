from django.core.management.base import BaseCommand
from kitchen.models import Profile
from kitchen.reminders import deliver_reminder, ReminderDeliveryFailed, ReminderUnavailable

class Command(BaseCommand):
    help = 'Manually send one digest to each eligible opted-in user. No watcher or automatic scheduling.'

    def handle(self, *args, **options):
        sent = 0
        for profile in Profile.objects.select_related('user').filter(email_reminders=True, user__is_active=True).exclude(user__email=''):
            try:
                deliver_reminder(profile.user)
                sent += 1
            except ReminderUnavailable:
                continue
            except ReminderDeliveryFailed:
                self.stderr.write(f'Delivery failed for user #{profile.user.pk}. Check email configuration; delivery can be retried.')
        self.stdout.write(f'{sent} reminder(s) processed. In local mode these are previews, not sent emails. Already-processed and ineligible users skipped.')
