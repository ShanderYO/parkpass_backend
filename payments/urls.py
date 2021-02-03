from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from payments.views import TinkoffCallbackView, TestView, HomebankAcquiringPageView

urlpatterns = [
    url(r'^callback/$', TinkoffCallbackView.as_view()),
    url(r'^test/$', TestView.as_view()),
    url(r'^homebank/$', HomebankAcquiringPageView.as_view()),
]

urlpatterns += staticfiles_urlpatterns()