# courses/forms.py
from django import forms
from .models import Comment, Review

class CommentForm(forms.ModelForm):
    """
    Form for creating and editing comments.
    """
    parent_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Write your comment or question here...',
                'class': 'form-control'
            }),
        }
        labels = {
            'content': ''
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].help_text = 'Markdown is supported'

    def clean_content(self):
        content = self.cleaned_data['content']
        if len(content.strip()) < 3:
            raise forms.ValidationError("Comment must be at least 3 characters long.")
        return content


class ReviewForm(forms.ModelForm):
    """
    Form for creating and editing course reviews.
    """
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(attrs={'class': 'rating-radio'}),
            'comment': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Share your experience with this course (optional)...',
                'class': 'form-control'
            }),
        }
        labels = {
            'rating': 'Your Rating',
            'comment': 'Your Review (Optional)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating'].error_messages = {
            'required': 'Please select a rating',
            'invalid_choice': 'Please select a valid rating (1-5)'
        }
