# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from .models import User
import os


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
    
    # Add website validation
    website = forms.URLField(
        required=False,
        validators=[URLValidator()],
        widget=forms.URLInput(attrs={'placeholder': 'https://example.com'})
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'bio', 'avatar', 'website', 'location']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
            # Add placeholders based on field names
            if not field.widget.attrs.get('placeholder'):
                field.widget.attrs['placeholder'] = field.label or field_name.replace('_', ' ').title()
    
    def clean_avatar(self):
        """Validate avatar file uploads"""
        avatar = self.cleaned_data.get('avatar')
        
        if not avatar:
            return avatar
        
        # Check file size (max 2MB)
        if avatar.size > 2 * 1024 * 1024:
            raise ValidationError('Image file too large (max 2MB)')
        
        # Check file extension
        ext = os.path.splitext(avatar.name)[1].lower()
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        if ext not in valid_extensions:
            raise ValidationError(f'Unsupported file extension. Allowed: {", ".join(valid_extensions)}')
        
        # Check content type (basic check)
        valid_mime_types = ['image/jpeg', 'image/png', 'image/gif']
        if hasattr(avatar, 'content_type') and avatar.content_type not in valid_mime_types:
            raise ValidationError('Please upload a valid image file (JPEG, PNG, or GIF)')
        
        return avatar
    
    def clean_website(self):
        """Additional website validation"""
        website = self.cleaned_data.get('website')
        
        if website:
            # Ensure URL has protocol
            if not website.startswith(('http://', 'https://')):
                website = 'https://' + website
                
            # Validate using Django's URLValidator
            validator = URLValidator()
            try:
                validator(website)
            except ValidationError:
                raise ValidationError('Please enter a valid URL')
        
        return website