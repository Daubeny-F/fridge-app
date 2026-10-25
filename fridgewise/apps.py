from django.contrib.admin.apps import AdminConfig


class FridgewiseAdminConfig(AdminConfig):
    default_site = 'kitchen.admin_site.FridgewiseAdminSite'
