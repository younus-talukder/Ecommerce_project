from .cart import Cart

# context processor for work cart in all pages

def cart(request):
    # return the default data from our cart
    return {'cart': Cart(request)}

