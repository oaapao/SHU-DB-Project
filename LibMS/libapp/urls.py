from django.urls import path
from libapp import views
from django.conf.urls import url

urlpatterns = [
    path('', views.index, name="index"),
    path('index/', views.index, name="index"),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),

    path('checkIn/', views.checkIn, name='checkIn'),
    path('checkOut/', views.checkOut, name='checkOut'),
    path('reserve/', views.reserve, name='reserve'),

    path('goCheckIn/<slug:book>', views.goCheckIn, name='goCheckIn'),
    path('goCheckOut/<slug:book>/<int:num>', views.goCheckOut, name='goCheckOut'),
    path('goReserve/<slug:book>', views.goReserve, name='goReserve'),

    path('search/', views.search, name='search'),
    path('getKeyword/',views.getKeyword,name='getKeyword'),

    path('profile/', views.profile, name='profile'),
    path('collections/', views.collections, name='collections'),
    path('bookDetail/', views.bookDetail, name='bookDetail'),

    path('borrowList/', views.borrowList, name='borrowList'),
    path('reserveList/', views.reserveList, name='reserveList'),
    path('overdueList/', views.overdueList, name='overdueList'),

    path('dropReserve/<slug:book>', views.dropReserve, name='dropReserve'),


]
