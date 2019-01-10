from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from .views import *

urlpatterns = [
                  url(r'^login/$', LoginView.as_view()),
                  url(r'^login/phone/$', LoginWithPhoneView.as_view()),
                  url(r'^login/email/$', LoginWithEmailView.as_view()),
                  url(r'^password/change/$', PasswordChangeView.as_view()),
                  url(r'^logout/$', LogoutView.as_view()),
                  url(r'^password/restore/$', PasswordRestoreView.as_view()),
                  url(r'^email/add/$', ChangeEmailView.as_view()),
                  url(r'^email/confirm/(?P<code>\w+)/$', EmailConfirmationView.as_view()),
                  url(r'^applications/$', ApplicationsView.as_view()),
                  url(r'^applications/(?P<id>\d+)/$', ApplicationsView.as_view()),

                  url(r'^stats/top/$', ParkingsTopView.as_view()),
                  url(r'^stats/parkings/$', ParkingStatisticsView.as_view()),
                  url(r'^stats/sessions/$', ParkingSessionsView.as_view()),

                  url(r'^profile/$', AccountInfoView.as_view()),
                  url(r'^parkings/$', ParkingsView.as_view()),
                  url(r'^parkings/(?P<id>\d+)/$', ParkingsView.as_view()),
                  url(r'^parkings/(?P<id>\d+)/tariff/$', TariffView.as_view()),

                  url(r'^sessions/$', ParkingSessionsView.as_view()),
                  url(r'^sessions/(?P<id>\d+)/$', ParkingSessionsView.as_view()),

                  url(r'^connect/$', ConnectParkingView.as_view()),
                  url(r'^vendors/$', VendorsView.as_view()),
                  url(r'^vendors/(?P<id>\d+)/$', VendorsView.as_view()),
                  url(r'^company/$', CompanyView.as_view()),
                  url(r'^company/(?P<id>\d+)/$', CompanyView.as_view()),
                  url(r'^events/$', EventsView.as_view()),
              ] + staticfiles_urlpatterns()
