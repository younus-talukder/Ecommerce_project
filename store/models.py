import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'categories'


class Product(models.Model):
    name = models.CharField(max_length=50)
    price = models.DecimalField(default=0, decimal_places=2, max_digits=6)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, default=1)
    description = models.CharField(max_length=250, default='', blank=True, null=True)
    image = models.ImageField(upload_to='uploads/product/')
    #add sales staff
    is_sale = models.BooleanField(default=False)
    sale_price=models.DecimalField(default=0, decimal_places=2, max_digits=6)


    def __str__(self):
        return self.name


def generate_order_number():
    date_part = timezone.now().strftime('%Y%m%d')
    random_part = uuid.uuid4().hex[:10].upper()
    return f'ORD-{date_part}-{random_part}'


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        PROCESSING = 'processing', 'Processing'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
    )
    order_number = models.CharField(
        max_length=32,
        unique=True,
        default=generate_order_number,
        editable=False,
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, default='')
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.order_number

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(subtotal__gte=0),
                name='order_subtotal_nonnegative',
            ),
            models.CheckConstraint(
                condition=models.Q(total__gte=0),
                name='order_total_nonnegative',
            ),
        ]


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        related_name='order_items',
        null=True,
        blank=True,
    )
    product_name = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False,
    )

    def save(self, *args, **kwargs):
        self.line_total = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.product_name} × {self.quantity}'

    class Meta:
        ordering = ['id']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=0),
                name='order_item_unit_price_nonnegative',
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name='order_item_quantity_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(line_total__gte=0),
                name='order_item_line_total_nonnegative',
            ),
        ]

