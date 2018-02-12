from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from parkings.views import GetParkingView, GetParkingViewList, UpdateParkingView, CreateParkingSessionView, \
    UpdateParkingSessionView, CompleteParkingSessionView

urlpatterns = [
    url(r'^get/(?P<pk>\d+)/$', GetParkingView.as_view()),
    url(r'^list/$', GetParkingViewList.as_view()),

    url(r'^update/$', UpdateParkingView.as_view()),
    url(r'^session/create/$', CreateParkingSessionView.as_view()),
    url(r'^session/update/$', UpdateParkingSessionView.as_view()),
    url(r'^session/complete/$', CompleteParkingSessionView.as_view()),
]

urlpatterns += staticfiles_urlpatterns()