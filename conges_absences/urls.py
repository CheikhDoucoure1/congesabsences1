from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from conges import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.tableau_de_bord, name='tableau_de_bord'),
    path('connexion/', views.connexion, name='connexion'),
    path('deconnexion/', views.deconnexion, name='deconnexion'),
    path('nouvelle-demande/', views.nouvelle_demande, name='nouvelle_demande'),
    path('mes-demandes/', views.mes_demandes, name='mes_demandes'),
    path('mes-demandes/<int:demande_id>/annuler/', views.annuler_demande, name='annuler_demande'),
    path('mon-solde/', views.mon_solde, name='mon_solde'),
    path('calendrier/', views.calendrier, name='calendrier'),
    path('approbations/', views.approbations, name='approbations'),
    path('approbations/<int:demande_id>/', views.detail_demande, name='detail_demande'),
    path('approbations/<int:demande_id>/traiter/', views.traiter_demande, name='traiter_demande'),
    path('equipe/', views.equipe, name='equipe'),
    path('administration/', views.administration, name='administration'),
    path('administration/importer-employes/', views.importer_employes, name='importer_employes'),
    path('administration/template-employes/', views.telecharger_template_employes, name='template_employes'),
    path('notifications/', views.notifications, name='notifications'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('profil/', views.profil, name='profil'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
