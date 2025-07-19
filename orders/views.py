from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Sum, F
from django.views.generic import (
    ListView, DetailView, CreateView, 
    UpdateView, DeleteView, TemplateView
)
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.utils import timezone
import csv
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Sum, F, Q
from django.contrib import messages
from django.utils import timezone
from .models import Order, Customer
from inventory.models import Product, Category, Supplier, StockMovement, ProductImage, InventoryAlert
from .forms import OrderForm, CustomerForm, OrderItemFormSet  # Only import forms that exist in orders/forms.py
from inventory.forms import ProductForm, StockMovementForm, CategoryForm, SupplierForm, ProductImageForm
from .models import Order, Customer, OrderItem  # Make sure OrderItem is imported
from inventory.models import Product  # If needed
from .forms import OrderForm, CustomerForm, OrderItemFormSet
from django.contrib.auth.forms import UserCreationForm  # Your form imports
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Inventory summary
        products = Product.objects.all()
        context['total_products'] = products.count()
        context['low_stock'] = products.filter(quantity__lte=F('reorder_level')).count()
        context['out_of_stock'] = products.filter(quantity=0).count()
        context['total_value'] = products.aggregate(
            total=Sum(F('quantity') * F('cost_price')))['total'] or 0
        
        # Recent activity
        context['recent_movements'] = StockMovement.objects.select_related(
            'product', 'created_by'
        ).order_by('-created_at')[:10]
        
        # Alerts
        context['active_alerts'] = InventoryAlert.objects.filter(
            is_resolved=False
        ).select_related('product').order_by('-created_at')[:10]
        
        # Expiring soon
        context['expiring_soon'] = products.filter(
            expiry_date__gte=timezone.now().date(),
            expiry_date__lte=timezone.now().date() + timezone.timedelta(days=30)
        )
        
        return context
class OrdersDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'orders/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_orders'] = Order.objects.count()
        context['pending_orders'] = Order.objects.filter(status='pending').count()
        context['completed_orders'] = Order.objects.filter(status='completed').count()
        context['total_revenue'] = sum(o.total for o in Order.objects.all())
        context['recent_orders'] = Order.objects.select_related('customer').order_by('-order_date')[:10]
        return context
class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related('category', 'supplier')
        search = self.request.GET.get('search')
        category = self.request.GET.get('category')
        supplier = self.request.GET.get('supplier')
        stock_status = self.request.GET.get('stock_status')
        expiry_status = self.request.GET.get('expiry_status')

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(barcode__icontains=search)
            )
        if category:
            queryset = queryset.filter(category__id=category)
        if supplier:
            queryset = queryset.filter(supplier__id=supplier)
        if stock_status == 'low':
            queryset = queryset.filter(quantity__lte=F('reorder_level'))
        elif stock_status == 'out':
            queryset = queryset.filter(quantity=0)
        if expiry_status == 'expiring':
            queryset = queryset.filter(
                expiry_date__gte=timezone.now().date(),
                expiry_date__lte=timezone.now().date() + timezone.timedelta(days=30))
        elif expiry_status == 'expired':
            queryset = queryset.filter(expiry_date__lt=timezone.now().date())

        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True)
        context['suppliers'] = Supplier.objects.filter(is_active=True)
        context['total_value'] = Product.objects.aggregate(
            total=Sum(F('quantity') * F('cost_price')))['total'] or 0
        return context

class ProductDetailView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = 'inventory/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['movements'] = self.object.movements.select_related(
            'created_by').order_by('-created_at')[:10]
        context['images'] = self.object.images.all()
        context['alerts'] = self.object.inventoryalert_set.filter(
            is_resolved=False).order_by('-created_at')
        return context

class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('inventory:product_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"Product '{self.object.name}' created successfully.")
        return response

class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'

    def get_success_url(self):
        messages.success(self.request, f"Product '{self.object.name}' updated successfully.")
        return reverse_lazy('inventory:product_detail', kwargs={'slug': self.object.slug})

class ProductDeleteView(LoginRequiredMixin, DeleteView):
    model = Product
    template_name = 'inventory/product_confirm_delete.html'
    success_url = reverse_lazy('inventory:product_list')

    def delete(self, request, *args, **kwargs):
        product = self.get_object()
        messages.success(request, f"Product '{product.name}' deleted successfully.")
        return super().delete(request, *args, **kwargs)

class ProductImageCreateView(LoginRequiredMixin, CreateView):
    model = ProductImage
    form_class = ProductImageForm
    template_name = 'inventory/productimage_form.html'

    def get_initial(self):
        initial = super().get_initial()
        initial['product'] = get_object_or_404(Product, pk=self.kwargs['product_id'])
        return initial

    def get_success_url(self):
        messages.success(self.request, "Image added successfully.")
        return reverse_lazy('inventory:product_detail', kwargs={'slug': self.object.product.slug})

class ProductImageDeleteView(LoginRequiredMixin, DeleteView):
    model = ProductImage
    template_name = 'inventory/productimage_confirm_delete.html'

    def get_success_url(self):
        messages.success(self.request, "Image deleted successfully.")
        return reverse_lazy('inventory:product_detail', kwargs={'slug': self.object.product.slug})

class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'inventory/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.filter(parent__isnull=True, is_active=True)

class CategoryDetailView(LoginRequiredMixin, DetailView):
    model = Category
    template_name = 'inventory/category_detail.html'
    context_object_name = 'category'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['child_categories'] = self.object.children.filter(is_active=True)
        context['products'] = self.object.products.filter(is_active=True)
        return context

class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/category_form.html'
    success_url = reverse_lazy('inventory:category_list')

class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/category_form.html'

    def get_success_url(self):
        return reverse_lazy('inventory:category_detail', kwargs={'pk': self.object.pk})

class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'inventory/category_confirm_delete.html'
    success_url = reverse_lazy('inventory:category_list')

    def delete(self, request, *args, **kwargs):
        category = self.get_object()
        # Move products to uncategorized before deletion
        uncategorized = Category.objects.get_or_create(name='Uncategorized', slug='uncategorized')[0]
        category.products.update(category=uncategorized)
        messages.success(request, f"Category '{category.name}' deleted. Products moved to 'Uncategorized'.")
        return super().delete(request, *args, **kwargs)

class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = 'inventory/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 20

    def get_queryset(self):
        return Supplier.objects.filter(is_active=True).order_by('name')

class SupplierDetailView(LoginRequiredMixin, DetailView):
    model = Supplier
    template_name = 'inventory/supplier_detail.html'
    context_object_name = 'supplier'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = self.object.products.filter(is_active=True)
        context['total_inventory_value'] = sum(
            product.total_value for product in context['products'])
        return context

class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'inventory/supplier_form.html'
    success_url = reverse_lazy('inventory:supplier_list')

class SupplierUpdateView(LoginRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'inventory/supplier_form.html'

    def get_success_url(self):
        return reverse_lazy('inventory:supplier_detail', kwargs={'pk': self.object.pk})

class SupplierDeleteView(LoginRequiredMixin, DeleteView):
    model = Supplier
    template_name = 'inventory/supplier_confirm_delete.html'
    success_url = reverse_lazy('inventory:supplier_list')

    def delete(self, request, *args, **kwargs):
        supplier = self.get_object()
        supplier.is_active = False
        supplier.save()
        messages.success(request, f"Supplier '{supplier.name}' deactivated.")
        return redirect(self.success_url)

class StockMovementListView(LoginRequiredMixin, ListView):
    model = StockMovement
    template_name = 'inventory/movement_list.html'
    context_object_name = 'movements'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset().select_related('product', 'created_by')
        product_id = self.request.GET.get('product')
        movement_type = self.request.GET.get('type')
        date_range = self.request.GET.get('date_range')
        
        if product_id:
            queryset = queryset.filter(product__id=product_id)
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
        if date_range == 'today':
            today = timezone.now().date()
            queryset = queryset.filter(created_at__date=today)
        elif date_range == 'week':
            week_ago = timezone.now() - timezone.timedelta(days=7)
            queryset = queryset.filter(created_at__gte=week_ago)
            
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.filter(is_active=True)
        return context

class StockMovementCreateView(LoginRequiredMixin, CreateView):
    model = StockMovement
    form_class = StockMovementForm
    template_name = 'inventory/movement_form.html'

    def get_initial(self):
        initial = super().get_initial()
        product_id = self.request.GET.get('product')
        if product_id:
            product = get_object_or_404(Product, pk=product_id)
            initial['product'] = product
            initial['unit_price'] = product.unit_price
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Stock movement recorded successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('inventory:product_detail', kwargs={'slug': self.object.product.slug})

class StockMovementDetailView(LoginRequiredMixin, DetailView):
    model = StockMovement
    template_name = 'inventory/movement_detail.html'
    context_object_name = 'movement'

class InventoryAlertListView(LoginRequiredMixin, ListView):
    model = InventoryAlert
    template_name = 'inventory/alert_list.html'
    context_object_name = 'alerts'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related('product', 'resolved_by')
        alert_type = self.request.GET.get('type')
        resolved = self.request.GET.get('resolved')
        
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        if resolved == 'true':
            queryset = queryset.filter(is_resolved=True)
        elif resolved == 'false':
            queryset = queryset.filter(is_resolved=False)
            
        return queryset.order_by('-created_at')

class ResolveAlertView(LoginRequiredMixin, View):
    def post(self, request, pk):
        alert = get_object_or_404(InventoryAlert, pk=pk)
        alert.resolve(request.user)
        messages.success(request, "Alert marked as resolved.")
        return redirect('inventory:alert_list')
@require_POST
def update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(Order.STATUS_CHOICES).keys():
        order.status = new_status
        order.save()
        messages.success(request, f"Order #{order.id} updated to {new_status.title()}.")
    else:
        messages.error(request, "Invalid status.")
    return redirect(reverse('orders:order_detail', kwargs={'pk': order.id}))
class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related('customer').order_by('-order_date')  # Changed from created_at to order_date
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')

        if search:
            queryset = queryset.filter(
                Q(customer__name__icontains=search) |
                Q(customer__email__icontains=search) |
                Q(id__icontains=search)
            )
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_orders'] = Order.objects.count()
        context['total_revenue'] = Order.objects.aggregate(total=Sum('total'))['total'] or 0
        context['customers'] = Customer.objects.all()
        return context
class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.select_related('product')
        context['total'] = self.object.items.aggregate(total=Sum(F('quantity') * F('price')))['total'] or 0
        return context      
class OrderCreateView(LoginRequiredMixin, CreateView):
    model = Order
    form_class = OrderForm
    template_name = 'orders/order_form.html'
    success_url = reverse_lazy('orders:order_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = OrderItemFormSet(self.request.POST)
        else:
            context['formset'] = OrderItemFormSet()  # Initialize empty formset
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, f"Order #{self.object.id} created successfully.")
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('orders:order_detail', kwargs={'pk': self.object.pk})
class OrderUpdateView(LoginRequiredMixin, UpdateView):
    model = Order
    form_class = OrderForm
    template_name = 'orders/order_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['formset'] = OrderItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"Order #{self.object.id} updated successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy('orders:order_detail', kwargs={'pk': self.object.pk})   
class OrderDeleteView(LoginRequiredMixin, DeleteView):
    model = Order
    template_name = 'orders/order_confirm_delete.html'
    success_url = reverse_lazy('orders:order_list')

    def delete(self, request, *args, **kwargs):
        order = self.get_object()
        messages.success(request, f"Order #{order.id} deleted successfully.")
        return super().delete(request, *args, **kwargs)     
class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'orders/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().order_by('name')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )
        return queryset         
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_customers'] = self.get_queryset().count()
        context['total_orders'] = Order.objects.count()
        context['total_revenue'] = Order.objects.aggregate(total=Sum('total'))['total'] or 0
        return context
class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'orders/customer_detail.html'
    context_object_name = 'customer'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['orders'] = self.object.orders.select_related('created_by').order_by('-created_at')
        context['total_spent'] = self.object.orders.aggregate(total=Sum('total'))['total'] or 0
        return context  
class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'orders/customer_form.html'
    success_url = reverse_lazy('orders:customer_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"Customer '{self.object.name}' created successfully.")
        return response
    def get_success_url(self):
        return reverse_lazy('orders:customer_detail', kwargs={'pk': self.object.pk})
class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'orders/customer_form.html'

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"Customer '{self.object.name}' updated successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy('orders:customer_detail', kwargs={'pk': self.object.pk})
class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    model = Customer
    template_name = 'orders/customer_confirm_delete.html'
    success_url = reverse_lazy('orders:customer_list')

    def delete(self, request, *args, **kwargs):
        customer = self.get_object()
        messages.success(request, f"Customer '{customer.name}' deleted successfully.")
        return super().delete(request, *args, **kwargs) 
class OrderItemListView(LoginRequiredMixin, ListView):  
    model = OrderItem
    template_name = 'orders/order_item_list.html'
    context_object_name = 'items'

    def get_queryset(self):
        order = get_object_or_404(Order, pk=self.kwargs['pk'])
        return order.items.select_related('product').order_by('product__name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order'] = get_object_or_404(Order, pk=self.kwargs['pk'])
        return context  
class OrderItemCreateView(LoginRequiredMixin, CreateView):
    model = OrderItem
    form_class = OrderItemFormSet
    template_name = 'orders/order_item_form.html'

    def get_initial(self):
        initial = super().get_initial()
        initial['order'] = get_object_or_404(Order, pk=self.kwargs['pk'])
        return initial

    def form_valid(self, form):
        order = get_object_or_404(Order, pk=self.kwargs['pk'])
        form.instance.order = order
        response = super().form_valid(form)
        messages.success(self.request, "Order item added successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy('orders:order_detail', kwargs={'pk': self.object.order.pk}) 
class OrderItemUpdateView(LoginRequiredMixin, UpdateView):
    model = OrderItem
    form_class = OrderItemFormSet
    template_name = 'orders/order_item_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Order item updated successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy('orders:order_detail', kwargs={'pk': self.object.order.pk}) 
class OrderItemDeleteView(LoginRequiredMixin, DeleteView):
    model = OrderItem
    template_name = 'orders/order_item_confirm_delete.html'

    def delete(self, request, *args, **kwargs):
        item = self.get_object()
        order = item.order
        messages.success(request, "Order item deleted successfully.")
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('orders:order_detail', kwargs={'pk': self.object.order.pk}) 
def add_order_item(request, pk):    
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        form = OrderItemFormSet(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, "Order item added successfully.")
            return redirect('orders:order_detail', pk=order.pk)
    else:
        form = OrderItemFormSet(instance=order)
    return render(request, 'orders/order_item_form.html', {'form': form, 'order': order})   
def update_order_item(request, pk, item_pk):
    order = get_object_or_404(Order, pk=pk)
    item = get_object_or_404(OrderItem, pk=item_pk, order=order)
    
    if request.method == 'POST':
        form = OrderItemFormSet(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Order item updated successfully.")
            return redirect('orders:order_detail', pk=order.pk)
    else:
        form = OrderItemFormSet(instance=item)
    
    return render(request, 'orders/order_item_form.html', {'form': form, 'order': order})       
def delete_order_item(request, pk, item_pk):
    order = get_object_or_404(Order, pk=pk)
    item = get_object_or_404(OrderItem, pk=item_pk, order=order)
    
    if request.method == 'POST':
        item.delete()
        messages.success(request, "Order item deleted successfully.")
        return redirect('orders:order_detail', pk=order.pk)
    
    return render(request, 'orders/order_item_confirm_delete.html', {'item': item, 'order': order})     
def export_orders(request): 
    orders = Order.objects.all().select_related('customer')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'

    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Customer Name', 'Order Date', 'Status', 'Total'])

    for order in orders:
        writer.writerow([
            order.id,
            order.customer.name,
            order.order_date.strftime('%Y-%m-%d %H:%M:%S'),
            order.get_status_display(),
            order.total
        ])

    return response     
def export_order_items(request, pk):    
    order = get_object_or_404(Order, pk=pk)
    items = order.items.select_related('product')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="order_{order.id}_items.csv"'

    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Product Name', 'Quantity', 'Price', 'Total'])

    for item in items:
        writer.writerow([
            order.id,
            item.product.name,
            item.quantity,
            item.price,
            item.get_total()
        ])

    return response 
def export_customers(request):
    customers = Customer.objects.all()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customers.csv"'

    writer = csv.writer(response)
    writer.writerow(['Customer ID', 'Name', 'Email', 'Phone', 'Address'])

    for customer in customers:
        writer.writerow([
            customer.id,
            customer.name,
            customer.email,
            customer.phone,
            customer.address
        ])

    return response     
def export_products(request):
    products = Product.objects.all().select_related('category', 'supplier')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="products.csv"'

    writer = csv.writer(response)
    writer.writerow(['Product ID', 'Name', 'SKU', 'Category', 'Supplier', 'Quantity', 'Cost Price', 'Selling Price'])

    for product in products:
        writer.writerow([
            product.id,
            product.name,
            product.sku,
            product.category.name if product.category else '',
            product.supplier.name if product.supplier else '',
            product.quantity,
            product.cost_price,
            product.unit_price
        ])

    return response 
def export_stock_movements(request):    
    movements = StockMovement.objects.all().select_related('product', 'created_by')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="stock_movements.csv"'

    writer = csv.writer(response)
    writer.writerow(['Movement ID', 'Product', 'Movement Type', 'Quantity', 'Unit Price', 'Total Value', 'Created By', 'Created At'])

    for movement in movements:
        writer.writerow([
            movement.id,
            movement.product.name,
            movement.get_movement_type_display(),
            movement.quantity,
            movement.unit_price,
            movement.get_total_value(),
            movement.created_by.username if movement.created_by else '',
            movement.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return response 
def export_inventory_alerts(request):   
    alerts = InventoryAlert.objects.all().select_related('product', 'created_by')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory_alerts.csv"'

    writer = csv.writer(response)
    writer.writerow(['Alert ID', 'Product', 'Alert Type', 'Quantity', 'Created By', 'Created At', 'Resolved'])

    for alert in alerts:
        writer.writerow([
            alert.id,
            alert.product.name,
            alert.get_alert_type_display(),
            alert.quantity,
            alert.created_by.username if alert.created_by else '',
            alert.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            alert.is_resolved
        ])

    return response   
def import_order_items(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file')
            return redirect('orders:order_list')
        
        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            for row in reader:
                try:
                    order = Order.objects.get(id=row['order_id'])
                    product = Product.objects.get(id=row['product_id'])
                    
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=row['quantity'],
                        price=row['price']
                    )
                except (Order.DoesNotExist, Product.DoesNotExist) as e:
                    messages.warning(request, f'Skipped row: {e}')
                    continue
            
            messages.success(request, 'Order items imported successfully!')
            return redirect('orders:order_list')
            
        except Exception as e:
            messages.error(request, f'Error importing file: {e}')
            return redirect('orders:order_list')
    
    return render(request, 'orders/import_order_items.html')  
    from django.shortcuts import render
from .models import Product  # or whatever your inventory model is

def low_stock_report(request):
    low_stock_items = Product.objects.filter(quantity__lt=10)  # example threshold
    return render(request, 'inventory/low_stock.html', {'items': low_stock_items})