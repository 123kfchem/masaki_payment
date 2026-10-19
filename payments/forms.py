from decimal import Decimal

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class PaymentForm(forms.Form):
    phone_number = forms.CharField(
        max_length=15,
        label="Client phone number",
        help_text="Use a valid Safaricom number such as 254700000000 or +254700000000",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    amount = forms.DecimalField(
        min_value=Decimal("1.00"),
        max_digits=10,
        decimal_places=2,
        label="Amount",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )

    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"].strip().replace(" ", "")
        if phone_number.startswith("0"):
            phone_number = "+254" + phone_number[1:]
        elif phone_number.startswith("7"):
            phone_number = "+254" + phone_number
        elif phone_number.startswith("254"):
            phone_number = f"+{phone_number}"
        elif not phone_number.startswith("+"):
            phone_number = f"+{phone_number}"

        if not phone_number.startswith("+254"):
            raise forms.ValidationError("Please enter a valid Safaricom phone number.")
        return phone_number


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username", widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(strip=False, widget=forms.PasswordInput(attrs={'class': 'form-control'}))
