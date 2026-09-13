from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from cart.cart import Cart

from .forms import CheckoutForm, SignUpForm
from .models import Category, Order, OrderItem, Product


def category(request, foo):
    # replace hyphen with space
    foo = foo.replace('-',' ')
    # grab the category from the url
    try:
        category_object = Category.objects.get(name=foo)
    except Category.DoesNotExist:
        messages.error(request, "Category does not exist.")
        return redirect('home')

    products = Product.objects.filter(category=category_object)
    return render(
        request,
        'category.html',
        {'products': products, 'category': category_object},
    )

def product(request, pk):
    product_object = get_object_or_404(Product, id=pk)
    return render(request, 'product.html', {'product': product_object})

# Create your views here.
def home(request):
    products = Product.objects.all()

    return render(request, 'home.html', {'products': products})


def about(request):
    return render(request, 'about.html', {})


def login_user(request):
    next_url = request.POST.get('next') or request.GET.get('next', '')

    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        if not username or not password:
            messages.error(request, "Username and password are required.")
            return render(request, 'login.html', {'next': next_url})

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "you have been logged in")
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('home')

        messages.error(request, "Invalid username or password.")
        return render(request, 'login.html', {'next': next_url})

    return render(request, 'login.html', {'next': next_url})


@require_POST
def logout_user(request):
    logout(request)
    messages.success(request, "Log out successful")
    return redirect('home')


def register_user(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')  # ✅ correct field

            # authenticate and login
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "You have registered successfully!")
                return redirect('home')
        else:
            # instead of redirect, re-render with errors
            messages.error(request, "There was an error with your registration.")
            return render(request, 'register.html', {'form': form})
    else:
        form = SignUpForm()

    return render(request, 'register.html', {'form': form})


def _checkout_lines(cart_items):
    lines = []
    subtotal = Decimal('0.00')

    for item in cart_items:
        product_object = item['product']
        quantity = int(item['quantity'])
        unit_price = (
            product_object.sale_price
            if product_object.is_sale
            else product_object.price
        )
        line_total = unit_price * quantity
        subtotal += line_total
        lines.append(
            {
                'product': product_object,
                'product_name': product_object.name,
                'unit_price': unit_price,
                'quantity': quantity,
                'line_total': line_total,
            }
        )

    return lines, subtotal


@login_required(login_url='login')
@require_http_methods(['GET', 'POST'])
def checkout(request):
    cart = Cart(request)
    cart_items = list(cart)
    if not cart_items:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart_summary')

    checkout_lines, subtotal = _checkout_lines(cart_items)
    initial = {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,
    }
    form = CheckoutForm(request.POST or None, initial=initial)

    if request.method == 'POST' and form.is_valid():
        # Re-read the cart and authoritative product prices immediately before
        # entering the transaction so no totals come from browser input.
        cart_items = list(Cart(request))
        if not cart_items:
            messages.warning(request, 'Your cart is empty.')
            return redirect('cart_summary')
        checkout_lines, subtotal = _checkout_lines(cart_items)

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                phone=form.cleaned_data['phone'],
                address_line_1=form.cleaned_data['address_line_1'],
                address_line_2=form.cleaned_data['address_line_2'],
                city=form.cleaned_data['city'],
                postal_code=form.cleaned_data['postal_code'],
                subtotal=subtotal,
                total=subtotal,
            )
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product=line['product'],
                        product_name=line['product_name'],
                        unit_price=line['unit_price'],
                        quantity=line['quantity'],
                        line_total=line['line_total'],
                    )
                    for line in checkout_lines
                ]
            )

        cart.clear()
        return redirect('order_confirmation', order_number=order.order_number)

    return render(
        request,
        'checkout.html',
        {
            'form': form,
            'checkout_lines': checkout_lines,
            'subtotal': subtotal,
            'total': subtotal,
        },
    )


@login_required(login_url='login')
def order_confirmation(request, order_number):
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        order_number=order_number,
        user=request.user,
    )
    return render(
        request,
        'order_detail.html',
        {'order': order, 'is_confirmation': True},
    )


@login_required(login_url='login')
def order_history(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'order_history.html', {'orders': orders})


@login_required(login_url='login')
def order_detail(request, order_number):
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        order_number=order_number,
        user=request.user,
    )
    return render(request, 'order_detail.html', {'order': order})

