from django.urls import path
from . import views

app_name = 'stock'

urlpatterns = [
    path('list/', views.stock_list, name='list'),
    path('detail/<int:pk>/', views.stock_detail, name='detail'),
    path('buy/<int:pk>/', views.stock_buy, name='buy'),
    path('sell/<int:pk>/', views.stock_sell, name='sell'),
    path('account/', views.account, name='account'),
]

