from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Fridgewise administration'
admin.site.site_title = 'Fridgewise admin'
admin.site.index_title = 'Manage your kitchen platform'
urlpatterns = [path('admin/', admin.site.urls), path('', include('kitchen.urls'))]
