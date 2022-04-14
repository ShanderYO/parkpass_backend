from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from parkings.views import *

urlpatterns = [
    url(r'^get/(?P<pk>\d+)/$', GetParkingView.as_view()),
    url(r'^get/(?P<pk>\d+)/subscriptions/$', GetAvailableSubscriptionsView.as_view()),
    url(r'^get/(?P<pk>\d+)/tariff/$', GetTariffParkingView.as_view()),
    url(r'^list/$', GetParkingViewList.as_view()),
    url(r'^all/$', GetAvailableParkingsView.as_view()),
    url(r'^complain/$', ComplainSessionView.as_view()),
    url(r'^wish/(?P<parking>\d+)/$', WishView.as_view()),
    url(r'^wish/(?P<parking>\d+)/count/$', CountWishView.as_view()),

    url(r'^update/$', UpdateParkingView.as_view()),
    url(r'^session/create/$', CreateParkingSessionView.as_view()),
    url(r'^session/cancel/$', CancelParkingSessionView.as_view()),
    url(r'^session/update/$', UpdateParkingSessionView.as_view()),
    url(r'^session/complete/$', CompleteParkingSessionView.as_view()),
    url(r'^session/list/update/$', ParkingSessionListUpdateView.as_view()),

    url(r'^subscription/pay/$', SubscriptionsPayView.as_view()),
    url(r'^subscription/pay/(?P<pk>\d+)/status/$', SubscriptionsPayStatusView.as_view()),

    url(r'^send-valet-email/$', SendValetEmailView.as_view()),  # TODO удалить после прохождения этапа 0

    url(r'^close-session/$', CloseSessionRequest.as_view()),

    url(r'^export/xls/$', exportParkingDataToExcel),
]

urlpatterns += staticfiles_urlpatterns()
