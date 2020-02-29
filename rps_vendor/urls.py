from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from rps_vendor.views import RpsCreateParkingSessionView, RpsCancelParkingSessionView, RpsUpdateParkingSessionView, \
    RpsCompleteParkingSessionView, RpsParkingSessionListUpdateView, MockingGetParkingCardDebt, MockingOrderAuthorized, \
    MockingOrderConfirm, MockingOrderRefund, GetParkingCardDebt, InitPayDebt, AccountInitPayment, GetCardSessionStatus, \
    SubscriptionCallbackView, RpsCreateOrGetAccount, SubscriptionUpdateView

urlpatterns = [
    url(r'^rps/session/create/$', RpsCreateParkingSessionView.as_view()),
    url(r'^rps/session/cancel/$', RpsCancelParkingSessionView.as_view()),
    url(r'^rps/session/update/$', RpsUpdateParkingSessionView.as_view()),
    url(r'^rps/session/complete/$', RpsCompleteParkingSessionView.as_view()),
    url(r'^rps/session/list/update/$', RpsParkingSessionListUpdateView.as_view()),

    url(r'^rps/cards/debt/$', GetParkingCardDebt.as_view()),
    url(r'^rps/cards/account/payment/init/$', AccountInitPayment.as_view()),
    url(r'^rps/cards/guest/payment/init/$', InitPayDebt.as_view()),
    url(r'^rps/cards/payment/status/$', GetCardSessionStatus.as_view()),

    url(r'^rps/subscription/callback/$', SubscriptionCallbackView.as_view()),
    url(r'^rps/subscription/update/$', SubscriptionUpdateView.as_view()),

    url(r'^rps/mock/debt/$', MockingGetParkingCardDebt.as_view()),
    url(r'^rps/mock/authorized/$', MockingOrderAuthorized.as_view()),
    url(r'^rps/mock/confirm/$', MockingOrderConfirm.as_view()),
    url(r'^rps/mock/refund/$', MockingOrderRefund.as_view()),

    url(r'^rps/account/register/$', RpsCreateOrGetAccount.as_view())
]

urlpatterns += staticfiles_urlpatterns()