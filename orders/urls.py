from django.urls import path
from .views import OrdersDashboardView, update_order_status
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.OrderListView.as_view(), name='order_list'),
    path('create/', views.OrderCreateView.as_view(), name='order_create'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('dashboard/', OrdersDashboardView.as_view(), name='orders_dashboard'),
    path('<int:pk>/update/', views.OrderUpdateView.as_view(), name='order_update'),
    path('<int:pk>/delete/', views.OrderDeleteView.as_view(), name='order_delete'),
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('<int:pk>/update-status/', update_order_status, name='update_status'),
    path('customers/create/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/update/', views.CustomerUpdateView.as_view(), name='customer_update'),
    path('customers/<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
    path('orders/<int:pk>/items/add/', views.add_order_item, name='add_order_item'),
    path('orders/<int:pk>/items/<int:item_pk>/update/', views.update_order_item, name='update_order_item'),
    path('orders/<int:pk>/items/<int:item_pk>/delete/', views.delete_order_item, name='delete_order_item'),
    path('orders/<int:pk>/items/', views.OrderItemListView.as_view(), name='order_item_list'),
    path('orders/<int:pk>/items/create/', views.OrderItemCreateView.as_view(), name='order_item_create'),
    path('orders/<int:pk>/items/<int:item_pk>/update/', views.OrderItemUpdateView.as_view(), name='order_item_update'),
    path('orders/<int:pk>/items/<int:item_pk>/delete/', views.OrderItemDeleteView.as_view(), name='order_item_delete'),
    path('orders/<int:pk>/items/export/', views.export_order_items, name='export_order_items'),
    path('orders/<int:pk>/items/import/', views.import_order_items, name='import_order_items'),
]