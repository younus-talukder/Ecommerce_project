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
