# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class CustomUserCreationForm(UserCreationForm):
    """
    A form that creates a user, with no privileges, from the given email and password.
    """
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Last Name'})
    )
    
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "password1", "password2")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
            if field_name != 'password1' and field_name != 'password2':
                # Don't override placeholders for password fields
                if not field.widget.attrs.get('placeholder'):
                    field.widget.attrs['placeholder'] = field.label or field_name.replace('_', ' ').title()


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
            # Add placeholders based on field names
            if not field.widget.attrs.get('placeholder'):
                field.widget.attrs['placeholder'] = field.label or field_name.replace('_', ' ').title()