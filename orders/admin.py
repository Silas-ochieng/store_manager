from django.contrib import admin
from django.utils.html import format_html
from .models import Customer, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    raw_id_fields = ['product']
    fields = ('product', 'quantity', 'price', 'get_total')
    readonly_fields = ['get_total']

    def get_total(self, obj):
        if obj.pk:
            return f"${obj.get_total():,.2f}"
        return "-"
    get_total.short_description = "Item Total"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'order_date', 'status', 'total_display')
    list_filter = ('status', 'order_date')
    search_fields = ('customer__name', 'id')
    inlines = [OrderItemInline]
    readonly_fields = ('total',)

    def total_display(self, obj):
        return f"${obj.total:,.2f}"
    total_display.short_description = 'Total'


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'preview_image', 'order_count')
    search_fields = ('name', 'email', 'phone')
    readonly_fields = ['preview_image']

    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="60" style="border-radius:5px;" />', obj.image.url)
        return "No Image"
    preview_image.short_description = 'Image'

    def order_count(self, obj):
        return obj.order_set.count()
    order_count.short_description = 'Orders'
