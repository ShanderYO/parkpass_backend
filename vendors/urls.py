from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from . import views as v

urlpatterns = [
                  url(r'^login/$', v.LoginView.as_view()),
                  url(r'^login/phone/$', v.LoginWithPhoneView.as_view()),
                  url(r'^login/email/$', v.LoginWithEmailView.as_view()),
                  url(r'^login/confirm/$', v.ConfirmLoginView.as_view()),
                  url(r'^login/changepw/$', v.PasswordChangeView.as_view()),
                  url(r'^logout/$', v.LogoutView.as_view()),
                  url(r'^login/restore', v.PasswordRestoreView.as_view()),
                  url(r'^email/add/$', v.ChangeEmailView.as_view()),
                  url(r'^email/confirm/(?P<code>\w+)/$', v.EmailConfirmationView.as_view()),
              ] + staticfiles_urlpatterns()
