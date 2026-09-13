from django.contrib import admin

from store.models import Category, Order, OrderItem, Product

admin.site.register(Category)
admin.site.register(Product)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ('product', 'product_name', 'unit_price', 'quantity', 'line_total')
    readonly_fields = fields


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'user',
        'first_name',
        'last_name',
        'total',
        'status',
        'created_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = (
        'order_number',
        'user__username',
        'first_name',
        'last_name',
        'email',
        'phone',
    )
    ordering = ('-created_at',)
    list_select_related = ('user',)
    readonly_fields = ('order_number', 'subtotal', 'total', 'created_at', 'updated_at')
    inlines = (OrderItemInline,)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'order', 'unit_price', 'quantity', 'line_total')
    list_filter = ('order__status',)
    search_fields = ('product_name', 'order__order_number')
    ordering = ('-order__created_at', 'id')
    list_select_related = ('order', 'product')
    readonly_fields = (
        'order',
        'product',
        'product_name',
        'unit_price',
        'quantity',
        'line_total',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
