from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from .views import *

urlpatterns = [

                  url(r'^login/$', LoginView.as_view()),
                  url(r'^login/phone/$', LoginWithPhoneView.as_view()),
                  url(r'^login/confirm/$', ConfirmLoginView.as_view()),
                  url(r'^logout/$', LogoutView.as_view()),

                  url(r'^objects/parking/view/(?P<page>\w+)/$', ShowParkingView.as_view()),
                  url(r'^objects/parking/create/$', EditParkingView.as_view()),
                  url(r'^objects/parking/(?P<id>\w+)/$', EditParkingView.as_view()),

                  url(r'^objects/parkingsession/view/(?P<page>\w+)/$', ShowParkingSessionView.as_view()),
                  url(r'^objects/parkingsession/create/$', EditParkingSessionView.as_view()),
                  url(r'^objects/parkingsession/(?P<id>\w+)/$', EditParkingSessionView.as_view()),

                  url(r'^objects/vendor/view/(?P<page>\w+)/$', ShowVendorView.as_view()),
                  url(r'^objects/vendor/create/$', EditVendorView.as_view()),
                  url(r'^objects/vendor/(?P<id>\w+)/$', EditVendorView.as_view()),

                  url(r'^objects/complain/view/(?P<page>\w+)/$', ShowComplainView.as_view()),
                  url(r'^objects/complain/create/$', EditComplainView.as_view()),
                  url(r'^objects/complain/(?P<id>\w+)/$', EditComplainView.as_view()),

                  url(r'^objects/issue/view/(?P<page>\w+)/$', ShowIssueView.as_view()),
                  url(r'^objects/issue/create/$', EditIssueView.as_view()),
                  url(r'^objects/issue/(?P<id>\w+)/$', EditIssueView.as_view()),

                  url(r'^objects/upgradeissue/view/(?P<page>\w+)/$', ShowUpgradeIssueView.as_view()),
                  url(r'^objects/upgradeissue/create/$', EditUpgradeIssueView.as_view()),
                  url(r'^objects/upgradeissue/(?P<id>\w+)/$', EditUpgradeIssueView.as_view()),

                  url(r'^statistics/parkings/$', AllParkingsStatisticsView.as_view()),
                  url(r'^statistics/log/$', GetLogView.as_view()),

              ] + staticfiles_urlpatterns()
