from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from valet.views import ValetSessionView, get_valet_session_status

urlpatterns = [
    url(r'^session/get/$', ValetSessionView.as_view()),
    url(r'^session/book/$', ValetSessionView.as_view()),
    url(r'^session/status/$', get_valet_session_status),
]

urlpatterns += staticfiles_urlpatterns()