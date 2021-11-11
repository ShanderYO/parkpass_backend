import base64

from django import template

from accounts.models import Account
from notifications.models import Mailing
from parkings.models import ParkingSession, Parking
from payments.models import TinkoffPayment, Order, HomeBankPayment, CreditCard
from rps_vendor.models import Developer, RpsSubscription, RpsParkingCardSession, RpsParking
from django.utils.html import escape
register = template.Library()

@register.filter
def isDeveloperPage(original):
    return isinstance(original, Developer)

@register.filter
def isRpsParking(original):
    return isinstance(original, RpsParking)

@register.filter
def isParkingSessionPage(original):
    return isinstance(original, ParkingSession)

@register.filter
def isRpsSubscriptionPage(original):
    return isinstance(original, RpsSubscription)

@register.filter
def isParkingPage(original):
    return isinstance(original, Parking)

@register.filter
def isRpsParkingCardSessionPage(original):
    return isinstance(original, RpsParkingCardSession)

@register.filter
def isAccountPage(original):
    return isinstance(original, Account)

@register.filter
def isMailingPage(original):
    return isinstance(original, Mailing)

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

@register.inclusion_tag('tags/bindedCreditCards.html')
def show_bind_credit_cards(original):
    credit_cards = CreditCard.objects.filter(account_id=original.id).values_list('id')
    return {'credit_cards': credit_cards}


@register.inclusion_tag('tags/payWidget.html')
def generate_widget(original):
    encoded_id = base64.b64encode(bytes(str(original.id), 'utf-8')).decode("utf-8")
    # html = escape('\n'
    #               '<button id="parkpass-widget-button">parkpass widget</button>\n'
    # '<script src="https://static.x4.digital/pp-widget/dist/widget.js"></script>\n'
    # '<script>\n'
    # '   var wrapper = document.createElement("div");\n'
    # '   wrapper.innerHTML = "<parkpasspayment-widget pid=\'%s\'></parkpasspayment-widget>";\n'
    # '   document.getElementsByTagName("body")[0].appendChild(wrapper);\n'
    # '</script>' % encoded_id)

    html = escape('\n'
    '<div id="parkpass-widget-wrapper"></div>\n'
    '<script src="https://static.x4.digital/pp-widget/dist/widget.js"></script>\n'
    '<script>\n'
      '     document.getElementById("parkpass-widget-wrapper").innerHTML="<parkpasspayment-widget pid=\'%s\'></parkpasspayment-widget>";\n'
    '</script>' % encoded_id)
    return {'html': html}

