# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, UserProfileForm  # <-- Import the new form

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
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'users/signup.html', {'form': form})

# === ADD THIS NEW VIEW ===
@login_required
def profile_edit(request):
    """
    Allow users to edit their profile information.
    """
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            # Add a success message
            from django.contrib import messages
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile_edit')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'users/profile_edit.html', {'form': form})