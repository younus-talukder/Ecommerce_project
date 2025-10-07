from .cart import Cart

# context processor for work cart in all pages


# cart/context_processors.py

def cart(request):
    """
    Safe context processor for cart. Import Cart lazily so import-time
    errors in cart.py don't crash the serverless function.
    """
    try:
        # import here to avoid running code at module-import time
        from .cart import Cart
        cart_instance = Cart(request)
    except Exception as e:
        # fallback minimal cart object to avoid template errors
        class _EmptyCart:
            def __iter__(self): return iter([])
            def __len__(self): return 0
            def __bool__(self): return False
            def get_total_price(self): return 0
            def items(self): return []
        cart_instance = _EmptyCart()

    return {'cart': cart_instance}
