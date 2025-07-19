from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from orders.models import OrderItem
import logging

logger = logging.getLogger(__name__)

def update_order_total_safe(order):
    try:
        order.update_total()
        logger.debug(f"Updated total for Order #{order.id}")
    except Exception as e:
        logger.error(f"Failed to update total for Order #{order.id if order else 'N/A'}: {e}")

@receiver([post_save, post_delete], sender=OrderItem)
def update_order_total_on_change(sender, instance, **kwargs):
    if instance.order:
        update_order_total_safe(instance.order)
