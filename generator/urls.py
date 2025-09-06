from django.urls import path
from . import views

app_name = 'generator'

urlpatterns = [
    # API endpoints
    path('api/generate/', views.generate_page, name='generate_page'),
    path('api/pages/', views.list_pages, name='list_pages'),
    path('api/pages/<int:page_id>/', views.get_page, name='get_page'),
    
    # HTML views
    path('view/<int:page_id>/', views.view_page, name='view_page'),
    path('demo/', views.demo_form, name='demo_form'),
]