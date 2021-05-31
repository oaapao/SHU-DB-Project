from django.conf.urls.static import static
from django.urls import path

from LibMS import settings
from libapp import views
from django.conf.urls import url

urlpatterns = [
    path('', views.index, name="index"),
    path('index/', views.index, name="index"),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),

    path('goCheckIn/<slug:book>/', views.goCheckIn, name='goCheckIn'),
    path('goCheckOut/<int:id>', views.goCheckOut, name='goCheckOut'),
    path('goReserve/<slug:book>', views.goReserve, name='goReserve'),

    path('search/', views.search, name='search'),
    path('getKeyword/',views.getKeyword,name='getKeyword'),

    path('profile/', views.profile, name='profile'),
    path('collections/<slug:book>', views.collections, name='collections'),
    path('collectionList/', views.collectionList, name='collectionList'),
    path('collectionsOut/<slug:book>', views.collectionsOut, name='collectionsOut'),

    path('bookDetail/<slug:isbn>', views.bookDetail, name='bookDetail'),
    path('borrowList/', views.borrowList, name='borrowList'),
    path('reserveList/', views.reserveList, name='reserveList'),
    path('overdueList/', views.overdueList, name='overdueList'),
    path('dropReserve/<slug:book>', views.dropReserve, name='dropReserve'),
    path('bookCart/', views.bookCart, name='bookCart'),
    path('inCart/<slug:book_id>', views.inCart, name='inCart'),
    path('payMoney/<int:bid>', views.payMoney, name='payMoney'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
