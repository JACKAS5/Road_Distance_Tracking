from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('roads/', views.get_roads, name='get_roads'),
    path('distance/', views.calculate_distance, name='calculate_distance'),
    path('search/', views.search_location, name='search_location'),
]