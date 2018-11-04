from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from .views import *

urlpatterns = [

                  url(r'^login/$', LoginView.as_view()),
                  url(r'^login/phone/$', LoginWithPhoneView.as_view()),
                  url(r'^logout/$', LogoutView.as_view()),
                  url(r'^objects/(?P<name>\w+)/(?P<id>\d+)/(?P<action>\w+)/$', ObjectActionView.as_view()),

                  url(r'^statistics/parkings/$', AllParkingsStatisticsView.as_view()),
                  url(r'^statistics/log/(?P<name>.+)/$', GetLogView.as_view()),
                  url(r'^statistics/log/$', GetLogView.as_view()),

              ] + staticfiles_urlpatterns() + [
                  url(r'^objects/%s/$' % i, generic_object_view(i).as_view()) for i in admin_objects
              ] + [
                  url(r'^objects/%s/(?P<id>\d+)/$' % i, generic_object_view(i).as_view()) for i in admin_objects
              ]
