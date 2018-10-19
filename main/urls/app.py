from django.conf.urls import url
from django.contrib.auth import views as auth_view

from main import views
from main.views import UserLoginView, FAQView
from two_factor.views import LoginView


urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^profile/$', views.profile, name='profile'),
    url(r'^set-2fa-mode/$', views.set_2fa_mode, name='set_2fa_mode'),
    url(r'^preferences/$', view=views.PreferencesView.as_view(), name='preferences'),
    url(r'^preferences-complete/$', views.preferences_complete, name='preferences_complete'),
    # url(r'^trades/$', views.trades, name='trades'),
    # url(r'^login/$', UserLoginView.as_view(), name='login'),
    url(r'^login/$', LoginView.as_view(), name='login'),
    url(r'^logout/$', auth_view.logout, {'next_page': '/login'}, name='logout'),
    url(r'^signup/$', views.signup, name='signup'),
    url(r'^exchanges/$', views.exch_list, name='exchlist'),
    url(r'^currencies/$', views.curr_list, name='currlist'),
    url(r'^faq/$', FAQView.as_view(), name='faq'),
    url(r'^password_reset/$', auth_view.password_reset, {
            'template_name': 'password_reset_form.html',
            'email_template_name': 'password_reset_email.html',
            'subject_template_name': 'password_reset_subject.txt'
        },
        name='password_reset'),
    url(r'^password_reset/done/$', auth_view.password_reset_done, {'template_name': 'password_reset_done.html'},
        name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_view.password_reset_confirm, {'template_name': 'password_reset_confirm.html'}, name='password_reset_confirm'),
    url(r'^reset/done/$', auth_view.password_reset_complete,  {'template_name': 'password_reset_complete.html'},
        name='password_reset_complete'),
    url(r'^ip_changed/$', views.ip_changed, name='ip_changed'),
    url(r'^confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.login_confirm, name='login_confirm'),
    url(r'^save_preferences/$', views.save_preferences, name='save_preferences'),
]
