from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from payments.views import TinkoffCallbackView, CancelPayment

urlpatterns = [
    url(r'^callback/$', TinkoffCallbackView.as_view()),
    url(r'^cancel/$',CancelPayment.as_view()),
]

urlpatterns += staticfiles_urlpatterns()