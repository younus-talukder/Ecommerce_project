# cart/cart.py
from decimal import Decimal

class Cart:
    CART_SESSION_ID = 'cart'   # session key

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(self.CART_SESSION_ID)
        if not cart:
            cart = self.session[self.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, update_quantity=False):
        """
        Add a product to the cart or update its quantity.
        """
        product_id = str(product.id)
        if product_id in self.cart:
            if update_quantity:
                self.cart[product_id]['quantity'] = quantity
        else:
            # store price as string for JSON serializability in session
            self.cart[product_id] = {'price': str(product.price), 'quantity': quantity}
        self.save()

    def save(self):
        """Mark the session as modified (so Django saves it)."""
        self.session.modified = True

    def remove(self, product):
        """Remove a product from the cart."""
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        """
        Iterate over the items in the cart, yielding dictionaries containing:
        { 'product': Product instance, 'quantity': int, 'price': Decimal, 'total_price': Decimal }
        """
        # import here to avoid DB access at module import time
        from store.models import Product

        product_ids = list(self.cart.keys())
        # fetch existing product objects in one query
        products = Product.objects.filter(id__in=product_ids)
        product_map = {str(p.id): p for p in products}

        # yield a copy so modifications don't affect session data unexpectedly
        for pid, item in list(self.cart.items()):
            product = product_map.get(pid)
            if product:
                price = Decimal(item.get('price', '0'))
                qty = item.get('quantity', 1)
                yield {
                    'product': product,
                    'quantity': qty,
                    'price': price,
                    'total_price': price * qty
                }
            else:
                # product was removed from DB — delete it from session cart
                del self.cart[pid]
                self.save()

    def __len__(self):
        """Return total number of items (sum of quantities)."""
        return sum(item.get('quantity', 1) for item in self.cart.values())

    def items(self):
        """Return a list of cart items (materialized iterator)."""
        return list(self.__iter__())

    def get_total_price(self):
        """Return total price for the cart as Decimal."""
        total = Decimal('0')
        for item in self.__iter__():
            total += item['total_price']
        return total

    def clear(self):
        """Empty the cart from
        the session."""
        self.session.pop(self.CART_SESSION_ID, None)
        self.save()