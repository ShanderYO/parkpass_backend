from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from payments.views import TinkoffCallbackView

urlpatterns = [
    url(r'^callback/$', TinkoffCallbackView.as_view()),
]

urlpatterns += staticfiles_urlpatterns()