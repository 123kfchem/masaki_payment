from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('report/pdf/', views.download_pdf_report, name='download_pdf_report'),
    path('callback/', views.payment_callback, name='payment_callback'),
]
