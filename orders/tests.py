from django.test import TestCase
from django.urls import reverse
from inventory.models import Product
from .models import Customer, Order, OrderItem

class OrdersTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(
            name="Test Product", 
            price=50.00,
            quantity=10
        )
        cls.customer = Customer.objects.create(
            name="Test Customer",
            email="test@example.com"
        )
        cls.order = Order.objects.create(
            customer=cls.customer,
            total=100.00
        )
        OrderItem.objects.create(
            order=cls.order,
            product=cls.product,
            quantity=2,
            price=50.00
        )

    def test_customer_str(self):
        self.assertEqual(str(self.customer), "Test Customer")

    def test_order_str(self):
        self.assertEqual(str(self.order), f"Order #{self.order.id} - Test Customer")

    def test_order_item_str(self):
        item = OrderItem.objects.first()
        self.assertEqual(str(item), "2 x Test Product")

    def test_order_total(self):
        self.order.update_total()
        self.assertEqual(self.order.total, 100.00)

    def test_order_list_view(self):
        response = self.client.get(reverse('orders:order_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Order #{self.order.id}")