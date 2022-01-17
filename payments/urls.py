from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from payments.views import TinkoffCallbackView, TestView, HomebankAcquiringPageView, HomeBankCallbackView, \
    HomebankAcquiringResultPageSuccessView, HomebankAcquiringResultPageErrorView, SetTestEmailsView

urlpatterns = [
    url(r'^callback/$', TinkoffCallbackView.as_view()),
    url(r'^homebank-callback/$', HomeBankCallbackView.as_view()),
    url(r'^test/$', TestView.as_view()),
    url(r'^ios-beta-testing/$', SetTestEmailsView.as_view()),
    url(r'^homebank/$', HomebankAcquiringPageView.as_view()),
    url(r'^result-success/$', HomebankAcquiringResultPageSuccessView.as_view()),
    url(r'^result-error/$', HomebankAcquiringResultPageErrorView.as_view()),
]

urlpatterns += staticfiles_urlpatterns()