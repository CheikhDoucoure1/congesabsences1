from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Employe, Departement, TypeConge, SoldeConge, DemandeConge, Notification


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
    list_display = ['employe', 'type_conge', 'annee', 'jours_acquis', 'jours_pris', 'jours_reportes']
    list_filter = ['type_conge', 'annee']
    search_fields = ['employe__first_name', 'employe__last_name']


@admin.register(DemandeConge)
class DemandeCongeAdmin(admin.ModelAdmin):
    list_display = ['reference', 'employe', 'type_conge', 'date_debut', 'date_fin', 'nombre_jours', 'statut']
    list_filter = ['statut', 'type_conge', 'date_soumission']
    search_fields = ['reference', 'employe__first_name', 'employe__last_name']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['destinataire', 'titre', 'lue', 'date_creation']
    list_filter = ['lue']
