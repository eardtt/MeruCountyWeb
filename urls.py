"""
URL configuration for meru_ff_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

# Function to redirect the root URL to the standings page
def home_redirect(request):
    # This redirect is now safe because we are correctly using the league: namespace
    return redirect('league:standings')

urlpatterns = [
    # Admin Panel URL
    path('admin/', admin.site.urls),
    
    # NEW: Redirects the base URL (/) to the 'standings' page
    # This pattern is named 'home', which is what was failing in your base.html
    path('', home_redirect, name='home'), 
    
    # Links the '/league/' path to your app's urls.py
    # CRITICAL FIX: We are including the namespace argument here.
    path('league/', include(('league.urls', 'league'), namespace='league')),
]