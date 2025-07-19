from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import (
    Category, Product, Supplier, 
    StockMovement, ProductImage, InventoryAlert
)
from .forms import ProductForm, StockMovementForm
from .views import ProductCreateView

class InventoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create test user
        cls.user = User.objects.create_user(
            username='testuser', 
            password='testpass123'
        )
        
        # Create test supplier
        cls.supplier = Supplier.objects.create(
            name="Tech Supplier",
            contact_person="John Doe",
            email="john@techsupplier.com",
            phone="1234567890",
            address="123 Tech St",
            is_active=True
        )
        
        # Create test categories
        cls.parent_category = Category.objects.create(
            name="Electronics",
            slug="electronics",
            is_active=True
        )
        cls.category = Category.objects.create(
            name="Laptops",
            slug="laptops",
            parent=cls.parent_category,
            is_active=True
        )
        
        # Create test products
        cls.product1 = Product.objects.create(
            name="Premium Laptop",
            slug="premium-laptop",
            description="High-end laptop",
            category=cls.category,
            supplier=cls.supplier,
            unit_price=1299.99,
            cost_price=999.99,
            quantity=15,
            reorder_level=5,
            sku="SKU-0001",
            barcode="LP001",
            is_active=True
        )
        
        cls.product2 = Product.objects.create(
            name="Budget Laptop",
            slug="budget-laptop",
            description="Affordable laptop",
            category=cls.category,
            supplier=cls.supplier,
            unit_price=599.99,
            cost_price=399.99,
            quantity=3,  # Low stock
            reorder_level=5,
            sku="SKU-0002",
            is_active=True,
            expiry_date=timezone.now().date() + timedelta(days=10)  # Expiring soon
        )
        
        # Create test stock movements
        cls.movement1 = StockMovement.objects.create(
            product=cls.product1,
            movement_type='purchase',
            quantity=10,
            before_quantity=5,
            after_quantity=15,
            unit_price=999.99,
            total_price=9999.90,
            created_by=cls.user
        )
        
        # Create test image
        cls.product_image = ProductImage.objects.create(
            product=cls.product1,
            image='test.jpg',
            caption='Product Image'
        )
        
        # Create test alert
        cls.alert = InventoryAlert.objects.create(
            product=cls.product2,
            alert_type='low_stock',
            message="Low stock alert",
            threshold=5,
            is_resolved=False
        )

    # Model Tests
    def test_category_str(self):
        self.assertEqual(str(self.category), "Laptops")

    def test_category_get_absolute_url(self):
        url = self.category.get_absolute_url()
        self.assertEqual(url, f'/inventory/categories/{self.category.slug}/')

    def test_product_str(self):
        self.assertEqual(str(self.product1), "Premium Laptop (SKU-0001)")

    def test_product_stock_status(self):
        self.assertEqual(self.product1.stock_status, "In Stock")
        self.product1.quantity = 0
        self.assertEqual(self.product1.stock_status, "Out of Stock")
        self.product1.quantity = 3
        self.assertEqual(self.product1.stock_status, "Low Stock")

    def test_product_total_value(self):
        self.assertEqual(self.product1.total_value, 15 * 999.99)

    def test_product_days_to_expiry(self):
        self.assertEqual(self.product2.days_to_expiry, 10)

    def test_supplier_str(self):
        self.assertEqual(str(self.supplier), "Tech Supplier")

    def test_supplier_total_products(self):
        self.assertEqual(self.supplier.total_products_supplied(), 2)

    def test_stock_movement_str(self):
        self.assertEqual(str(self.movement1), "Purchase of Premium Laptop")

    def test_stock_movement_save_updates_product(self):
        initial_qty = self.product1.quantity
        StockMovement.objects.create(
            product=self.product1,
            movement_type='sale',
            quantity=5,
            before_quantity=initial_qty,
            after_quantity=initial_qty-5,
            created_by=self.user
        )
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.quantity, initial_qty - 5)

    def test_inventory_alert_str(self):
        self.assertEqual(str(self.alert), "Low Stock alert for Budget Laptop")

    # Form Tests
    def test_product_form_valid(self):
        form_data = {
            'name': 'New Laptop',
            'description': 'Test description',
            'category': self.category.id,
            'supplier': self.supplier.id,
            'unit_price': 899.99,
            'cost_price': 699.99,
            'quantity': 10,
            'reorder_level': 3,
            'is_active': True
        }
        form = ProductForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_product_form_invalid_price(self):
        form_data = {
            'name': 'New Laptop',
            'unit_price': 500,
            'cost_price': 600  # Unit price < cost price
        }
        form = ProductForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('unit_price', form.errors)

    def test_stock_movement_form_valid(self):
        form_data = {
            'product': self.product1.id,
            'movement_type': 'purchase',
            'quantity': 5
        }
        form = StockMovementForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

    # View Tests
    def test_product_list_view(self):
        response = self.client.get(reverse('inventory:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Premium Laptop")
        self.assertContains(response, "Budget Laptop")
        self.assertTemplateUsed(response, 'inventory/product_list.html')

    def test_product_list_view_filtering(self):
        # Test category filter
        response = self.client.get(
            reverse('inventory:product_list') + f'?category={self.category.id}'
        )
        self.assertContains(response, "Premium Laptop")
        
        # Test low stock filter
        response = self.client.get(
            reverse('inventory:product_list') + '?stock_status=low'
        )
        self.assertContains(response, "Budget Laptop")
        self.assertNotContains(response, "Premium Laptop")

    def test_product_detail_view(self):
        response = self.client.get(self.product1.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1299.99")
        self.assertContains(response, "Tech Supplier")
        self.assertTemplateUsed(response, 'inventory/product_detail.html')

    def test_product_create_view(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('inventory:product_create'), {
            'name': 'New Product',
            'category': self.category.id,
            'supplier': self.supplier.id,
            'unit_price': 799.99,
            'cost_price': 599.99,
            'quantity': 10,
            'reorder_level': 3,
            'is_active': True
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(name='New Product').exists())

    def test_stock_movement_create_view(self):
        self.client.force_login(self.user)
        initial_qty = self.product1.quantity
        response = self.client.post(reverse('inventory:movement_create'), {
            'product': self.product1.id,
            'movement_type': 'sale',
            'quantity': 2
        })
        self.assertEqual(response.status_code, 302)
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.quantity, initial_qty - 2)

    def test_supplier_detail_view(self):
        response = self.client.get(reverse('inventory:supplier_detail', args=[self.supplier.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tech Supplier")
        self.assertContains(response, "Premium Laptop")

    def test_alert_list_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('inventory:alert_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Low stock alert")

    def test_resolve_alert_view(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('inventory:resolve_alert', args=[self.alert.id]))
        self.assertEqual(response.status_code, 302)
        self.alert.refresh_from_db()
        self.assertTrue(self.alert.is_resolved)

    # Signal Tests
    def test_low_stock_alert_created(self):
        # Product2 already has quantity=3 with reorder_level=5
        alert = InventoryAlert.objects.filter(
            product=self.product2,
            alert_type='low_stock',
            is_resolved=False
        ).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.message, "Low stock alert")

    def test_expiry_alert_created(self):
        # Product2 has expiry_date in 10 days
        alert = InventoryAlert.objects.filter(
            product=self.product2,
            alert_type='expiring',
            is_resolved=False
        ).first()
        self.assertIsNotNone(alert)
        self.assertIn("expires in 10 days", alert.message)

    # Permission Tests
    def test_protected_views_require_login(self):
        urls = [
            reverse('inventory:product_create'),
            reverse('inventory:movement_create'),
            reverse('inventory:supplier_create'),
        ]
        
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/accounts/login/', response.url)