class Cart:
    def __init__(self, request):
        self.session = request.session

        # Get the current cart from the session
        cart = self.session.get('session_key')

        # If the user is new, create an empty cart
        if not cart:
            cart = self.session['session_key'] = {}

        # Make it available across all pages
        self.cart = cart

    def add(self, product):
        product_id = str(product.id)
        #logic
        if product_id in self.cart:
            pass
        else:
            self.cart[product_id] = {'price' : str(product.price)}

        self.session.modified = True

