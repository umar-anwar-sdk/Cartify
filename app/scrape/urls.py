from django.urls import path
from . import views

urlpatterns = [
    path('scrape/', views.scrape_product, name='scrape_product'),
    path('categories/', views.get_all_categories, name='get_all_categories'),
    path('products-by-category/', views.get_products_by_category, name='get_products_by_category'),
    path('product/<int:product_id>/', views.get_product_by_id, name='get_product_by_id'),
    path('click-count/', views.get_count_to_check_clicks, name='get_count_to_check_clicks'),
    path('admin/all-scraped-items/', views.admin_list_all_scraped_items, name='admin_all_scraped_items'),
]