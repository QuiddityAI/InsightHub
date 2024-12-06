import json
import logging
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from data_map_backend.models import Organization, DataCollection, CollectionColumn, User
from data_map_backend.notifier import default_notifier


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
        default_notifier.info(f"User {email} unsuccessfully tried to log in", user=None)
        return redirect(next_url + '&error=Invalid username or password')

    default_notifier.info(f"User {email} just logged in", user=user)
    return redirect(next_url)


@csrf_exempt
def signup_from_app(request):
    if request.method != 'POST':
        # not allowed
        return HttpResponse(status=405)
    email = request.POST.get('email')
    password = request.POST.get('password')
    if not email or not password:
        return HttpResponse(status=400)
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

    # initialize user:
    try:
        absclust_org = Organization.objects.get(name='AbsClust for Science')
        absclust_org.members.add(user)
    except Organization.DoesNotExist:
        logging.error("Organization AbsClust does not exist")
    else:
        # potentially set up initial collections etc.
        pass

    user = authenticate(username=email, password=password)
    login(request, user)

    default_notifier.info(f"User {email} just registered", user=user)
    return redirect(next_url)


@csrf_exempt
def change_password_from_app(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)
    try:
        old_password = data['old_password']
        new_password = data['new_password']
    except KeyError:
        return HttpResponse(status=400)
    logging.warning(f"Changing password for user {request.user.username}")
    user = authenticate(username=request.user.username, password=old_password)
    if user is None:
        return HttpResponse(status=401)
    user.set_password(new_password)
    user.save()
    default_notifier.info(f"User {request.user.username} just updated password", user=request.user)
    return HttpResponse(status=200)