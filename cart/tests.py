from decimal import Decimal

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from store.models import Category, Product


class CartViewsTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name='Test category')
        self.regular_product = Product.objects.create(
            name='Regular product',
            price=Decimal('20.00'),
            category=category,
            image='uploads/product/test-regular.jpg',
        )
        self.sale_product = Product.objects.create(
            name='Sale product',
            price=Decimal('30.00'),
            category=category,
            image='uploads/product/test-sale.jpg',
            is_sale=True,
            sale_price=Decimal('12.50'),
        )

    def ajax_post(self, url_name, data):
        return self.client.post(
            reverse(url_name),
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

    def test_add_uses_quantity_and_increments_existing_item(self):
        response = self.ajax_post(
            'cart_add',
            {'product_id': self.regular_product.id, 'quantity': 2},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['cart_quantity'], 2)

        response = self.ajax_post(
            'cart_add',
            {'product_id': self.regular_product.id, 'quantity': 1},
        )
        self.assertEqual(response.json()['quantity'], 3)
        self.assertEqual(
            self.client.session['cart'][str(self.regular_product.id)]['quantity'],
            3,
        )

    def test_sale_product_uses_sale_price(self):
        self.ajax_post(
            'cart_add',
            {'product_id': self.sale_product.id, 'quantity': 2},
        )

        stored_item = self.client.session['cart'][str(self.sale_product.id)]
        self.assertEqual(stored_item['price'], '12.50')

        # Existing carts created by the old implementation are corrected too.
        session = self.client.session
        session['cart'][str(self.sale_product.id)]['price'] = '30.00'
        session.save()

        response = self.client.get(reverse('cart_summary'))
        self.assertContains(response, '$25.00')

    def test_update_and_remove_cart_item(self):
        self.ajax_post('cart_add', {'product_id': self.regular_product.id})

        response = self.client.post(
            reverse('cart_update'),
            {'product_id': self.regular_product.id, 'quantity': 4},
        )
        self.assertRedirects(response, reverse('cart_summary'))
        self.assertEqual(
            self.client.session['cart'][str(self.regular_product.id)]['quantity'],
            4,
        )

        response = self.client.post(
            reverse('cart_delete'),
            {'product_id': self.regular_product.id},
        )
        self.assertRedirects(response, reverse('cart_summary'))
        self.assertNotIn(str(self.regular_product.id), self.client.session['cart'])

    def test_summary_renders_items_totals_and_cart_badge(self):
        self.ajax_post(
            'cart_add',
            {'product_id': self.regular_product.id, 'quantity': 2},
        )
        self.ajax_post(
            'cart_add',
            {'product_id': self.sale_product.id, 'quantity': 1},
        )

        response = self.client.get(reverse('cart_summary'))
        self.assertContains(response, self.regular_product.name)
        self.assertContains(response, self.sale_product.name)
        self.assertContains(response, '$52.50')
        self.assertContains(response, 'id="cart_quantity"')
        self.assertContains(response, '>3</span>', html=False)

    def test_invalid_cart_requests_are_rejected_safely(self):
        response = self.ajax_post('cart_add', {'quantity': 1})
        self.assertEqual(response.status_code, 400)

        response = self.ajax_post(
            'cart_add',
            {'product_id': 999999, 'quantity': 1},
        )
        self.assertEqual(response.status_code, 404)

        response = self.ajax_post(
            'cart_add',
            {'product_id': self.regular_product.id, 'quantity': 0},
        )
        self.assertEqual(response.status_code, 400)

        self.assertEqual(self.client.get(reverse('cart_add')).status_code, 405)
        self.assertEqual(self.client.get(reverse('cart_update')).status_code, 405)
        self.assertEqual(self.client.get(reverse('cart_delete')).status_code, 405)

    def test_rendering_does_not_create_an_empty_cart_session(self):
        response = self.client.get(reverse('home'))
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)
