from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Employe, Departement, TypeConge, SoldeConge, DemandeConge, Notification, Recrutement, Depart, CongeSupplementaire, HistoriqueModification


@admin.register(Employe)
class EmployeAdmin(UserAdmin):
    list_display = ['username', 'first_name', 'last_name', 'email', 'role', 'departement', 'actif']
    list_filter = ['role', 'departement', 'actif']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    fieldsets = UserAdmin.fieldsets + (
        ('Informations professionnelles', {
            'fields': ('matricule', 'poste', 'departement', 'manager', 'role', 'telephone', 'date_embauche', 'actif')
        }),
    )


@admin.register(Departement)
class DepartementAdmin(admin.ModelAdmin):
    list_display = ['nom', 'code']


@admin.register(TypeConge)
class TypeCongeAdmin(admin.ModelAdmin):
    list_display = ['libelle', 'code', 'jours_max', 'necessite_justificatif', 'actif']
    list_filter = ['actif']


@admin.register(SoldeConge)
class SoldeCongeAdmin(admin.ModelAdmin):
    list_display = ['employe', 'type_conge', 'annee', 'jours_acquis', 'jours_pris', 'jours_reportes', 'jours_supplementaires']
    list_filter = ['type_conge', 'annee']
    search_fields = ['employe__first_name', 'employe__last_name']


@admin.register(CongeSupplementaire)
class CongeSupplementaireAdmin(admin.ModelAdmin):
    list_display = ['employe', 'type_conge', 'annee', 'nombre_jours', 'accorde_par', 'date_creation']
    list_filter = ['type_conge', 'annee']
    search_fields = ['employe__first_name', 'employe__last_name', 'motif']


@admin.register(DemandeConge)
class DemandeCongeAdmin(admin.ModelAdmin):
    list_display = ['reference', 'employe', 'type_conge', 'date_debut', 'date_fin', 'nombre_jours', 'statut']
    list_filter = ['statut', 'type_conge', 'date_soumission']
    search_fields = ['reference', 'employe__first_name', 'employe__last_name']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['destinataire', 'titre', 'lue', 'date_creation']
    list_filter = ['lue']


@admin.register(Recrutement)
class RecrutementAdmin(admin.ModelAdmin):
    list_display = ['employe', 'type_contrat', 'statut', 'date_embauche', 'responsable_rh']
    list_filter = ['statut', 'type_contrat', 'source']
    search_fields = ['employe__first_name', 'employe__last_name']


@admin.register(Depart)
class DepartAdmin(admin.ModelAdmin):
    list_display = ['employe', 'type_depart', 'statut', 'date_annonce', 'date_depart', 'traite_par']
    list_filter = ['statut', 'type_depart']
    search_fields = ['employe__first_name', 'employe__last_name']


@admin.register(HistoriqueModification)
class HistoriqueModificationAdmin(admin.ModelAdmin):
    list_display = ['date_action', 'type_action', 'employe_concerne', 'auteur', 'description']
    list_filter = ['type_action']
    search_fields = ['employe_concerne__first_name', 'employe_concerne__last_name', 'description']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
