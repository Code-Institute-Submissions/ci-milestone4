from django.shortcuts import (
    render, redirect, reverse, get_object_or_404, HttpResponse
)
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings

from .forms import OrderForm
from .models import Order, OrderLineItem, OrderStatus

from products.models import ProductStock
from profiles.models import UserProfile
from profiles.forms import UserProfileForm
from bag.contexts import bag_contents

import stripe
import json

from stripe import PaymentIntent


@require_POST
def cache_checkout_data(request):
    try:
        pid = request.POST.get('client_secret').split('_secret')[0]
        stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe.PaymentIntent.modify(pid, metadata={
            'bag': json.dumps(request.session.get('bag', {})),
            'save_info': request.POST.get('save_info'),
            'username': request.user,
        })
        return HttpResponse(status=200)
    except Exception as e:
        messages.error(request, ('Sorry, your payment cannot be '
                                 'processed right now. Please try '
                                 'again later.'))
        return HttpResponse(content=e, status=400)


def checkout(request):
    stripe_public_key = settings.STRIPE_PUBLIC_KEY
    stripe_secret_key = settings.STRIPE_SECRET_KEY

    if request.method == 'POST':
        # Get's bag from session
        bag = request.session.get('bag', {})

        # Get POSTed form data
        form_data = {
            'name_full': request.POST['name_full'],
            'email': request.POST['email'],
            'tel': request.POST['tel'],
            'street_address1': request.POST['street_address1'],
            'street_address2': request.POST['street_address2'],
            'city': request.POST['city'],
            'county': request.POST['county'],
            'country': request.POST['country'],
            'postcode': request.POST['postcode'],
        }

        # Check form data is valid
        order_form = OrderForm(form_data)
        processing_status = OrderStatus.objects.get(status_code="processing")
        if order_form.is_valid():
            # Create the Order record
            order = order_form.save(commit=False)
            pid = request.POST.get('client_secret').split('_secret')[0]
            order.stripe_pid = pid
            # Stores a record of the bag data
            order.original_bag = json.dumps(bag)
            # Sets order_status to Processing
            order.order_status = processing_status
            order.creation_method = 'View'
            order.save()
            # Attach the Line Items to the Order
            for item_id, item_data in bag.items():
                # Check Bag line item is an existing product line...
                try:
                    product_line = ProductStock.objects.get(id=item_id)
                    # Penultimate stock check
                    product_line.reserve_stock(item_data)
                    order_line_item = OrderLineItem(
                        order=order,
                        product_line=product_line,
                        quantity=item_data,
                    )
                    order_line_item.save()
                # ... reject with error and delete Order record if
                # product line not found
                except product_line.DoesNotExist:
                    messages.error(request, (
                        "One of the products in your bag wasn't "
                        "found in our database. "
                        "Please call us for assistance!")
                    )
                    order.delete()
                    PaymentIntent.cancel(pid, cancellation_reason='abandoned')
                    return redirect(reverse('view_bag'))
                except ValueError as e:
                    messages.error(request, e)
                    order.delete()
                    PaymentIntent.cancel(pid, cancellation_reason='abandoned')
                    return redirect(reverse('view_bag'))

            # Save the info to the user's profile if all is well
            request.session['save_info'] = 'save-info' in request.POST
            PaymentIntent.capture(pid)
            return redirect(reverse('checkout_success',
                                    args=[order.order_number]))
        # Error if form is invalid
        else:
            messages.error(request, ('There was an error with your form. '
                                     'Please double check your information.'))

    # Non-POST actions
    else:
        # Get's bag from session
        bag = request.session.get('bag', {})
        # Errors if bag is empty
        if not bag:
            messages.error(request,
                           "There's nothing in your bag at the moment")
            return redirect(reverse('products'))

        # Checking bag contents and stock pre-check
        for item_id, item_data in bag.items():
            # Check Bag line item is an existing product line...
            try:
                product_line = ProductStock.objects.get(id=item_id)
                product_line.reserve_stock(item_data, dry_run=True)
            # ... reject with error if product line not found
            except product_line.DoesNotExist:
                messages.error(request, (
                    "One of the products in your bag wasn't "
                    "found in our database. "
                    "Please call us for assistance!")
                )
                return redirect(reverse('view_bag'))
            # Raise error if stock check fails
            except ValueError as e:
                messages.error(request, e)
                return redirect(reverse('view_bag'))

        # Gets bag context object
        current_bag = bag_contents(request)
        total = current_bag['grand_total']
        # Stripe requires decimals as an integer (e.g. £9.90 is £990)
        stripe_total = round(total * 100)
        stripe.api_key = stripe_secret_key
        intent = stripe.PaymentIntent.create(
            amount=stripe_total,
            currency=settings.STRIPE_CURRENCY,
            capture_method='manual'
        )

        # Attempt to prefill the form with any info
        # the user maintains in their profile
        if request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(user=request.user)
                order_form = OrderForm(initial={
                    'name_full': profile.user.get_full_name(),
                    'email': profile.user.email,
                    'tel': profile.user_tel,
                    'street_address1': profile.user_street_address1,
                    'street_address2': profile.user_street_address2,
                    'county': profile.user_county,
                    'city': profile.user_city,
                    'country': profile.user_country,
                    'postcode': profile.user_postcode,
                })
            except UserProfile.DoesNotExist:
                order_form = OrderForm()
        else:
            order_form = OrderForm()

    # Error if Stripe key missing
    if not stripe_public_key:
        messages.warning(request, ('Stripe public key is missing. '
                                   'Did you forget to set it in '
                                   'your environment?'))

    template = 'checkout/checkout.html'
    context = {
        'order_form': order_form,
        'stripe_public_key': stripe_public_key,
        'client_secret': intent.client_secret,
    }

    return render(request, template, context)


def checkout_success(request, order_number):
    """
    Handle successful checkouts
    """
    # 'Save my details' checkbox on form
    save_info = request.session.get('save_info')
    order = get_object_or_404(Order, order_number=order_number)

    if request.user.is_authenticated:
        profile = UserProfile.objects.get(user=request.user)
        # Attach the user's profile to the order
        order.user_profile = profile
        order.save()

        # Save the user's info, if user ticked checkbox on form
        if save_info:
            profile_data = {
                'user_tel': order.tel,
                'user_street_address1': order.street_address1,
                'user_street_address2': order.street_address2,
                'user_city': order.city,
                'user_county': order.county,
                'user_country': order.country,
                'user_postcode': order.postcode,
            }
            user_profile_form = UserProfileForm(profile_data, instance=profile)
            if user_profile_form.is_valid():
                user_profile_form.save()

    messages.success(request, f'Order successfully processed! \
        Your order number is {order_number}. A confirmation \
        email will be sent to {order.email}.')

    # Clears bag from session
    if 'bag' in request.session:
        del request.session['bag']

    template = 'checkout/checkout_success.html'
    context = {
        'order': order,
    }

    return render(request, template, context)
