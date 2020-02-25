from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from partners.views import (
    GetPartnerParkingView, GetPartnerAvailableParkingsView,
    GetPartnerCardSessionStatus, InitPartnerPayDebt, GetPartnerParkingCardDebt
)

urlpatterns = [
    url(r'^get/(?P<pk>\d+)/$', GetPartnerParkingView.as_view()),
    url(r'^all/$', GetPartnerAvailableParkingsView.as_view()),

    url(r'^cards/debt/$', GetPartnerParkingCardDebt.as_view()),
    url(r'^cards/guest/payment/init/$', InitPartnerPayDebt.as_view()),
    url(r'^cards/payment/status/$', GetPartnerCardSessionStatus.as_view()),
]

urlpatterns += staticfiles_urlpatterns()
