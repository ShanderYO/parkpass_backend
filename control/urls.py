from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from .views import *

urlpatterns = [

                  url(r'^login/$', LoginView.as_view()),
                  url(r'^login/phone/$', LoginWithPhoneView.as_view()),
                  url(r'^logout/$', LogoutView.as_view()),

                  url(r'^objects/(?P<name>\w+)/$', ObjectView.as_view()),
                  url(r'^objects/(?P<name>\w+)/(?P<id>\d+)/$', ObjectView.as_view()),
                  url(r'^objects/(?P<name>\w+)/(?P<id>\d+)/(?P<action>\w+)/$', ObjectActionView.as_view()),

                  url(r'^statistics/parkings/$', AllParkingsStatisticsView.as_view()),
                  url(r'^statistics/log/$', GetLogView.as_view()),

              ] + staticfiles_urlpatterns()
