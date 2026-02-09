# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import CustomUserCreationForm

def signup(request):
    """
    Handle user registration.
    """
    # If user is already authenticated, redirect them
    if request.user.is_authenticated:
        return redirect('course_list')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('course_list')  # Always redirect after successful POST
        # If form is invalid, fall through to render form with errors
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'users/signup.html', {'form': form})