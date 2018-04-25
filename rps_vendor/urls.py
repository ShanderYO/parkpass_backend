from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from rps_vendor.views import RpsCreateParkingSessionView, RpsCancelParkingSessionView, RpsUpdateParkingSessionView, \
    RpsCompleteParkingSessionView, RpsParkingSessionListUpdateView

urlpatterns = [
    url(r'^rps/session/create/$', RpsCreateParkingSessionView.as_view()),
    url(r'^rps/session/cancel/$', RpsCancelParkingSessionView.as_view()),
    url(r'^rps/session/update/$', RpsUpdateParkingSessionView.as_view()),
    url(r'^rps/session/complete/$', RpsCompleteParkingSessionView.as_view()),
    url(r'^rps/session/list/update/$', RpsParkingSessionListUpdateView.as_view()),
]

urlpatterns += staticfiles_urlpatterns()