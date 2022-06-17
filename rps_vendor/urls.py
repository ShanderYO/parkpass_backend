from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from rps_vendor.views import RpsCreateParkingSessionView, RpsCancelParkingSessionView, RpsUpdateParkingSessionView, \
    RpsCompleteParkingSessionView, RpsParkingSessionListUpdateView, MockingGetParkingCardDebt, MockingOrderAuthorized, \
    MockingOrderConfirm, MockingOrderRefund, GetParkingCardDebt, InitPayDebt, AccountInitPayment, GetCardSessionStatus, \
    SubscriptionCallbackView, RpsCreateOrGetAccount, SubscriptionUpdateView, GetDeveloperParkingCardDebt, \
    ConfirmPayDeveloperDebt, CheckTimestamp, ResetDeveloperToken, send_push_notifications, check_remote_network, \
    get_users_for_push_notifications

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

    url(r'^rps/account/register/$', RpsCreateOrGetAccount.as_view()),

    url(r'^developer/cards/debt/$', GetDeveloperParkingCardDebt.as_view()),
    url(r'^developer/cards/confirm/$', ConfirmPayDeveloperDebt.as_view()),

    url(r'^developer/checktimestamp/$', CheckTimestamp.as_view()),
    url(r'^developer/reset-token/$', ResetDeveloperToken.as_view()),

    # remote vendors
    url(r'^remote/session/create/$', RpsCreateParkingSessionView.as_view()),
    url(r'^remote/session/cancel/$', RpsCancelParkingSessionView.as_view()),
    url(r'^remote/session/update/$', RpsUpdateParkingSessionView.as_view()),
    url(r'^remote/session/complete/$', RpsCompleteParkingSessionView.as_view()),
    url(r'^remote/session/list/update/$', RpsParkingSessionListUpdateView.as_view()),

    url(r'^remote/cards/debt/$', GetParkingCardDebt.as_view()),
    url(r'^remote/cards/account/payment/init/$', AccountInitPayment.as_view()),
    url(r'^remote/cards/guest/payment/init/$', InitPayDebt.as_view()),
    url(r'^remote/cards/payment/status/$', GetCardSessionStatus.as_view()),

    url(r'^remote/subscription/callback/$', SubscriptionCallbackView.as_view()),
    url(r'^remote/subscription/update/$', SubscriptionUpdateView.as_view()),

    # service methods
    url(r'^check-remote-network/$', check_remote_network),
    url(r'^push-notifications/$', send_push_notifications),
    url(r'^get-users-for-push-notifications/$', get_users_for_push_notifications),
]

urlpatterns += staticfiles_urlpatterns()