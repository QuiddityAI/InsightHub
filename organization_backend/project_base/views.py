import logging
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def login_from_app(request):
    if request.method != 'POST':
        # not allowed
        return HttpResponse(status=405)
    email = request.POST.get('email')
    password = request.POST.get('password')
    user = authenticate(username=email, password=password)
    next_url = request.GET.get('next', '/')
    if "?" not in next_url:
        next_url += "?"
    try:
        login(request, user)
    except ValueError:
        logging.error("User not found")
        return redirect(next_url + '&error=Invalid username or password')
    return redirect(next_url)


@csrf_exempt
def signup_from_app(request):
    if request.method != 'POST':
        # not allowed
        return HttpResponse(status=405)
    email = request.POST.get('email')
    password = request.POST.get('password')
    next_url = request.GET.get('next', '/')
    if "?" not in next_url:
        next_url += "?"
    if User.objects.filter(username=email).exists():
        return redirect(next_url + '&error=Email already exists')
    user = User()
    user.username = email
    user.email = email
    user.set_password(password)
    user.save()
    user = authenticate(username=email, password=password)
    login(request, user)
    return redirect(next_url)