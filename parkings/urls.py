from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from parkings.views import GetParkingView, GetParkingViewList, UpdateParkingView, CreateParkingSessionView, \
    UpdateParkingSessionView, CompleteParkingSessionView, TestSignedRequestView, ParkingSessionListUpdateView, \
    CancelParkingSessionView, ComplainSessionView

urlpatterns = [
    url(r'^get/(?P<pk>\d+)/$', GetParkingView.as_view()),
    url(r'^list/$', GetParkingViewList.as_view()),
    url(r'^complain/$', ComplainSessionView.as_view()),

    url(r'^v1/test/$', TestSignedRequestView.as_view()),
    url(r'^v1/update/$', UpdateParkingView.as_view()),
    url(r'^v1/session/create/$', CreateParkingSessionView.as_view()),
    url(r'^v1/session/cancel/$', CancelParkingSessionView.as_view()),
    url(r'^v1/session/update/$', UpdateParkingSessionView.as_view()),
    url(r'^v1/session/complete/$', CompleteParkingSessionView.as_view()),
    url(r'^v1/session/list/update/$', ParkingSessionListUpdateView.as_view()),
]

urlpatterns += staticfiles_urlpatterns()