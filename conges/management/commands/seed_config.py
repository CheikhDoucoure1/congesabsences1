"""Seed the configuration data every real deployment needs (departments,
leave/absence types) — WITHOUT any demo user account, unlike init_data
(which is for local development/testing only, see its own docstring).

Safe to re-run: uses get_or_create, so it only fills in what's missing.

Usage: python manage.py seed_config
"""
from django.core.management.base import BaseCommand
from conges.models import Departement, TypeConge


class Command(BaseCommand):
    help = "Crée les départements et types de congé/absence de base (aucun compte utilisateur)"

    def handle(self, *args, **options):
        self.stdout.write('Création des départements...')
        depts_crees = 0
        for nom, code in [
            ('Direction Générale', 'DG'),
            ('Direction des Ressources Humaines', 'DRH'),
            ('Production & Exploitation', 'PROD'),
            ('Finance & Comptabilité', 'FIN'),
            ('Logistique', 'LOG'),
            ('Informatique', 'IT'),
            ('Commercial', 'COM'),
            ('Juridique', 'JUR'),
        ]:
            _, created = Departement.objects.get_or_create(code=code, defaults={'nom': nom})
            if created:
                depts_crees += 1

        self.stdout.write('Création des types de congé...')
        types_crees = 0
        conge_data = [
            ('annuel',    'Congé annuel',    '#2196F3', 'fa-umbrella-beach', 24, False),
            ('maternite', 'Congé maternité', '#E91E63', 'fa-baby',           98, True),
            ('astreinte', 'Astreintes',      '#FF9800', 'fa-clock',          30, False),
        ]
        absence_data = [
            ('abs_maladie',        'Absence maladie',                           '#F44336', 'fa-hospital',        15, True),
            ('abs_sans_solde',     'Absence sans solde',                        '#607D8B', 'fa-money-bill-slash', 30, False),
            ('abs_exceptionnelle', 'Absence exceptionnelle (événement familial)','#FF9800', 'fa-star',             5, True),
            ('permission',         "Permission d'absence",                      '#9C27B0', 'fa-id-card',           3, False),
        ]
        for categorie, data in (('conge', conge_data), ('absence', absence_data)):
            for code, libelle, couleur, icone, jours_max, justif in data:
                _, created = TypeConge.objects.get_or_create(
                    code=code,
                    defaults={
                        'libelle': libelle,
                        'categorie': categorie,
                        'couleur': couleur,
                        'icone': icone,
                        'jours_max': jours_max,
                        'necessite_justificatif': justif,
                    }
                )
                if created:
                    types_crees += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n{depts_crees} département(s) créé(s), {types_crees} type(s) de congé/absence créé(s).\n'
            'Déjà présents : ignorés (relancer cette commande ne duplique rien).'
        ))
