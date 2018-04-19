from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from accounts.views import LoginView, LogoutView, AccountView, ConfirmLoginView, AddCardView, DeleteCardView, SetDefaultCardView, \
    DebtParkingSessionView, StartParkingSession, CompleteParkingSession, ForceStopParkingSession, ForcePayView, \
    ResumeParkingSession, AccountParkingListView

urlpatterns = [
    url(r'^login/$', LoginView.as_view()),
    url(r'^login/confirm/$', ConfirmLoginView.as_view()),
    url(r'^logout/$', LogoutView.as_view()),
    url(r'^me/$', AccountView.as_view()),

    url(r'^card/add/$', AddCardView.as_view()),
    url(r'^card/delete/$', DeleteCardView.as_view()),
    url(r'^card/default/$', SetDefaultCardView.as_view()),

    url(r'^session/create/$', StartParkingSession.as_view()),
    url(r'^session/complete/$', CompleteParkingSession.as_view()),
    url(r'^session/stop/$', ForceStopParkingSession.as_view()),
    url(r'^session/resume/$', ResumeParkingSession.as_view()),

    url(r'^session/list/$', AccountParkingListView.as_view()),
    url(r'^session/debt/$', DebtParkingSessionView.as_view()),
    url(r'^session/pay/$', ForcePayView.as_view()),

]

urlpatterns += staticfiles_urlpatterns()