from django.db import transaction
from .models import Category

def create_initial_data(sender, **kwargs):
    """
    Create initial inventory data after migrations
    """
    with transaction.atomic():
        # Create root categories if they don't exist
        if not Category.objects.exists():
            Category.objects.bulk_create([
                Category(name="Uncategorized", slug="uncategorized", is_active=True),
                Category(name="Electronics", slug="electronics", is_active=True),
                Category(name="Clothing", slug="clothing", is_active=True),
                Category(name="Office Supplies", slug="office-supplies", is_active=True),
            ])
            print("Created initial inventory categories")