from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from .views import *

urlpatterns = [

                  url(r'^login/$', LoginView.as_view()),
                  url(r'^login/phone/$', LoginWithPhoneView.as_view()),
                  url(r'^login/email/$', LoginWithEmailView.as_view()),
                  url(r'^login/confirm/$', ConfirmLoginView.as_view()),
                  url(r'^login/changepw/$', PasswordChangeView.as_view()),
                  url(r'^logout/$', LogoutView.as_view()),
                  url(r'^login/restore', PasswordRestoreView.as_view()),
                  url(r'^email/add/$', ChangeEmailView.as_view()),
                  url(r'^email/confirm/(?P<code>\w+)/$', EmailConfirmationView.as_view()),
                  url(r'^info/$', InfoView.as_view()),
                  # Statistics
                  url(r'^stats/parking/$', ParkingStatisticsView.as_view()),
                  url(r'^stats/summary/$', AllParkingsStatisticsView.as_view()),
                  url(r'^issue/$', IssueView.as_view())

              ] + staticfiles_urlpatterns()
