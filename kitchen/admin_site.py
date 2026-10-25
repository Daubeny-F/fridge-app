from django.contrib.admin import AdminSite
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.core import signing
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseNotAllowed
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone


class FridgewiseAdminSite(AdminSite):
    index_template = 'admin/kitchen_index.html'

    def get_urls(self):
        return [
            path('fridges/', self.admin_view(self.fridges), name='kitchen_fridges'),
            path('fridges/<int:user_id>/', self.admin_view(self.fridge), name='kitchen_fridge'),
            path('fridges/<int:user_id>/reminder/', self.admin_view(self.reminder), name='kitchen_fridge_reminder'),
        ] + super().get_urls()

    def index(self, request, extra_context=None):
        from .models import Ingredient, Recipe
        context = dict(extra_context or {})
        if request.user.has_perm('kitchen.view_ingredient'):
            context['kitchen_summary'] = {
                'users': get_user_model().objects.count(),
                'ingredients': Ingredient.objects.count(),
                'expired': Ingredient.objects.filter(expires_on__lt=timezone.localdate()).count(),
            }
        if request.user.has_perm('kitchen.view_recipe'):
            context['recipe_count'] = Recipe.objects.count()
        return super().index(request, extra_context=context)

    def fridges(self, request):
        if not request.user.has_perm('kitchen.view_ingredient'):
            raise PermissionDenied
        query = request.GET.get('q', '').strip()[:150]
        users = get_user_model().objects.annotate(
            ingredient_count=Count('ingredients'),
            expired_count=Count('ingredients', filter=Q(ingredients__expires_on__lt=timezone.localdate())),
        ).order_by('username')
        if query:
            users = users.filter(Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query))
        return TemplateResponse(request, 'admin/fridges.html', {
            **self.each_context(request), 'title': 'Users’ fridges', 'query': query,
            'page_obj': Paginator(users, 25).get_page(request.GET.get('page')),
        })

    def fridge(self, request, user_id):
        if not request.user.has_perm('kitchen.view_ingredient'):
            raise PermissionDenied
        owner = get_object_or_404(get_user_model(), pk=user_id)
        query = request.GET.get('q', '').strip()[:80]
        items = owner.ingredients.all()
        summary = items.aggregate(
            total=Count('pk'),
            expired=Count('pk', filter=Q(expires_on__lt=timezone.localdate())),
        )
        if query:
            items = items.filter(name__icontains=query)
        return TemplateResponse(request, 'admin/fridge.html', {
            **self.each_context(request), 'title': f'{owner.username}’s fridge',
            'owner': owner, 'query': query, 'summary': summary,
            'page_obj': Paginator(items, 50).get_page(request.GET.get('page')),
            'can_edit': request.user.has_perm('kitchen.change_ingredient'),
            'can_add': request.user.has_perm('kitchen.add_ingredient'),
            'can_send': request.user.has_perm('kitchen.add_reminderdelivery'),
        })

    def reminder(self, request, user_id):
        from .reminders import prepare_reminder, deliver_reminder, ReminderUnavailable, ReminderDeliveryFailed
        if not (request.user.has_perm('kitchen.view_ingredient') and request.user.has_perm('kitchen.add_reminderdelivery')):
            raise PermissionDenied
        if request.method not in {'GET', 'POST'}:
            return HttpResponseNotAllowed(['GET', 'POST'])
        owner = get_object_or_404(get_user_model(), pk=user_id)
        if request.method == 'POST':
            try:
                confirmation = signing.loads(request.POST.get('confirmation', ''), salt='fridgewise-email-reminder', max_age=600)
                if confirmation.get('user') != owner.pk or confirmation.get('actor') != request.user.pk:
                    raise signing.BadSignature
            except (signing.BadSignature, TypeError, ValueError, AttributeError):
                messages.error(request, 'This email preview expired or is invalid. Review the message again before sending.')
                return redirect('admin:kitchen_fridge_reminder', user_id=owner.pk)
            try:
                receipt = deliver_reminder(owner, requested_by=request.user, expected_fingerprint=confirmation.get('fingerprint', ''))
            except (ReminderUnavailable, ReminderDeliveryFailed) as error:
                messages.error(request, str(error))
                return redirect('admin:kitchen_fridge_reminder', user_id=owner.pk)
            if receipt.channel == 'preview':
                messages.success(request, 'Email preview saved to the local outbox folder. No email was sent. Restart with start-gmail.ps1 to send through Gmail.')
            else:
                messages.success(request, f'Reminder submitted to the mail server for {receipt.recipient}. Check the recipient’s inbox or spam folder.')
            return redirect('admin:kitchen_fridge', user_id=owner.pk)
        prepared = prepare_reminder(owner)
        confirmation = signing.dumps({'user': owner.pk, 'actor': request.user.pk, 'fingerprint': prepared['fingerprint']}, salt='fridgewise-email-reminder')
        return TemplateResponse(request, 'admin/reminder.html', {
            **self.each_context(request), 'title': 'Review expiry reminder', 'owner': owner,
            'reminder': prepared, 'confirmation': confirmation,
        })
