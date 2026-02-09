# courses/forms.py
from django import forms
from .models import Comment

class CommentForm(forms.ModelForm):
    """
    Form for submitting comments on lessons.
    """
    class Meta:
        model = Comment
        fields = ['content', 'parent']  # parent is hidden, set in view
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].widget.attrs.update({
            'placeholder': 'Add a comment or question...',
            'rows': 3,
        })
        # Parent field will be hidden in template
        self.fields['parent'].widget = forms.HiddenInput()
        self.fields['parent'].required = False