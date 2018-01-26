from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from parkings.views import GetParkingView, GetParkingViewList

urlpatterns = [
    url(r'^get/(?P<pk>\d+)/$', GetParkingView.as_view()),
    url(r'^list/$', GetParkingViewList.as_view()),
]

urlpatterns += staticfiles_urlpatterns()