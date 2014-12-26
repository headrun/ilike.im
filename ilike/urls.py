from django.conf.urls import patterns, include, url
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^$', 'ilike.views.index', name='index'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'', include('social_auth.urls')),
    url(r'^home/', 'ilike.views.home', name='home'),
    url(r'^login-error/', 'ilike.views.login_error', name='error'),
    url(r'^crushes/', 'ilike.views.crushes', name='crushes'),
    url(r'^click/', 'ilike.views.change_state', name='click'),
    url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    url(r'^fb-pic/([^/]*)/$', 'ilike.views.display_pic', name='display_picture'),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}, name='logout'),
    url(r'^terms/', 'ilike.views.terms', name='terms'),
    url(r'^privacy/', 'ilike.views.privacy', name='privacy'),
    url(r'^press/', 'ilike.views.press', name='press'),
    url(r'^how/', 'ilike.views.how', name='how'),
)
