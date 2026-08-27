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
    path('approbations/<int:demande_id>/modifier/', views.modifier_demande, name='modifier_demande'),
    path('equipe/', views.equipe, name='equipe'),
    path('historique/', views.historique_modifications, name='historique_modifications'),
    path('administration/', views.administration, name='administration'),
    path('administration/importer-employes/', views.importer_employes, name='importer_employes'),
    path('administration/template-employes/', views.telecharger_template_employes, name='template_employes'),
    path('recrutements/', views.recrutements, name='recrutements'),
    path('recrutements/<int:recrutement_id>/statut/', views.maj_recrutement, name='maj_recrutement'),
    path('departs/', views.departs, name='departs'),
    path('departs/<int:depart_id>/statut/', views.maj_depart, name='maj_depart'),
    path('notifications/', views.notifications, name='notifications'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('profil/', views.profil, name='profil'),
    path('mes-demandes/<int:demande_id>/justificatif/', views.voir_justificatif, name='voir_justificatif'),
] + static(
    # Only the public 'avatars/' subfolder is served this way (profile
    # pictures — low sensitivity, needed by every page's header/sidebar).
    # Leave justificatifs (medical certificates, etc.) OUT of this: they are
    # served exclusively through the authenticated views.voir_justificatif,
    # which checks the requester actually has the right to see that file.
    # Note this static() helper is itself a no-op unless settings.DEBUG is
    # True — a real deployment needs its own web server / storage backend
    # with equivalent access control for the media root.
    settings.MEDIA_URL + 'avatars/',
    document_root=str(settings.MEDIA_ROOT / 'avatars'),
)
