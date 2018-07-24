from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from .views import *

urlpatterns = [

                  url(r'^login/$', LoginView.as_view()),
                  url(r'^login/phone/$', LoginWithPhoneView.as_view()),
                  url(r'^login/email/$', LoginWithEmailView.as_view()),
                  url(r'^login/confirm/$', ConfirmLoginView.as_view()),
                  url(r'^login/changepw/$', PasswordChangeView.as_view()),
                  url(r'^logout/$', LogoutView.as_view()),
                  url(r'^login/restore', PasswordRestoreView.as_view()),
                  url(r'^email/add/$', ChangeEmailView.as_view()),
                  url(r'^email/confirm/(?P<code>\w+)/$', EmailConfirmationView.as_view()),

              ] + staticfiles_urlpatterns()
