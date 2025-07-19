from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User

class Supplier(models.Model):
    name = models.CharField(max_length=100, unique=True)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    website = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = "suppliers"
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]

    def total_products_supplied(self):
        return self.products.count()

    def total_inventory_value(self):
        return sum(product.total_value for product in self.products.all())

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='category_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('inventory:category_detail', args=[self.slug])

    def product_count(self):
        return self.products.count()

    def get_all_children(self):
        children = []
        for child in self.children.all():
            children.append(child)
            children.extend(child.get_all_children())
        return children

class ProductManager(models.Manager):
    def active(self):
        return self.filter(is_active=True)

    def low_stock(self):
        return self.active().filter(quantity__lte=models.F('reorder_level'))

    def out_of_stock(self):
        return self.active().filter(quantity=0)

    def expiring_soon(self, days=30):
        today = timezone.now().date()
        return self.active().filter(
            expiry_date__isnull=False,
            expiry_date__gte=today,
            expiry_date__lte=today + timezone.timedelta(days=days)
        )

class Product(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, related_name='products')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=5)
    sku = models.CharField(max_length=50, unique=True)
    barcode = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    dimensions = models.CharField(max_length=50, blank=True)
    manufacture_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductManager()

    def __str__(self):
        return f"{self.name} ({self.sku})"

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['barcode']),
            models.Index(fields=['quantity']),
            models.Index(fields=['is_active']),
            models.Index(fields=['expiry_date']),
        ]

    def clean(self):
        if self.unit_price < self.cost_price:
            raise ValidationError("Unit price cannot be less than cost price")
        
        if self.quantity < 0:
            raise ValidationError("Quantity cannot be negative")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.sku:
            self.sku = f"SKU-{self.id or 0:04d}"
        super().save(*args, **kwargs)
        if not self.sku.startswith('SKU-'):
            self.sku = f"SKU-{self.id:04d}"
            super().save(update_fields=['sku'])

    def get_absolute_url(self):
        return reverse('inventory:product_detail', args=[self.slug])

    @property
    def stock_status(self):
        if self.quantity == 0:
            return "Out of Stock"
        elif self.quantity <= self.reorder_level:
            return "Low Stock"
        return "In Stock"

    @property
    def total_value(self):
        return self.quantity * self.cost_price

    @property
    def days_to_expiry(self):
        if not self.expiry_date:
            return None
        return (self.expiry_date - timezone.now().date()).days

    def generate_barcode(self):
        if not self.barcode:
            self.barcode = f"BC-{self.id:08d}"
            self.save()

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')
    is_default = models.BooleanField(default=False)
    caption = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.product.name}"

    class Meta:
        ordering = ['-is_default', 'created_at']

class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
        ('transfer', 'Transfer'),
        ('loss', 'Loss'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()
    before_quantity = models.IntegerField(editable=False)
    after_quantity = models.IntegerField(editable=False)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_movement_type_display()} of {self.product.name}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['movement_type']),
            models.Index(fields=['product']),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:  # Only for new records
            self.before_quantity = self.product.quantity
            
            if self.movement_type in ['purchase', 'return']:
                self.after_quantity = self.product.quantity + self.quantity
            else:
                self.after_quantity = self.product.quantity - self.quantity

            if not self.unit_price:
                self.unit_price = self.product.unit_price
            self.total_price = self.unit_price * abs(self.quantity)
            
        super().save(*args, **kwargs)
        
        # Update product quantity
        if self.movement_type in ['purchase', 'return']:
            self.product.quantity += self.quantity
        elif self.movement_type in ['sale', 'adjustment', 'loss']:
            self.product.quantity -= self.quantity
        self.product.save()

class InventoryAlert(models.Model):
    ALERT_TYPES = [
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.TextField()
    threshold = models.IntegerField(null=True, blank=True)  # For stock alerts
    days_to_expiry = models.IntegerField(null=True, blank=True)  # For expiry alerts
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['is_resolved']),
            models.Index(fields=['alert_type']),
        ]

    def __str__(self):
        return f"{self.get_alert_type_display()} alert for {self.product.name}"

    def resolve(self, user):
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = user
        self.save()
    def get_absolute_url(self):
        return reverse('inventory:alert_detail', args=[self.pk])    
    def clean(self):
        if self.alert_type == 'low_stock' and self.threshold is None:
            raise ValidationError("Threshold must be set for low stock alerts")
        if self.alert_type == 'expiring' and self.days_to_expiry is None:
            raise ValidationError("Days to expiry must be set for expiring alerts")
        if self.alert_type == 'expired' and self.days_to_expiry is not None:
            raise ValidationError("Days to expiry should not be set for expired alerts")
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
class Alert(models.Model):
    # Basic alert fields
    ALERT_TYPES = [
        ('low_stock', 'Low Stock'),
        ('expired', 'Expired Product'),
        ('threshold', 'Threshold Reached'),
        ('other', 'Other'),
    ]
    
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alerts_created')
    related_product = models.ForeignKey(
        'Product',  # Assuming you have a Product model
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alerts'
    )

    def __str__(self):
        return f"{self.get_alert_type_display()} Alert - {self.message[:50]}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Alert'
        verbose_name_plural = 'Alerts'        
    
