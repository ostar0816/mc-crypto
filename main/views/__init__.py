import json
import itertools
import collections
from base64 import b32encode
from binascii import unhexlify
from decimal import Decimal as D

import pymongo
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.views.generic import TemplateView
from django.shortcuts import render, redirect, resolve_url
from django.http import HttpResponseRedirect
from django.views.decorators.cache import never_cache
from django.core.mail import EmailMultiAlternatives, send_mail
from django.urls import reverse
from django.conf import settings
from django.template import loader

from pankow.models import TradePlan
from main.models import User, Preferences, Log, Profile
from main.forms import ProfileForm, SignupForm
from two_factor.views.core import SetupView
from two_factor.views.utils import class_view_decorator
from romulus import MG


mongo = pymongo.MongoClient()
db = mongo.belvedere
EXCH = sorted(MG.exchanges)
REGIONS = collections.defaultdict(list)
for e, v in MG.exch_data.items():
    if v['region']:
        region = v['region']
        if region == 'Middle East' or region.endswith('Asia'):
            region = 'Asia'
        REGIONS[region].append(e)
REGIONS_JSON = json.dumps(REGIONS)


@login_required(login_url="login/")
def index(request):
    # cur_user = User.objects.get(pk=request.user.id)
    # if cur_user.objects.filter(preferences).exists():
    #     cur_preferences = cur_user.preferences.preferences
    if not db.simul.count():
        exch = []
        exch_groups = []
        curr_ = []
        total_vol = '0'
    else:
        exch = sorted(db.simul.distinct('exchanges_slug'))
        exch_groups = [list(v)
                       for _, v in itertools.groupby(exch, key=lambda i: i[0])]
        curr_ = sorted(db.simul.distinct('currencies'))
        total_vol = next(db.simul.aggregate([
            {'$project': {'markets': ['$spread_info.a', '$spread_info.b']}},
            {'$unwind': '$markets'},
            {'$group': {
                '_id': {
                    'exch': '$markets.exch',
                    'a': '$markets.a',
                    'b': '$markets.b',
                },
                'vol': {'$avg': '$markets.vol'},
            }},
            {'$group': {'_id': None, 'total': {'$sum': '$vol'}}},
        ]))['total']
        total_vol = total_vol.to_decimal().quantize(D('0'))
        total_in_usd = False
        btc_rate = list(db.rates.find(
            {'currency': 'Bitcoin', 'exch': 'bitmex'},
            {'price.usd': True},
        ))
        if btc_rate:
            btc_rate = btc_rate[0]['price']['usd'].to_decimal()
            total_vol = (total_vol * btc_rate).quantize(D('0'))
            total_in_usd = True

    return render(
        request, 'index.html',
        {
            'exchange_number': len(exch),
            'currencies_number': len(curr_),
            'total_vol': total_vol,
            'total_in_usd': total_in_usd,
            'exchanges': exch,
            'exchange_groups': exch_groups,
            'currencies': curr_,
            'regions': REGIONS_JSON,
        }
    )


def exch_list(request):
    exch = sorted(db.simul.distinct('exchanges_slug'))
    return render(request, 'exch_list.html', {'exch_list': exch})


def curr_list(request):
    curr_ = sorted(db.simul.distinct('currencies'))
    return render(request, 'curr_list.html', {'curr_list': curr_})


def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            email = form.cleaned_data.get('email')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(email=email, password=raw_password)
            login(request, user)
            send_mail("Welcome to Macchina",
                      "Congratulations! You have successfully registered on macchina.com",
                      "alpha@macchina.com", [email])
            return redirect('/')
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})


@login_required(login_url="login/")
def profile(request):
    if request.method == 'POST':
        profile_form = ProfileForm(request.POST, instance=request.user.profile)
        if profile_form.is_valid():
            profile_form.save()
    else:
        profile_form = ProfileForm()

    return render(
        request, 'profile.html',
        {
            'profile_form': profile_form
        }
    )


@login_required(login_url="login/")
def set_2fa_mode(request):
    user = User.objects.get(pk=request.user.id)
    value = False
    if request.method == 'POST':
        if request.POST.get('group1') == 'only_auth':
            value = True

    if hasattr(user, 'preferences'):
        user.preferences.is_only_auth = value
        user.save()
    else:
        pre = Preferences(is_only_auth=value, user_id=request.user.id)
        pre.save()

    return HttpResponseRedirect('/preferences')


@login_required(login_url="login/")
def realtime(request):
    return render(
        request, 'realtime.html',
    )


@login_required(login_url="login/")
def trades(request):
    trade_plan_list = TradePlan.objects.filter(user=request.user)
    return render(
        request, 'trades.html',
        {
            'trade_plan_list': trade_plan_list,
        }
    )


def save_preferences(request):
    user = User.objects.get(pk=request.user.id)
    if request.method == 'POST':
        selected_exch = request.POST.getlist('incl-exch[]')

    if hasattr(user, 'preferences'):
        user.preferences.preferences = selected_exch
        user.save()
    else:
        pre = Preferences(preferences=selected_exch, user_id=request.user.id)
        pre.save()

    return render(
        request, 'preferences.html',
        {
            'exchanges': EXCH,
        }
    )


@login_required(login_url="login/")
def two_factor_auth(request):
    return render(
        request, 'two_factor_auth.html',
    )


@login_required(login_url="login/")
def two_factor_verify(request):
    return render(
        request, 'two_factor_verify.html',
    )


@login_required(login_url="login/")
def two_factor_api_keys(request):
    return render(
        request, 'two_factor_api_keys.html',
        {
            'exchanges': EXCH,
        }
    )


@login_required(login_url="login/")
def two_factor_complete(request):
    return render(
        request, 'two_factor_complete.html',
    )


@login_required(login_url="login/")
def preferences_complete(request):
    return render(
        request, 'preferences_complete.html',
    )


@class_view_decorator(login_required)
class PreferencesView(SetupView):
    template_name = 'preferences.html'

    def get_context_data(self, form, **kwargs):
        context = super(PreferencesView, self).get_context_data(form, **kwargs)
        if self.steps.current == 'generator':
            key = self.get_key('generator')
            rawkey = unhexlify(key.encode('ascii'))
            b32key = b32encode(rawkey).decode('utf-8')
            self.request.session[self.session_key_name] = b32key
            context.update({
                'QR_URL': reverse(self.qrcode_url)
            })
        elif self.steps.current == 'validation':
            context['device'] = self.get_device()
        context['cancel_url'] = resolve_url(settings.LOGIN_REDIRECT_URL)
        context['is_only_auth'] = self.request.user.preferences.is_only_auth
        context['exchanges'] = EXCH
        log_list = Log.objects.filter(user=self.request.user)
        context['log_list'] = log_list
        return context


class UserLoginView(LoginView):
    template_name = 'login.html'

    def form_valid(self, form):
        token_generator = default_token_generator
        domain_override = None
        extra_email_context = None

        last_access = None
        log_list = Log.objects.filter(user=form.get_user())
        if log_list:
            last_access = log_list.latest('date')
        cur_ip = self.request.META.get('REMOTE_ADDR')

        is_email_verified = Profile.objects.get(user_id=form.get_user().id).is_email_verified

        # Do Login without ip address comparison in case user already did email confirmation.

        if is_email_verified or last_access is None:
            login(self.request, form.get_user())
            Profile.objects.filter(user_id=form.get_user().id).update(is_email_verified=False)
            return HttpResponseRedirect(self.get_success_url())

        if (cur_ip == last_access.ip_address or settings.DEBUG or
                not settings.SEND_LOGIN_CHECK_EMAIL):
            login(self.request, form.get_user())
            return HttpResponseRedirect(self.get_success_url())
        else:
            email = self.request.POST.get('username')
            for user in self.get_users(email):
                if not domain_override:
                    current_site = get_current_site(self.request)
                    site_name = current_site.name
                    domain = current_site.domain
                else:
                    site_name = domain = domain_override
                context = {
                    'email': email,
                    'domain': domain,
                    'site_name': site_name,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)).decode(),
                    'user': user,
                    'token': token_generator.make_token(user),
                    'protocol': 'https',
                }
                if extra_email_context is not None:
                    context.update(extra_email_context)
                self.send_mail(
                    'login_confirm_subject.txt', 'login_confirm_email.html', context,
                    'support@macchina.com', email
                )
            return HttpResponseRedirect('/ip_changed')

    def get_users(self, email):
        """
        Given an email, return matching user(s) who should receive a reset.
        """
        active_users = User._default_manager.filter(**{
            '%s__iexact' % User.get_email_field_name(): email,
            'is_active': True,
        })
        return (u for u in active_users if u.has_usable_password())

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Send a django.core.mail.EmailMultiAlternatives to `to_email`.
        """
        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)

        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name is not None:
            html_email = loader.render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, 'text/html')

        email_message.send()


def ip_changed(request):
    return render(
        request, 'ip_changed.html',
    )


@never_cache
def login_confirm(request, uidb64=None, token=None,
                  token_generator=default_token_generator,
                  post_reset_redirect=None,
                  extra_context=None):
    """
    Check the hash in a password reset link and present a form for login
    """

    assert uidb64 is not None and token is not None  # checked by URLconf
    try:
        # urlsafe_base64_decode() decodes to bytestring
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and token_generator.check_token(user, token):
        Profile.objects.filter(user_id=user.id).update(is_email_verified=True)

    return HttpResponseRedirect('/login')


class FAQView(TemplateView):

    template_name = 'faq.html'
