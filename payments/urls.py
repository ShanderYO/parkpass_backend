from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from payments.views import (
    TinkoffCallbackView,
    TestView,
    HomebankAcquiringPageView,
    HomeBankCallbackView,
    HomebankAcquiringResultPageSuccessView,
    HomebankAcquiringResultPageErrorView,
    SetTestEmailsView,
    UzumCallbackView,
    UzumCallbackReceiptsView,
    UzumReceiptsView,
)

from rps_vendor.views import InitPayment

urlpatterns = [
    url(r"^callback/$", TinkoffCallbackView.as_view()),
    url(r"^homebank-callback/$", HomeBankCallbackView.as_view()),
    url(r"^test/$", TestView.as_view()),
    url(r"^ios-beta-testing/$", SetTestEmailsView.as_view()),
    url(r"^homebank/$", HomebankAcquiringPageView.as_view()),
    url(r"^result-success/$", HomebankAcquiringResultPageSuccessView.as_view()),
    url(r"^result-error/$", HomebankAcquiringResultPageErrorView.as_view()),
    url(r"^init/$", InitPayment.as_view(), name="init_payment"),
    url(r"^uzum-callback/$", UzumCallbackView.as_view()),
    # url(r"^uzum-callback-receipts/$", UzumCallbackReceiptsView.as_view()),
    url(r"^uzum-receipts/$", UzumReceiptsView.as_view()),
]

urlpatterns += staticfiles_urlpatterns()
