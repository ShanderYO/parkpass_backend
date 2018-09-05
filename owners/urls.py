from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from .views import *

urlpatterns = [
                  url(r'^login/$', LoginView.as_view()),
                  url(r'^login/phone/$', LoginWithPhoneView.as_view()),
                  url(r'^login/email/$', LoginWithEmailView.as_view()),
                  url(r'^login/confirm/$', ConfirmLoginView.as_view()),
                  url(r'^password/change/$', PasswordChangeView.as_view()),
                  url(r'^logout/$', LogoutView.as_view()),
                  url(r'^password/restore/$', PasswordRestoreView.as_view()),
                  url(r'^email/add/$', ChangeEmailView.as_view()),
                  url(r'^email/confirm/(?P<code>\w+)/$', EmailConfirmationView.as_view()),
                  url(r'^connectissue/$', ConnectIssueView.as_view()),
                  url(r'^upgadeissues/send/$', IssueUpgradeView.as_view()),
                  url(r'^upgradeissues/show/(?P<page>\w+)/$', ListUpgradeIssuesView.as_view()),
                  url(r'^stats/parking/$', ParkingStatisticsView.as_view()),
                  url(r'^stats/info/$', AccountInfoView.as_view()),
                  url(r'^issue/$', IssueView.as_view()),
                  url(r'^parkings/(?P<page>\w+)/$', ListParkingsView.as_view()),
                  url(r'^company/view/(?P<page>\w+)/$', ListCompanyView.as_view()),
                  url(r'^company/create/$', EditCompanyView.as_view()),
                  url(r'^company/(?P<id>\w+)/$', EditCompanyView.as_view()),
              ] + staticfiles_urlpatterns()
