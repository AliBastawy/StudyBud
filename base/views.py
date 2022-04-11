from multiprocessing import context
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
# from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout

# I replaced it with other Forms
# from django.contrib.auth.forms import UserCreationForm

from .models import Room, Topic, Message, User
from .forms import RoomForm, UserForm, MyUserCreationForm



def loginPage(request):

  # Prevet Users from entering login page from the url if they are authenticated like localhost:8000/login
  if request.user.is_authenticated:
    return redirect('home')

  if request.method == 'POST':
    email = request.POST.get('email').lower()
    password = request.POST.get('password')

    # Check if the email entered exist in the database or not
    try:
      user = User.objects.get(email=email)
    except:
      messages.error(request, 'Email does not exist')
    
    user = authenticate(request, email=email, password=password)

    if user is not None:
      login(request, user)
      return redirect('home')
    else:
      messages.error(request, 'Email or Password does not exist')

  # Used to differentiate between login page and register page as they both in the same html
  page = 'login'

  context = {'page': page}
  return render(request, 'base/login_register.html', context)


def logoutPage(request):
  logout(request)
  return redirect('home')


def registerPage(request):
  form = MyUserCreationForm()
  
  if request.method == 'POST':
    form = MyUserCreationForm(request.POST)
    if form.is_valid():
      user = form.save(commit=False)
      user.username = user.username.lower()
      user.save()
      login(request, user)
      return redirect('home')
    else :
      messages.error(request, 'An Error occurred during Registiration')
  
  context = {'form': form}
  return render(request, 'base/login_register.html', context)


def home(request):
  q = request.GET.get('q') if request.GET.get('q') != None else ''

  rooms = Room.objects.filter(
    Q(topic__name__icontains=q) |
    Q(name__icontains=q) |
    Q(description__icontains=q)
  )
  topics = Topic.objects.all()[0:5]
  room_count = rooms.count() #.count() is faster than .len()
  
  room_messages = Message.objects.filter(Q(room__topic__name__icontains=q))

  context = {'rooms': rooms, 'topics': topics, 'room_count': room_count, 'room_messages': room_messages}
  return render(request, 'base/home.html', context)


def room(request, pk):
  room = Room.objects.get(id=pk)
  room_messages = room.message_set.all() # Because message is a child of room so we do room.message_set not Message.all()
  
  participants = room.participants.all() # Here I made it without _set because it is Many To Many relationship


  if request.method == 'POST':
    # In others I was saying form = RoomForm(room) and somethings like that
    # but here I want to add to the Database some data that will not be added when the user post a message
    # like I want the user details, which room they are talking on, and the body of message
    message = Message.objects.create(
      user=request.user,
      room=room,
      body=request.POST.get('body')
    )
    room.participants.add(request.user)
    return redirect('room', pk)
  
  
  context = {'room': room, 'room_messages': room_messages, 'participants': participants}
  return render(request, 'base/room.html', context)


def userProfile(request, pk):
  user = User.objects.get(id=pk)
  rooms = user.room_set.all()
  room_messages = user.message_set.all()
  topics = Topic.objects.all()
  context = {'user': user, 'rooms': rooms, 'room_messages': room_messages, 'topics': topics}
  return render(request, 'base/profile.html', context)


@login_required(login_url="login")
def createRoom(request):
  form = RoomForm()
  topics = Topic.objects.all()

  if request.method == 'POST':
    topic_name = request.POST.get('topic')
    topic, created = Topic.objects.get_or_create(name=topic_name)
    
    Room.objects.create(
      host=request.user,
      topic=topic,
      name=request.POST.get('name'),
      description=request.POST.get('description'),
    )
    return redirect('home')

  context = {'form': form, 'topics': topics}
  return render(request, 'base/room_form.html', context)


@login_required(login_url="login")
def updateRoom(request, pk):
  
  room = Room.objects.get(id=pk)
  form = RoomForm(instance=room)
  topics = Topic.objects.all()

  # Restrict any user except the owner of the room to delete it
  if request.user != room.host:
    return HttpResponse('You are not allowed here')

  if request.method == 'POST':
    topic_name = request.POST.get('topic')
    topic, created = Topic.objects.get_or_create(name=topic_name)
    room.name = request.POST.get('name')
    room.topic = topic
    room.description = request.POST.get('description')
    room.save()
    return redirect('home')
  
  context = {'form': form, 'topics': topics, 'room': room}
  return render(request, 'base/room_form.html', context)


@login_required(login_url="login")
def deleteRoom(request, pk):
  room = Room.objects.get(id=pk)
  
  # Restrict any user except the owner of the room to delete it
  if request.user != room.host:
    return HttpResponse('You are not allowed here')
  
  
  if request.method == 'POST':
    room.delete()
    return redirect('home')
  
  return render(request, 'base/delete.html', {'obj': room})


@login_required(login_url="login")
def deleteMessage(request, pk):
  message = Message.objects.get(id=pk)
  
  # Restrict any user except the owner of the message to delete it
  if request.user != message.user:
    return HttpResponse('You are not allowed here')
  
  
  if request.method == 'POST':
    message.delete()
    return redirect('home')
  
  return render(request, 'base/delete.html', {'obj': message})


@login_required(login_url='login')
def updateUser(request):
  user = request.user
  form = UserForm(instance=user)
  if request.method == 'POST':
    form = UserForm(request.POST, request.FILES, instance=user)
    if form.is_valid():
      form.save()
      return redirect('user-profile', pk=user.id)


  return render(request, 'base/update-user.html', {'form': form})


def topicPage(request):
  q = request.GET.get('q') if request.GET.get('q') != None else ''
  topics = Topic.objects.filter(name__icontains=q)
  return render(request, 'base/topics.html', {'topics': topics})


def activityPage(request):
  q = request.GET.get('q') if request.GET.get('q') != None else ''
  room_messages = Message.objects.filter(Q(room__topic__name__icontains=q))
  return render(request, 'base/activity.html', {'room_messages': room_messages})