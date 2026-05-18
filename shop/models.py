from django.db import models
from django.conf import settings
from clinic.models import Customer

class ShopCustomer(Customer):
    class Meta:
        proxy = True
        verbose_name = 'Do\'kon Mijozi'
        verbose_name_plural = 'Do\'kon Mijozlari'


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact = models.CharField(max_length=100, blank=True)
    history = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class ConsumableSet(models.Model):
    """Defines a set of consumables used for a procedure"""
    title = models.CharField(max_length=100, help_text="e.g. 'Jarrohlik To'plami', 'Vaksina To'plami'")
    # We will link items via ManyToMany or a through model to Product
    # But for now, let's keep it simple: A set has many items.
    
    def __str__(self):
        return self.title

class ConsumableItem(models.Model):
    consumable_set = models.ForeignKey(ConsumableSet, on_delete=models.CASCADE, related_name='items')
    # Use string reference to Product to avoid definition order issues if placed before Product
    product = models.ForeignKey('Product', on_delete=models.CASCADE) 
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.consumable_set.title}"

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=20, decimal_places=2)
    stock = models.IntegerField(default=0)
    min_stock = models.IntegerField(default=5, help_text="Sklad ogohlantirish chegarasi")
    discount_percent = models.IntegerField(default=0, help_text="Chegirma foizi (0-100)")
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    barcode = models.CharField(max_length=50, blank=True, null=True, unique=True)
    notified_low_stock = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    @property
    def discounted_price(self):
        """Calculate price after discount"""
        if self.discount_percent > 0:
            discount_amount = (self.price * self.discount_percent) / 100
            return self.price - discount_amount
        return self.price

class ProductBatch(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches')
    batch_id = models.CharField(max_length=50)
    expiry_date = models.DateField()
    quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.product.name} ({self.batch_id}) - Exp: {self.expiry_date}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('PREPARING', 'Preparing'),
        ('ON_WAY', 'On Way'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]

    SOURCE_CHOICES = [
        ('POS', 'POS'),
        ('TELEGRAM_BOT', 'Telegram Bot'),
    ]

    PAYMENT_CHOICES = [
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    customer_name = models.CharField(max_length=255, blank=True, help_text="For guest/web app users")
    total_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='POS')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='CASH')
    payment_proof = models.ImageField(upload_to='payments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    courier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    bonus_credited = models.BooleanField(default=False)
    coupon_code = models.CharField(max_length=20, blank=True, null=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._old_status = self.status

    def __str__(self):
        name = self.customer.name if self.customer else self.customer_name or "Mijozsiz"
        return f"Order #{self.id} - {name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=20, decimal_places=2) # Price at the time of purchase

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
