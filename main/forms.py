from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import password_validation
from django.utils.translation import ugettext_lazy as _
from django import forms

from .models import Profile, User


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username", max_length=30,
                               widget=forms.TextInput(attrs={'class': 'form-control', 'name': 'username'}))
    password = forms.CharField(label="Password", max_length=30,
                               widget=forms.TextInput(attrs={'class': 'form-control', 'name': 'password'}))


class UserRegistrationForm(forms.Form):
    username = forms.CharField(
        required=True,
        max_length=32,
        widget=forms.TextInput(attrs={'placeholder': 'Username'})
    )
    email = forms.EmailField(
        required=True
    )
    password = forms.CharField(
        required=True,
        max_length=32,
        widget=forms.PasswordInput,
    )


class ProfileForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = ('full_name', 'birth_date', 'birth_place', 'address', 'phone_number', 'id_doc_number')
        widgets = {
            'full_name': forms.TextInput(
                attrs={
                    'placeholder': _('full name'),
                    'class': 'form-input',
                    'type': 'text'
                }
            ),

            'birth_date': forms.DateInput(
                attrs={
                    'placeholder': _('birth date: 1990-01-01'),
                    'class': 'form-input',
                    'type': 'date'
                }
            ),

            'birth_place': forms.TextInput(
                attrs={
                    'placeholder': _('place of birth'),
                    'class': 'form-input'
                }
            ),

            'address': forms.TextInput(
                attrs={
                    'placeholder': _('residency address'),
                    'class': 'form-input'
                }
            ),

            'phone_number': forms.TextInput(
                attrs={
                    'placeholder': _('phone number'),
                    'class': 'form-input',
                    'type': 'tel'
                }
            ),

            'id_doc_number': forms.TextInput(
                attrs={
                    'placeholder': _('identification document number'),
                    'class': 'form-input',
                    'type': 'number'
                }
            ),
        }


class SignupForm(forms.ModelForm):
    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
    }
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput,
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput,
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    class Meta:
        model = User
        fields = ("email",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._meta.model.USERNAME_FIELD in self.fields:
            self.fields[self._meta.model.USERNAME_FIELD].widget.attrs.update({'autofocus': True})

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2

    def _post_clean(self):
        super()._post_clean()
        # Validate the password after self.instance is updated with form data
        # by super().
        password = self.cleaned_data.get('password2')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error('password2', error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
