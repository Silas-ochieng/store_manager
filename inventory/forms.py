from django import forms
from .models import InventoryAlert
from .models import Product, Category, Supplier, StockMovement, ProductImage
from django.core.exceptions import ValidationError
from django.utils import timezone

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        exclude = ['slug', 'created_at', 'updated_at']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'cost_price': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'manufacture_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tax_rate': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        self.fields['supplier'].queryset = Supplier.objects.filter(is_active=True)
        
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field_name not in ['is_active'] and not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'

    def clean(self):
        cleaned_data = super().clean()
        unit_price = cleaned_data.get('unit_price')
        cost_price = cleaned_data.get('cost_price')
        expiry_date = cleaned_data.get('expiry_date')
        manufacture_date = cleaned_data.get('manufacture_date')

        if unit_price and cost_price and unit_price < cost_price:
            self.add_error('unit_price', "Unit price cannot be less than cost price")

        if expiry_date and manufacture_date and expiry_date < manufacture_date:
            self.add_error('expiry_date', "Expiry date cannot be before manufacture date")

        if expiry_date and expiry_date < timezone.now().date():
            self.add_error('expiry_date', "Expiry date cannot be in the past")

        return cleaned_data

class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'movement_type', 'quantity', 'unit_price', 'reference', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only show active products
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
        
        # Set initial unit price from product if available
        if 'product' in self.initial:
            product = Product.objects.get(pk=self.initial['product'])
            self.fields['unit_price'].initial = product.unit_price

        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        movement_type = cleaned_data.get('movement_type')

        if product and quantity:
            if movement_type in ['sale', 'adjustment', 'loss'] and quantity > product.quantity:
                self.add_error('quantity', f"Not enough stock. Available: {product.quantity}")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.created_by = self.user
        
        if commit:
            instance.save()
        return instance

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        exclude = ['slug', 'created_at', 'updated_at']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude current instance from parent choices to prevent circular hierarchy
        if self.instance.pk:
            self.fields['parent'].queryset = Category.objects.exclude(pk=self.instance.pk)
        else:
            self.fields['parent'].queryset = Category.objects.all()

        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if field_name not in ['is_active'] and not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'

class InventoryAlertForm(forms.ModelForm):
    class Meta:
        model = InventoryAlert
        fields = ['product', 'alert_type', 'message', 'is_resolved']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = self.fields['product'].queryset.filter(is_active=True)                

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        exclude = ['created_at', 'updated_at']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if field_name not in ['is_active'] and not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and Supplier.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("A supplier with this email already exists.")
        return email

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'is_default', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'class': 'form-control'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].widget.attrs.update({'class': 'form-control'})