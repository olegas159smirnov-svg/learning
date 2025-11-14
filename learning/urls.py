from django.contrib.auth import views as auth_views
from django.contrib import admin
from django.urls import path, include
from django.conf import settings           # <- новый импорт настроек
from django.conf.urls.static import static # <- новый импорт обработчика статики

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='admin/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='stock:list'), name='logout'),
    path('admin/', admin.site.urls),
    path('stock/', include(('stock.urls', 'stock'), namespace='stock')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) # <- добавляем обработчик статики к списку урлов

