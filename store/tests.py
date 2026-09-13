from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Category, Order, Product


class StoreViewTests(TestCase):
    def test_missing_product_returns_404(self):
        response = self.client.get(reverse('product', args=[999999]))
        self.assertEqual(response.status_code, 404)

    def test_missing_category_redirects_home(self):
        response = self.client.get(reverse('category', args=['Missing']))
        self.assertRedirects(response, reverse('home'))

    def test_logout_requires_post(self):
        user = get_user_model().objects.create_user(
            username='shopper',
            password='a-secure-test-password',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_honors_safe_next_url(self):
        get_user_model().objects.create_user(
            username='returning-shopper',
            password='a-secure-test-password',
        )
        response = self.client.post(
            reverse('login'),
            {
                'username': 'returning-shopper',
                'password': 'a-secure-test-password',
                'next': reverse('checkout'),
            },
        )
        self.assertRedirects(
            response,
            reverse('checkout'),
            fetch_redirect_response=False,
        )


class CheckoutTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='buyer',
            password='a-secure-test-password',
            first_name='Test',
            last_name='Buyer',
            email='buyer@example.com',
        )
        self.other_user = get_user_model().objects.create_user(
            username='other-buyer',
            password='another-secure-password',
        )
        category = Category.objects.create(name='Checkout category')
        self.regular_product = Product.objects.create(
            name='Regular checkout product',
            price=Decimal('20.00'),
            category=category,
            image='uploads/product/checkout-regular.jpg',
        )
        self.sale_product = Product.objects.create(
            name='Sale checkout product',
            price=Decimal('30.00'),
            category=category,
            image='uploads/product/checkout-sale.jpg',
            is_sale=True,
            sale_price=Decimal('12.50'),
        )
        self.checkout_data = {
            'first_name': 'Test',
            'last_name': 'Buyer',
            'email': 'buyer@example.com',
            'phone': '+8801700000000',
            'address_line_1': '123 Test Road',
            'address_line_2': 'Apartment 4',
            'city': 'Dhaka',
            'postal_code': '1207',
        }

    def add_to_cart(self, product, quantity=1):
        return self.client.post(
            reverse('cart_add'),
            {'product_id': product.id, 'quantity': quantity},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

    def place_order(self):
        return self.client.post(reverse('checkout'), self.checkout_data)

    def test_anonymous_checkout_redirects_to_login_with_next(self):
        response = self.client.get(reverse('checkout'))
        expected = f"{reverse('login')}?next={reverse('checkout')}"
        self.assertRedirects(response, expected, fetch_redirect_response=False)

    def test_empty_cart_cannot_checkout(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('checkout'))
        self.assertRedirects(response, reverse('cart_summary'))
        self.assertEqual(Order.objects.count(), 0)

    def test_valid_checkout_creates_order_items_totals_and_clears_cart(self):
        self.client.force_login(self.user)
        self.add_to_cart(self.regular_product, quantity=2)
        self.add_to_cart(self.sale_product, quantity=3)

        # A stale/tampered session price must not influence checkout totals.
        session = self.client.session
        session['cart'][str(self.sale_product.id)]['price'] = '0.01'
        session.save()

        response = self.place_order()

        order = Order.objects.get()
        self.assertRedirects(
            response,
            reverse('order_confirmation', args=[order.order_number]),
        )
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.subtotal, Decimal('77.50'))
        self.assertEqual(order.total, Decimal('77.50'))
        self.assertEqual(order.items.count(), 2)

        regular_item = order.items.get(product=self.regular_product)
        self.assertEqual(regular_item.unit_price, Decimal('20.00'))
        self.assertEqual(regular_item.quantity, 2)
        self.assertEqual(regular_item.line_total, Decimal('40.00'))

        sale_item = order.items.get(product=self.sale_product)
        self.assertEqual(sale_item.unit_price, Decimal('12.50'))
        self.assertEqual(sale_item.quantity, 3)
        self.assertEqual(sale_item.line_total, Decimal('37.50'))
        self.assertNotIn('cart', self.client.session)

    def test_invalid_form_creates_no_order_and_preserves_cart(self):
        self.client.force_login(self.user)
        self.add_to_cart(self.regular_product, quantity=2)
        invalid_data = self.checkout_data.copy()
        invalid_data['city'] = ''

        response = self.client.post(reverse('checkout'), invalid_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')
        self.assertEqual(Order.objects.count(), 0)
        self.assertIn('cart', self.client.session)

    def test_order_item_snapshots_survive_product_changes_and_deletion(self):
        self.client.force_login(self.user)
        self.add_to_cart(self.sale_product, quantity=2)
        self.place_order()
        item = Order.objects.get().items.get()

        self.sale_product.name = 'Renamed product'
        self.sale_product.sale_price = Decimal('1.00')
        self.sale_product.save()
        self.sale_product.delete()

        item.refresh_from_db()
        self.assertIsNone(item.product)
        self.assertEqual(item.product_name, 'Sale checkout product')
        self.assertEqual(item.unit_price, Decimal('12.50'))
        self.assertEqual(item.line_total, Decimal('25.00'))

    def test_order_history_only_lists_current_users_orders(self):
        own_order = self.create_order(self.user)
        other_order = self.create_order(self.other_user)
        self.client.force_login(self.user)

        response = self.client.get(reverse('order_history'))

        self.assertContains(response, own_order.order_number)
        self.assertNotContains(response, other_order.order_number)

    def test_user_cannot_access_another_users_order(self):
        other_order = self.create_order(self.other_user)
        self.client.force_login(self.user)

        detail_response = self.client.get(
            reverse('order_detail', args=[other_order.order_number])
        )
        confirmation_response = self.client.get(
            reverse('order_confirmation', args=[other_order.order_number])
        )

        self.assertEqual(detail_response.status_code, 404)
        self.assertEqual(confirmation_response.status_code, 404)

    def test_order_numbers_are_unique(self):
        first_order = self.create_order(self.user)
        second_order = self.create_order(self.user)
        self.assertNotEqual(first_order.order_number, second_order.order_number)

    @staticmethod
    def create_order(user):
        return Order.objects.create(
            user=user,
            first_name='Order',
            last_name='Owner',
            email='owner@example.com',
            phone='+8801700000000',
            address_line_1='123 Test Road',
            city='Dhaka',
            postal_code='1207',
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
        )
