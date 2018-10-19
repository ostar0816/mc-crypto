import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.signals import user_logged_in
from django.contrib.gis.geoip2 import GeoIP2
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.conf import settings
from fernet_fields import EncryptedTextField


# Create your models here.

class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """User model."""

    username = None
    email = models.EmailField(_('email address'), unique=True)
    user_code = models.CharField(max_length=100, unique=True, default=uuid.uuid4)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def get_email(self):
        return self.email


class Profile(models.Model):
    """Profile model."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=30, default='', blank=True)
    birth_date = models.DateField(null=True, blank=True)
    birth_place = models.CharField(max_length=30, blank=True, default='')
    address = models.CharField(max_length=30, blank=True, default='')
    phone_number = models.CharField(max_length=30, blank=True, default='')
    id_doc_number = models.CharField(max_length=30, blank=True, default='')
    is_email_verified = models.BooleanField(default=False, blank=True)

    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            Profile.objects.create(user=instance)


class Preferences(models.Model):
    """Preferences model."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    currency = models.CharField(max_length=30, default='', blank=True)
    timezone = models.CharField(max_length=30, default='', blank=True)
    is_notifications = models.BooleanField(default=False)
    is_2fa = models.BooleanField(default=False)
    is_only_auth = models.BooleanField(default=False)

    @receiver(post_save, sender=User)
    def create_user_preferences(sender, instance, created, **kwargs):
        if created:
            Preferences.objects.create(user=instance)

    @receiver(post_save, sender=User)
    def save_user_preferences(sender, instance, **kwargs):
        try:
            instance.preferences.save()
        except ObjectDoesNotExist:
            print('This user has no preferences.')


class Exchanges(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cur_exchange = models.CharField(max_length=30, default='', blank=True)


class Apikey(models.Model):
    exchanges = models.OneToOneField(Exchanges, on_delete=models.CASCADE, related_name='exchanges')
    api_key1 = EncryptedTextField()
    api_key2 = EncryptedTextField()

    @receiver(post_save, sender=Exchanges)
    def create_user_exchanges(sender, instance, created, **kwargs):
        if created:
            Apikey.objects.create(user=instance)

    @receiver(post_save, sender=Exchanges)
    def save_user_exchanges(sender, instance, **kwargs):
        try:
            instance.apikey.save()
        except ObjectDoesNotExist:
            print('This exchange has no api keys.')


class Log(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True, blank=True)
    ip_address = models.CharField(max_length=255, default='', blank=True)
    country = models.CharField(max_length=255, default='', blank=True)
    browser = models.CharField(max_length=255, default='', blank=True)


def save_user_info(sender, user, request, **kwargs):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    g = GeoIP2()

    if settings.DEBUG:
        ip_address = '174.127.103.100'  # for dev mode

    country = g.country_name(ip_address)
    browser = request.META['HTTP_USER_AGENT']
    date = timezone.now()

    log = Log(user=user, date=date, ip_address=ip_address, country=country, browser=browser)
    log.save()


user_logged_in.connect(save_user_info)
