from django.urls import path
from .views import product_views, category_views, admin_views, vendor_views

urlpatterns = [
    # Products (public feed + vendor upload)
    path('feed/', product_views.product_feed, name='product_feed'),
    path('upload/', product_views.upload_product, name='upload_product'),
    path('favorite/', product_views.toggle_favorite, name='toggle_favorite'),

    # Categories (public)
    path('categories/', category_views.list_categories, name='list_categories'),
    path('categories/visibility/', category_views.manage_category_visibility, name='manage_category_visibility'),
    path('categories/create/', category_views.create_custom_category, name='create_custom_category'),
    path('public/vendors-and-categories/', category_views.public_vendors_and_categories, name='public_vendors_and_categories'),

    # Vendor Self-Service
    path('vendor/update-profile/', vendor_views.update_vendor_profile, name='update_vendor_profile'),
    path('vendor/products/', vendor_views.vendor_products, name='vendor_products'),
    path('vendor/products/<int:product_id>/edit/', vendor_views.edit_vendor_product, name='edit_vendor_product'),
    path('vendor/products/<int:product_id>/delete/', vendor_views.delete_vendor_product, name='delete_vendor_product'),

    # Admin – Vendors
    path('admin/vendors/', admin_views.list_vendors, name='admin_list_vendors'),
    path('admin/vendors/<int:vendor_id>/', admin_views.get_vendor_detail, name='admin_vendor_detail'),
    path('admin/vendors/<int:vendor_id>/edit/', admin_views.admin_edit_vendor, name='admin_edit_vendor'),
    path('admin/vendors/<int:vendor_id>/delete/', admin_views.admin_delete_vendor, name='admin_delete_vendor'),
    path('admin/vendors/<int:vendor_id>/toggle/', admin_views.toggle_vendor_active, name='admin_toggle_vendor'),
    path('admin/create-vendor/', admin_views.admin_create_vendor, name='admin_create_vendor'),
    path('admin/approve-vendor/', admin_views.approve_vendor, name='admin_approve_vendor'),

    # Admin – Products
    path('admin/products/', admin_views.admin_list_products, name='admin_list_products'),
    path('admin/products/<int:product_id>/', admin_views.admin_delete_product, name='admin_delete_product'),
    path('admin/products/<int:product_id>/edit/', admin_views.admin_edit_product, name='admin_edit_product'),
    path('admin/products/<int:product_id>/toggle/', admin_views.admin_toggle_product, name='admin_toggle_product'),
    path('admin/post-on-behalf/', admin_views.admin_post_product, name='admin_post_on_behalf'),

    # Admin – Categories
    path('admin/categories/', admin_views.admin_list_categories, name='admin_list_categories'),
    path('admin/categories/create/', admin_views.admin_create_category, name='admin_create_category'),
    path('admin/categories/<int:category_id>/edit/', admin_views.admin_edit_category, name='admin_edit_category'),
    path('admin/categories/<int:category_id>/delete/', admin_views.admin_delete_category, name='admin_delete_category'),
    path('admin/categories/<int:category_id>/toggle/', admin_views.admin_toggle_category, name='admin_toggle_category'),
    path('admin/categories/<int:category_id>/subcategories/', admin_views.admin_create_subcategory, name='admin_create_subcategory'),
    path('admin/subcategories/<int:subcategory_id>/edit/', admin_views.admin_edit_subcategory, name='admin_edit_subcategory'),
    path('admin/subcategories/<int:subcategory_id>/delete/', admin_views.admin_delete_subcategory, name='admin_delete_subcategory'),

    # Admin – Favorites & Analytics
    path('admin/favorites/', admin_views.admin_favorites, name='admin_favorites'),
    path('admin/customers/', admin_views.admin_list_customers, name='admin_list_customers'),
    path('admin/guests/', admin_views.admin_list_guests, name='admin_list_guests'),
    path('admin/analytics/', admin_views.admin_analytics, name='admin_analytics'),
    path('admin/export/<str:report_type>/', admin_views.admin_export_csv, name='admin_export_csv'),

    # Public – Vendor profile page
    path('vendor/<int:vendor_id>/', admin_views.vendor_public_profile, name='vendor_public_profile'),
]
