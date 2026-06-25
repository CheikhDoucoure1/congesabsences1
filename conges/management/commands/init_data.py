"""
Management command to populate initial demo data.
Usage: python manage.py init_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from conges.models import Employe, Departement, TypeConge, SoldeConge, DemandeConge


class Command(BaseCommand):
    help = 'Initialise les données de démonstration'

    def handle(self, *args, **options):
        self.stdout.write('Création des départements...')
        depts = {}
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
            d, _ = Departement.objects.get_or_create(code=code, defaults={'nom': nom})
            depts[code] = d

        self.stdout.write('Création des types de congé...')
        types = {}
        conge_data = [
            ('annuel',    'Congé annuel',    '#2196F3', 'fa-umbrella-beach', 24, False),
            ('maternite', 'Congé maternité', '#E91E63', 'fa-baby',           98, True),
            ('astreinte', 'Astreintes',      '#FF9800', 'fa-clock',          30, False),
        ]
        for code, libelle, couleur, icone, jours_max, justif in conge_data:
            t, _ = TypeConge.objects.get_or_create(
                code=code,
                defaults={
                    'libelle': libelle,
                    'categorie': 'conge',
                    'couleur': couleur,
                    'icone': icone,
                    'jours_max': jours_max,
                    'necessite_justificatif': justif,
                }
            )
            types[code] = t

        absence_data = [
            ('abs_maladie',        'Absence maladie',                           '#F44336', 'fa-hospital',        15, True),
            ('abs_sans_solde',     'Absence sans solde',                        '#607D8B', 'fa-money-bill-slash', 30, False),
            ('abs_exceptionnelle', 'Absence exceptionnelle (événement familial)','#FF9800', 'fa-star',             5, True),
            ('permission',         "Permission d'absence",                      '#9C27B0', 'fa-id-card',           3, False),
        ]
        for code, libelle, couleur, icone, jours_max, justif in absence_data:
            t, _ = TypeConge.objects.get_or_create(
                code=code,
                defaults={
                    'libelle': libelle,
                    'categorie': 'absence',
                    'couleur': couleur,
                    'icone': icone,
                    'jours_max': jours_max,
                    'necessite_justificatif': justif,
                }
            )
            types[code] = t

        self.stdout.write('Création des utilisateurs...')
        annee = date.today().year

        def make_user(username, email, password, first, last, role, dept_code, poste, manager=None):
            if Employe.objects.filter(username=username).exists():
                return Employe.objects.get(username=username)
            u = Employe.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first,
                last_name=last,
            )
            u.role = role
            u.departement = depts.get(dept_code)
            u.poste = poste
            u.manager = manager
            u.actif = True
            u.save()
            return u

        admin = make_user('admin', 'admin@petrosen.sn', 'admin123',
                          'Système', 'Admin', 'admin', 'IT', 'Administrateur Système')
        drh = make_user('drh', 'drh@petrosen.sn', 'password',
                        'Aïssatou', 'Ndiaye', 'rh', 'DRH', 'Directrice des Ressources Humaines')
        manager = make_user('manager', 'manager@petrosen.sn', 'password',
                            'Ibrahim', 'Diop', 'manager', 'PROD',
                            'Chef de Département Production', manager=drh)
        employe = make_user('employe', 'employe@petrosen.sn', 'password',
                            'Mariama', 'Ba', 'employe', 'PROD',
                            'Ingénieure Process', manager=manager)
        emp2 = make_user('o.fall', 'o.fall@petrosen.sn', 'password',
                         'Ousmane', 'Fall', 'employe', 'LOG',
                         'Responsable Logistique', manager=drh)
        emp3 = make_user('k.sarr', 'k.sarr@petrosen.sn', 'password',
                         'Khadija', 'Sarr', 'employe', 'FIN',
                         'Comptable Senior', manager=drh)
        emp4 = make_user('m.thiam', 'm.thiam@petrosen.sn', 'password',
                         'Modou', 'Thiam', 'employe', 'PROD',
                         'Technicien Process', manager=manager)

        self.stdout.write('Création des soldes de congé...')
        balance_data = {
            admin: {'annuel': (24,0), 'astreinte': (30, 0)},
            drh: {'annuel': (24,5), 'astreinte': (30, 0)},
            manager: {'annuel': (24,8), 'astreinte': (30, 5)},
            employe: {'annuel': (24,12), 'astreinte': (30, 0)},
            emp2: {'annuel': (24,20), 'astreinte': (30, 3)},
            emp3: {'annuel': (24,3), 'astreinte': (30, 0)},
            emp4: {'annuel': (24,7), 'astreinte': (30, 0)},
        }
        for user, balances in balance_data.items():
            for type_code, (acquis, pris) in balances.items():
                SoldeConge.objects.get_or_create(
                    employe=user,
                    type_conge=types[type_code],
                    annee=annee,
                    defaults={'jours_acquis': acquis, 'jours_pris': pris}
                )

        self.stdout.write('Création des demandes de congé...')
        today = date.today()

        demandes_data = [
            {
                'employe': employe,
                'type': types['annuel'],
                'debut': today - timedelta(days=60),
                'fin': today - timedelta(days=51),
                'statut': 'approuve',
                'motif': 'Vacances de fin d\'année en famille',
                'traite_par': manager,
                'commentaire': 'Approuvé. Bonnes vacances!',
            },
            {
                'employe': emp2,
                'type': types['annuel'],
                'debut': today + timedelta(days=10),
                'fin': today + timedelta(days=20),
                'statut': 'en_attente',
                'motif': 'Vacances estivales',
                'traite_par': None,
                'commentaire': '',
            },
            {
                'employe': manager,
                'type': types['annuel'],
                'debut': today + timedelta(days=30),
                'fin': today + timedelta(days=41),
                'statut': 'en_attente',
                'motif': 'Vacances d\'été planifiées',
                'traite_par': None,
                'commentaire': '',
            },
            {
                'employe': emp4,
                'type': types['astreinte'],
                'debut': today - timedelta(days=5),
                'fin': today - timedelta(days=3),
                'statut': 'approuve',
                'motif': 'Astreinte de nuit',
                'traite_par': manager,
                'commentaire': '',
            },
            {
                'employe': employe,
                'type': types['annuel'],
                'debut': today + timedelta(days=60),
                'fin': today + timedelta(days=70),
                'statut': 'en_attente',
                'motif': 'Voyage familial planifié',
                'traite_par': None,
                'commentaire': '',
            },
        ]

        for i, d in enumerate(demandes_data):
            if DemandeConge.objects.filter(employe=d['employe'], date_debut=d['debut']).exists():
                continue
            dem = DemandeConge(
                employe=d['employe'],
                type_conge=d['type'],
                date_debut=d['debut'],
                date_fin=d['fin'],
                motif=d['motif'],
                statut=d['statut'],
                traite_par=d['traite_par'],
                commentaire_traitement=d['commentaire'],
            )
            if d['statut'] != 'en_attente' and d['traite_par']:
                dem.date_traitement = timezone.now() - timedelta(days=i)
            dem.save()

        self.stdout.write(self.style.SUCCESS('\n✅ Données initialisées avec succès!\n'))
        self.stdout.write('Comptes de connexion :')
        self.stdout.write('  Admin    : admin@petrosen.sn / admin123')
        self.stdout.write('  DRH      : drh@petrosen.sn / password')
        self.stdout.write('  Manager  : manager@petrosen.sn / password')
        self.stdout.write('  Employé  : employe@petrosen.sn / password')
