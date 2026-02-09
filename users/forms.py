# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    """
    A form that creates a user, with no privileges, from the given email and password.
    """
    class Meta:
        model = User
        fields = ("email",)

# === ADD THIS NEW FORM ===
class UserProfileForm(forms.ModelForm):
    """
    Form for users to update their profile information.
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'bio', 'avatar', 'website', 'location']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap-like classes or simple styling
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})