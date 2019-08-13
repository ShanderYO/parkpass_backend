from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from parkpass import settings

urlpatterns = [
    url(r'^admin_tools/', include('admin_tools.urls')),
    url(r'^api/admin/', include(admin.site.urls)),
                  url(r'^api/v1/', include('base.urls')),
    url(r'^api/v1/account/', include("accounts.urls")),
    url(r'^api/v1/parking/', include("parkings.urls")),
    url(r'^api/v1/payments/', include("payments.urls")),
                  url(r'^api/v1/control/', include("control.urls")),
                  url(r'^api/v1/owner/', include("owners.urls")),
    url(r'^api/v1/parking/', include("rps_vendor.urls")),
    url(r'^api/v1/vendor/', include("vendors.urls")),
    url(r'^api/v1/auth/', include("jwtauth.urls")),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
              + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += staticfiles_urlpatterns()
