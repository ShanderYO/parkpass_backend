from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from parkings.views import GetParkingView, GetParkingViewList, UpdateParkingView, CreateParkingSessionView, \
    UpdateParkingSessionView, CompleteParkingSessionView, TestSignedRequestView, ParkingSessionListUpdateView, \
    CancelParkingSessionView, ComplainSessionView, WantParkingView

urlpatterns = [
    url(r'^get/(?P<pk>\d+)/$', GetParkingView.as_view()),
    url(r'^list/$', GetParkingViewList.as_view()),
    url(r'^complain/$', ComplainSessionView.as_view()),


    url(r'^test/$', TestSignedRequestView.as_view()),
    url(r'^update/$', UpdateParkingView.as_view()),
    url(r'^want_parking/(?P<parking>\d+)/$', WantParkingView.as_view()),
    url(r'^session/create/$', CreateParkingSessionView.as_view()),
    url(r'^session/cancel/$', CancelParkingSessionView.as_view()),
    url(r'^session/update/$', UpdateParkingSessionView.as_view()),
    url(r'^session/complete/$', CompleteParkingSessionView.as_view()),
    url(r'^session/list/update/$', ParkingSessionListUpdateView.as_view()),
]

urlpatterns += staticfiles_urlpatterns()
