from django.urls import path
from . import views
from . import admin_views

urlpatterns = [
    # Auth
    path('register/', views.register, name='register'),
    path('login/', views.signin, name='login'),
    path('refresh-token/', views.refresh_token, name='refresh_token'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('confirm-reset/', views.confirm_reset, name='confirm_reset'),
    path('check-user/', views.check_user, name='check_user'),
    path('profile/', views.profile, name='profile'),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('guest-login/', views.guest_login, name='guest_login'),
    path('convert-guest/', views.convert_guest, name='convert_guest'),
    path('public-config/', views.public_config, name='public_config'),

    # Admin – Customers & Guests
    path('admin/customers/', admin_views.admin_list_customers, name='admin_list_customers'),
    path('admin/customers/<int:customer_id>/', admin_views.admin_customer_detail, name='admin_customer_detail'),
    path('admin/customers/<int:customer_id>/block/', admin_views.admin_block_customer, name='admin_block_customer'),
    path('admin/guests/', admin_views.admin_list_guests, name='admin_list_guests'),

    # Admin – Notifications
    path('admin/notifications/', admin_views.admin_send_notification, name='admin_send_notification'),

    # Admin – Popup Settings
    path('admin/popup-settings/', admin_views.admin_get_popup_settings, name='admin_get_popup_settings'),
    path('admin/popup-settings/save/', admin_views.admin_save_popup_settings, name='admin_save_popup_settings'),

    # Admin – System Settings
    path('admin/system-settings/', admin_views.admin_get_system_settings, name='admin_get_system_settings'),
    path('admin/system-settings/save/', admin_views.admin_save_system_settings, name='admin_save_system_settings'),
]
