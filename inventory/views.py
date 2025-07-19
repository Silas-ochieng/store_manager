from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, 
    UpdateView, DeleteView, TemplateView
)
from datetime import datetime
from .models import InventoryAlert
from django.shortcuts import render
from datetime import timedelta
from orders.models import OrderItem # Import OrderItem from orders app
from .models import Product  # and any other models you need
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Sum, F, Q, Count
from django.contrib import messages
from django.utils import timezone
from orders.models import Order, Customer
from inventory.models import Category  # and any other inventory models you need
from .models import Product, Supplier, StockMovement, ProductImage, InventoryAlert, Category
from django.contrib.auth.forms import UserCreationForm
from .forms import (
    ProductForm, StockMovementForm, 
    CategoryForm, SupplierForm, ProductImageForm,InventoryAlertForm
)
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect('login')  # Assuming you have a login URL named 'login'
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
            expiry_date__lte=timezone.now().date() + timezone.timedelta(days=30))
        
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
                Q(barcode__icontains=search))
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

from django.db.models import Count

class CategoryDetailView(LoginRequiredMixin, DetailView):
    model = Category
    template_name = 'inventory/category_detail.html'
    context_object_name = 'category'
    
    def get_queryset(self):
        return super().get_queryset().annotate(
            active_products_count=Count('products', filter=Q(products__is_active=True)))

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
    

def product_export(request):
    # Implement your export logic here
    return HttpResponse("Export not implemented yet.")
# Note: This is a placeholder function. You can implement CSV or Excel export functionality as needed.

class CategoryDetailView(LoginRequiredMixin, DetailView):
    model = Category
    template_name = 'inventory/category_detail.html'
    context_object_name = 'category'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = self.object.products.filter(is_active=True)
        context['child_categories'] = self.object.children.filter(is_active=True)
        return context      
class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/category_form.html'
    success_url = reverse_lazy('inventory:category_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"Category '{self.object.name}' created successfully.")
        return response
class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/category_form.html'

    def get_success_url(self):
        messages.success(self.request, f"Category '{self.object.name}' updated successfully.")
        return reverse_lazy('inventory:category_detail', kwargs={'pk': self.object.pk})     
class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'inventory/category_confirm_delete.html'
    success_url = reverse_lazy('inventory:category_list')

    def delete(self, request, *args, **kwargs):
        category = self.get_object()
        # Move products to uncategorized before deletion
        uncategorized, created = Category.objects.get_or_create(name='Uncategorized', slug='uncategorized')
        category.products.update(category=uncategorized)
        messages.success(request, f"Category '{category.name}' deleted. Products moved to 'Uncategorized'.")
        return super().delete(request, *args, **kwargs)
    
    
class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'inventory/supplier_form.html'
    success_url = reverse_lazy('inventory:supplier_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"Supplier '{self.object.name}' created successfully.")
        return response 

class SupplierUpdateView(LoginRequiredMixin, UpdateView):   

    model = Supplier
    form_class = SupplierForm
    template_name = 'inventory/supplier_form.html'

    def get_success_url(self):
        messages.success(self.request, f"Supplier '{self.object.name}' updated successfully.")
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product'] = self.object.product
        return context

class StockMovementUpdateView(LoginRequiredMixin, UpdateView):  
    model = StockMovement
    form_class = StockMovementForm
    template_name = 'inventory/movement_form.html'

    def get_success_url(self):
        messages.success(self.request, "Stock movement updated successfully.")
        return reverse_lazy('inventory:movement_detail', kwargs={'pk': self.object.pk})
class StockMovementDeleteView(LoginRequiredMixin, DeleteView):
    model = StockMovement
    template_name = 'inventory/movement_confirm_delete.html'

    def delete(self, request, *args, **kwargs):
        movement = self.get_object()
        messages.success(request, f"Stock movement for '{movement.product.name}' deleted successfully.")
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('inventory:movement_list')
class InventoryAlertCreateView(LoginRequiredMixin, CreateView):
    model = InventoryAlert
    form_class = InventoryAlertForm
    template_name = 'inventory/alert_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Inventory alert created successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy('inventory:alert_list')     
class InventoryAlertUpdateView(LoginRequiredMixin, UpdateView):
    model = InventoryAlert
    form_class = InventoryAlertForm
    template_name = 'inventory/alert_form.html'

    def form_valid(self, form):
        messages.success(self.request, "Inventory alert updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('inventory:alert_detail', kwargs={'pk': self.object.pk})
class InventoryAlertDetailView(LoginRequiredMixin, DetailView):
    model = InventoryAlert
    template_name = 'inventory/alert_detail.html'
    context_object_name = 'alert'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product'] = self.object.product
        return context  
class InventoryAlertDeleteView(LoginRequiredMixin, DeleteView): 
    model = InventoryAlert
    template_name = 'inventory/alert_confirm_delete.html'

    def delete(self, request, *args, **kwargs):
        alert = self.get_object()
        messages.success(request, f"Inventory alert for '{alert.product.name}' deleted successfully.")
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('inventory:alert_list')     
class InventoryAlertResolveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        alert = get_object_or_404(InventoryAlert, pk=pk)
        alert.resolve(request.user)
        messages.success(request, "Alert marked as resolved.")
        return redirect('inventory:alert_list') 
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
class InventoryAlertDetailView(LoginRequiredMixin, DetailView):
    model = InventoryAlert
    template_name = 'inventory/alert_detail.html'
    context_object_name = 'alert'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product'] = self.object.product
        return context  
class InventoryAlertCreateView(LoginRequiredMixin, CreateView):
    model = InventoryAlert
    form_class = InventoryAlertForm
    template_name = 'inventory/alert_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Inventory alert created successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy('inventory:alert_list')     

class InventoryAlertUpdateView(LoginRequiredMixin, UpdateView):
    model = InventoryAlert
    form_class = InventoryAlertForm
    template_name = 'inventory/alert_form.html'

    def form_valid(self, form):
        messages.success(self.request, "Inventory alert updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('inventory:alert_detail', kwargs={'pk': self.object.pk})                    
class InventoryAlertDeleteView(LoginRequiredMixin, DeleteView):
    model = InventoryAlert
    template_name = 'inventory/alert_confirm_delete.html'

    def delete(self, request, *args, **kwargs):
        alert = self.get_object()
        messages.success(request, f"Inventory alert for '{alert.product.name}' deleted successfully.")
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('inventory:alert_list') 
class InventoryAlertResolveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        alert = get_object_or_404(InventoryAlert, pk=pk)
        alert.resolve(request.user)
        messages.success(request, "Alert marked as resolved.")
        return redirect('inventory:alert_list') 
    
def low_stock_report(request):
    low_stock_items = Product.objects.filter(quantity__lt=10)  # example threshold
    return render(request, 'inventory/low_stock.html', {'items': low_stock_items})


def sales_report(request):
    # Get today's date
    today = timezone.now().date()
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)
    
    # Get filter parameters from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')
    product_id = request.GET.get('product')
    
    # Base queryset
    order_items = OrderItem.objects.select_related('order', 'product')
    
    # Apply filters
    if status:
        order_items = order_items.filter(order__status=status)
    if product_id:
        order_items = order_items.filter(product_id=product_id)
    
    # Date filtering
    date_filter_applied = False
    if start_date and end_date:
        try:
            order_items = order_items.filter(
                order__order_date__date__range=[start_date, end_date]
            )
            date_filter_applied = True
        except:
            pass
    
    # Calculate sales data
    daily_sales = order_items.filter(
        order__order_date__date=today
    ).aggregate(
        total_sales=Sum(F('quantity') * F('price')),
        total_orders=Count('order', distinct=True)
    ) if not date_filter_applied else None
    
    weekly_sales = order_items.filter(
        order__order_date__date__gte=last_week
    ).aggregate(
        total_sales=Sum(F('quantity') * F('price')),
        total_orders=Count('order', distinct=True)
    ) if not date_filter_applied else None
    
    monthly_sales = order_items.filter(
        order__order_date__date__gte=last_month
    ).aggregate(
        total_sales=Sum(F('quantity') * F('price')),
        total_orders=Count('order', distinct=True)
    )
    
    # Filtered results (when date range is applied)
    filtered_sales = order_items.aggregate(
        total_sales=Sum(F('quantity') * F('price')),
        total_orders=Count('order', distinct=True)
    ) if date_filter_applied else None
    
    # Top selling products
    top_products = order_items.values(
        'product__name',
        'product__sku'
    ).annotate(
        total_sold=Sum('quantity'),
        revenue=Sum(F('quantity') * F('price'))
    ).order_by('-revenue')[:10]
    
    # Prepare context
    context = {
        'daily_sales': daily_sales or {'total_sales': 0, 'total_orders': 0},
        'weekly_sales': weekly_sales or {'total_sales': 0, 'total_orders': 0},
        'monthly_sales': monthly_sales or {'total_sales': 0, 'total_orders': 0},
        'filtered_sales': filtered_sales,
        'top_products': top_products,
        'status_choices': Order.STATUS_CHOICES,
        'all_products': Product.objects.all(),
        'date_filter_applied': date_filter_applied,
        'report_date': today,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'inventory/reports/sales.html', context)

def inventory_report(request):
    # Get filter parameters
    category_id = request.GET.get('category')
    stock_status = request.GET.get('stock_status')
    movement_type = request.GET.get('movement_type')
    movement_start = request.GET.get('movement_start')
    movement_end = request.GET.get('movement_end')
    
    # Base product queryset
    products = Product.objects.all()
    
    # Category filter
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Stock status filter
    if stock_status == 'out_of_stock':
        products = products.filter(quantity=0)
    elif stock_status == 'low_stock':
        products = products.filter(quantity__lt=F('reorder_level'))
    
    # Inventory summary
    inventory_summary = {
        'total_products': products.count(),
        'out_of_stock': products.filter(quantity=0).count(),
        'low_stock': products.filter(quantity__lt=F('reorder_level')).count(),
        'total_value': products.aggregate(
            total=Sum(F('quantity') * F('cost_price'))
        )['total'] or 0
    }
    
    # Stock movements filtering
    stock_movements = StockMovement.objects.select_related('product')
    
    if movement_type:
        stock_movements = stock_movements.filter(movement_type=movement_type)
    
    if movement_start and movement_end:
        try:
            movement_start = datetime.strptime(movement_start, '%Y-%m-%d').date()
            movement_end = datetime.strptime(movement_end, '%Y-%m-%d').date()
            stock_movements = stock_movements.filter(
                created_at__date__range=[movement_start, movement_end]
            )
        except ValueError:
            pass
    
    stock_movements = stock_movements.order_by('-created_at')[:20]
    
    # Category distribution (with current filters)
    categories = products.values(
        'category__name', 'category__id'
    ).annotate(
        count=Count('id'),
        total_value=Sum(F('quantity') * F('cost_price'))
    ).order_by('-count')
    
    context = {
        'inventory_summary': inventory_summary,
        'stock_movements': stock_movements,
        'categories': categories,
        'all_categories': Category.objects.all(),
        'current_category': int(category_id) if category_id else None,
        'current_stock_status': stock_status,
        'current_movement_type': movement_type,
        'movement_start': movement_start,
        'movement_end': movement_end,
    }
    
    return render(request, 'inventory/reports/inventory.html', context)
def resolve_alert(request, pk):
    alert = get_object_or_404(InventoryAlert, pk=pk)
    alert.resolved = True
    alert.resolved_by = request.user
    alert.resolved_at = timezone.now()
    alert.save()
    return redirect('inventory:alert_list') 
from django.shortcuts import get_object_or_404, redirect
from .models import Alert  # Make sure to import your Alert model

def delete_alert(request, pk):
    alert = get_object_or_404(Alert, pk=pk)
    alert.delete()
    return redirect('alerts_list')  # Or wherever you want to redirect after deletion

# Note: The above function assumes you have an InventoryAlert model with fields like resolved, resolved_by, and resolved_at.    
 # Make sure this URL exists
# Note: Ensure you have the necessary imports and models defined in your project.   
# This code provides a comprehensive set of views for managing inventory, including products, categories, suppliers, stock movements, and inventory alerts.