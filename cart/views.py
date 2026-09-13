from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .cart import Cart
from store.models import Product


def cart_summary(request):
    return render(request, 'cart_summary.html')


def _positive_quantity(request, default=None):
    raw_quantity = request.POST.get('quantity', default)
    try:
        quantity = int(raw_quantity)
    except (TypeError, ValueError):
        return None
    return quantity if quantity > 0 else None


def _product_from_request(request):
    raw_product_id = request.POST.get('product_id')
    try:
        product_id = int(raw_product_id)
    except (TypeError, ValueError):
        return None
    if product_id < 1:
        return None
    return get_object_or_404(Product, id=product_id)


def _success_response(request, payload, message):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse(payload)
    messages.success(request, message)
    return redirect('cart_summary')


@require_POST
def cart_add(request):
    cart = Cart(request)
    product = _product_from_request(request)
    if product is None:
        return JsonResponse({'error': 'A valid product ID is required.'}, status=400)

    quantity = _positive_quantity(request, default=1)
    if quantity is None:
        return JsonResponse({'error': 'Quantity must be a positive integer.'}, status=400)

    cart.add(product=product, quantity=quantity)
    return _success_response(
        request,
        {
            'product_name': product.name,
            'quantity': cart.get_quantity(product),
            'cart_quantity': len(cart),
        },
        f'{product.name} was added to your cart.',
    )


@require_POST
def cart_delete(request):
    cart = Cart(request)
    product = _product_from_request(request)
    if product is None:
        return JsonResponse({'error': 'A valid product ID is required.'}, status=400)

    cart.remove(product)
    return _success_response(
        request,
        {'cart_quantity': len(cart)},
        f'{product.name} was removed from your cart.',
    )


@require_POST
def cart_update(request):
    cart = Cart(request)
    product = _product_from_request(request)
    if product is None:
        return JsonResponse({'error': 'A valid product ID is required.'}, status=400)
    if not cart.contains(product):
        return JsonResponse({'error': 'Product is not in the cart.'}, status=404)

    quantity = _positive_quantity(request)
    if quantity is None:
        return JsonResponse({'error': 'Quantity must be a positive integer.'}, status=400)

    cart.add(product=product, quantity=quantity, update_quantity=True)
    return _success_response(
        request,
        {'quantity': quantity, 'cart_quantity': len(cart)},
        f'{product.name} quantity was updated.',
    )


# Create your views here.
