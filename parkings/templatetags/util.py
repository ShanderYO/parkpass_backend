from django import template

from parkings.models import ParkingSession
from payments.models import TinkoffPayment, Order, HomeBankPayment
from rps_vendor.models import Developer, RpsSubscription, RpsParkingCardSession

register = template.Library()

@register.filter
def isDeveloperPage(original):
    return isinstance(original, Developer)

@register.filter
def isParkingSessionPage(original):
    return isinstance(original, ParkingSession)

@register.filter
def isRpsSubscriptionPage(original):
    return isinstance(original, RpsSubscription)

@register.filter
def isRpsParkingCardSessionPage(original):
    return isinstance(original, RpsParkingCardSession)

@register.inclusion_tag('tags/orderAndPayments.html')
def show_session_order_and_payments(original):
    orders = Order.objects.filter(session_id=original.id).values_list('id')
    payments = TinkoffPayment.objects.filter(order_id__in=orders).values_list('id')
    homebank_payments = HomeBankPayment.objects.filter(order_id__in=orders).values_list('id')

    return {'payments': payments, 'homebank_payments': homebank_payments, 'orders': orders}

@register.inclusion_tag('tags/orderAndPayments.html')
def show_subscription_order_and_payments(original):
    orders = Order.objects.filter(subscription_id=original.id).values_list('id')
    payments = TinkoffPayment.objects.filter(order_id__in=orders).values_list('id')
    homebank_payments = HomeBankPayment.objects.filter(order_id__in=orders).values_list('id')

    return {'payments': payments, 'homebank_payments': homebank_payments, 'orders': orders}

@register.inclusion_tag('tags/orderAndPayments.html')
def show_card_order_and_payments(original):
    orders = Order.objects.filter(parking_card_session_id=original.id).values_list('id')
    payments = TinkoffPayment.objects.filter(order_id__in=orders).values_list('id')
    homebank_payments = HomeBankPayment.objects.filter(order_id__in=orders).values_list('id')

    return {'payments': payments, 'homebank_payments': homebank_payments, 'orders': orders}