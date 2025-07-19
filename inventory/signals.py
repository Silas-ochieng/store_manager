from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Product, InventoryAlert, StockMovement

@receiver(post_save, sender=Product)
def handle_product_stock_changes(sender, instance, created, **kwargs):
    """
    Creates inventory alerts when stock levels change
    """
    # Skip if this is a new product with zero quantity
    if created and instance.quantity == 0:
        return
    
    # Check stock levels
    if instance.quantity == 0:
        alert_type = 'out_of_stock'
        message = f"{instance.name} is out of stock"
    elif instance.quantity <= instance.reorder_level:
        alert_type = 'low_stock'
        message = f"{instance.name} is low on stock (Current: {instance.quantity}, Reorder at: {instance.reorder_level})"
    else:
        # No alert needed for normal stock levels
        return
    
    # Create or update existing unresolved alert
    InventoryAlert.objects.update_or_create(
        product=instance,
        alert_type=alert_type,
        is_resolved=False,
        defaults={
            'message': message,
            'threshold': instance.reorder_level,
            'days_to_expiry': None
        }
    )

@receiver(pre_save, sender=Product)
def check_expiry_dates(sender, instance, **kwargs):
    """
    Creates expiry alerts when products are near expiry
    """
    if not instance.expiry_date:
        return
    
    days_to_expiry = (instance.expiry_date - timezone.now().date()).days
    
    if days_to_expiry < 0:
        alert_type = 'expired'
        message = f"{instance.name} has expired"
    elif days_to_expiry <= 30:  # Alert for products expiring within 30 days
        alert_type = 'expiring'
        message = f"{instance.name} expires in {days_to_expiry} days"
    else:
        # No alert needed for products with distant expiry
        return
    
    # Create or update existing unresolved alert
    InventoryAlert.objects.update_or_create(
        product=instance,
        alert_type=alert_type,
        is_resolved=False,
        defaults={
            'message': message,
            'threshold': None,
            'days_to_expiry': days_to_expiry
        }
    )

@receiver(post_save, sender=StockMovement)
def resolve_related_alerts(sender, instance, created, **kwargs):
    """
    Automatically resolves stock-related alerts when stock is replenished
    """
    product = instance.product
    
    # Only check for purchase or return movements that increase stock
    if instance.movement_type not in ['purchase', 'return']:
        return
    
    # Check if stock is now above reorder level
    if product.quantity > product.reorder_level:
        # Resolve all low/out of stock alerts for this product
        InventoryAlert.objects.filter(
            product=product,
            alert_type__in=['low_stock', 'out_of_stock'],
            is_resolved=False
        ).update(
            is_resolved=True,
            resolved_at=timezone.now()
        )

@receiver(pre_save, sender=InventoryAlert)
def set_resolved_by(sender, instance, **kwargs):
    """
    Automatically sets the resolving user when an alert is marked as resolved
    """
    if instance.is_resolved and not instance.resolved_by:
        # You'll need to determine the current user here
        # This requires access to the request object, which isn't available in signals
        # Consider using middleware or passing the user in the save method instead
        pass