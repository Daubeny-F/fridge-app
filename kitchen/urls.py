from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('api/state/', views.state, name='state'),
    path('api/ingredients/', views.ingredients, name='ingredients'),
    path('api/ingredients/<int:pk>/', views.ingredient_detail, name='ingredient_detail'),
    path('api/recipes/<int:pk>/favorite/', views.favorite, name='favorite'),
    path('api/shopping/', views.shopping, name='shopping'),
    path('api/shopping/<int:pk>/', views.shopping_detail, name='shopping_detail'),
    path('api/settings/', views.settings_view, name='settings'),
    path('api/export/', views.export_inventory, name='export'),
]
