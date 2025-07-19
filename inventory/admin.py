from datetime import timezone
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Supplier, Category, Product, StockMovement, ProductImage, InventoryAlert
from .forms import ProductForm

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone', 'total_products', 'is_active', 'created_at')
    search_fields = ('name', 'contact_person', 'email', 'phone')
    list_filter = ('is_active', 'created_at')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at', 'total_inventory_value')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('contact_person', 'email', 'phone', 'website')
        }),
        ('Address', {
            'fields': ('address',)
        }),
        ('Metadata', {
            'fields': ('notes', 'created_at', 'updated_at', 'total_inventory_value')
        }),
    )
    actions = ['activate_suppliers', 'deactivate_suppliers']

    def total_products(self, obj):
        return obj.products.count()
    total_products.short_description = 'Products'

    def activate_suppliers(self, request, queryset):
        queryset.update(is_active=True)
    activate_suppliers.short_description = "Activate selected suppliers"

    def deactivate_suppliers(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_suppliers.short_description = "Deactivate selected suppliers"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'product_count', 'is_active', 'hierarchy')
    search_fields = ('name', 'description')
    list_filter = ('is_active', 'parent')
    list_editable = ('is_active',)
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'parent', 'is_active')
        }),
        ('Description', {
            'fields': ('description', 'image')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'

    def hierarchy(self, obj):
        return obj.get_full_path()
    hierarchy.short_description = 'Hierarchy'

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ('preview_image',)
    
    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px;"/>', obj.image.url)
        return "-"
    preview_image.short_description = 'Preview'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductForm
    list_display = ('name', 'category_link', 'supplier_link', 'unit_price', 'cost_price', 
                    'quantity', 'stock_status', 'expiry_status', 'is_active')
    list_filter = ('is_active', 'category', 'supplier', 'created_at')
    search_fields = ('name', 'sku', 'barcode', 'description')
    list_editable = ('unit_price', 'quantity', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'stock_status', 'total_value', 
                      'days_to_expiry', 'sku', 'barcode')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'is_active')
        }),
        ('Pricing', {
            'fields': ('unit_price', 'cost_price', 'tax_rate')
        }),
        ('Inventory', {
            'fields': ('quantity', 'reorder_level', 'stock_status', 'total_value')
        }),
        ('Identification', {
            'fields': ('sku', 'barcode')
        }),
        ('Physical Attributes', {
            'fields': ('weight', 'dimensions')
        }),
        ('Dates', {
            'fields': ('manufacture_date', 'expiry_date', 'days_to_expiry')
        }),
        ('Relationships', {
            'fields': ('category', 'supplier')
        }),
    )
    inlines = [ProductImageInline]
    actions = ['activate_products', 'deactivate_products', 'generate_barcodes']

    def category_link(self, obj):
        if obj.category:
            url = reverse('admin:inventory_category_change', args=[obj.category.id])
            return format_html('<a href="{}">{}</a>', url, obj.category)
        return "-"
    category_link.short_description = 'Category'

    def supplier_link(self, obj):
        if obj.supplier:
            url = reverse('admin:inventory_supplier_change', args=[obj.supplier.id])
            return format_html('<a href="{}">{}</a>', url, obj.supplier)
        return "-"
    supplier_link.short_description = 'Supplier'

    def expiry_status(self, obj):
        if not obj.expiry_date:
            return "-"
        days = obj.days_to_expiry
        if days is None:
            return "-"
        if days < 0:
            return format_html('<span style="color: red;">Expired ({} days)</span>', abs(days))
        elif days <= 30:
            return format_html('<span style="color: orange;">Expires in {} days</span>', days)
        return f"Expires in {days} days"
    expiry_status.short_description = 'Expiry Status'

    def activate_products(self, request, queryset):
        queryset.update(is_active=True)
    activate_products.short_description = "Activate selected products"

    def deactivate_products(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_products.short_description = "Deactivate selected products"

    def generate_barcodes(self, request, queryset):
        for product in queryset:
            if not product.barcode:
                product.generate_barcode()
                product.save()
        self.message_user(request, f"Generated barcodes for {queryset.count()} products")
    generate_barcodes.short_description = "Generate barcodes for selected products"

class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product_link', 'movement_type', 'quantity', 'before_after', 
                    'unit_price', 'total_price', 'created_by', 'created_at')
    list_filter = ('movement_type', 'created_at', 'product__category')
    search_fields = ('product__name', 'reference', 'notes')
    readonly_fields = ('before_quantity', 'after_quantity', 'created_at', 'created_by')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Information', {
            'fields': ('product', 'movement_type', 'reference')
        }),
        ('Quantities', {
            'fields': ('quantity', 'before_quantity', 'after_quantity')
        }),
        ('Pricing', {
            'fields': ('unit_price', 'total_price')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at')
        }),
    )

    def product_link(self, obj):
        url = reverse('admin:inventory_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product)
    product_link.short_description = 'Product'

    def before_after(self, obj):
        return f"{obj.before_quantity} → {obj.after_quantity}"
    before_after.short_description = 'Stock Change'

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only for new records
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(InventoryAlert)
class InventoryAlertAdmin(admin.ModelAdmin):
    list_display = ('product_link', 'alert_type', 'message', 'is_resolved', 
                    'created_at', 'resolved_at', 'resolved_by')
    list_filter = ('alert_type', 'is_resolved', 'created_at')
    search_fields = ('product__name', 'message')
    readonly_fields = ('created_at', 'resolved_at', 'resolved_by')
    actions = ['mark_as_resolved']
    date_hierarchy = 'created_at'

    def product_link(self, obj):
        url = reverse('admin:inventory_product_change', args=[obj.product.id])
        return format_html('<a href="{}">{}</a>', url, obj.product)
    product_link.short_description = 'Product'

    def mark_as_resolved(self, request, queryset):
        queryset.update(
            is_resolved=True,
            resolved_at=timezone.now(),
            resolved_by=request.user
        )
        self.message_user(request, f"Marked {queryset.count()} alerts as resolved")
    mark_as_resolved.short_description = "Mark selected alerts as resolved"

admin.site.register(StockMovement, StockMovementAdmin)