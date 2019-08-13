from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from .views import *

urlpatterns = [
    url(r'^login/$', PhoneLoginView.as_view()),
    url(r'^login/confirm/$', ConfirmPhoneLoginView.as_view()),
    url(r'^login/email/$', LoginWithEmailView.as_view()),
    url(r'^logout/$', LogoutView.as_view()),
    url(r'^tokens/update/$', UpdateTokensView.as_view()),
    url(r'^tokens/replace/$', ReplaceTokensView.as_view()),
]

urlpatterns += staticfiles_urlpatterns()