"""
Management command to import employee list from the staff roster.
Usage: python manage.py import_employes
"""
import unicodedata
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string
from conges.models import Employe, Departement, TypeConge, SoldeConge
from datetime import date


EMPLOYES = [
    ("Mamoudou",           "KA",         "DG"),
    ("Ndeye Rokhaya",      "DIALLO",     "DG"),
    ("Mouhamadou M. Nabi", "GUEYE",      "DG"),
    ("Mohamed Lamine",     "SONKO",      "DPEX"),
    ("Amsata Siga",        "DIOP",       "DDP"),
    ("Arsene Frederic",    "BOISSY",     "DPEX"),
    ("Daouda",             "TIGAMPO",    "DFC"),
    ("EL Hadji Mansour",   "THIAM",      "DPEX"),
    ("Malick",             "SECK",       "DG"),
    ("Sokhna Khadidiatou", "THIOYE",     "DDP"),
    ("Moustapha",          "DIA",        "DDP"),
    ("Massare Soundiata",  "KEITA",      "DG"),
    ("Amadou Baye",        "SY",         "DPEX"),
    ("Rouguiyatou",        "KAMARA",     "DG"),
    ("Afioune",            "SECK",       "DG"),
    ("Ami",                "SYLLA",      "DDP"),
    ("Adji Dievenaba",     "MBODJI",     "DPEX"),
    ("Marie Antoinette",   "BIAGUI",     "DFC"),
    ("Coumba Ndoffene",    "DIOUF",      "DFC"),
    ("Amadou Moctar",      "WADJI",      "DFC"),
    ("Massire",            "KEITA",      "DFC"),
    ("Ibrahima",           "KANTE",      "DFC"),
    ("Mamadou",            "SENE",       "DFC"),
    ("Ndiome",             "NDIONE",     "DFC"),
    ("Mansour",            "BAKHOUM",    "CG"),
    ("Mame Gnagna",        "AW",         "DG"),
    ("Noe Seckou Omar",    "DIEDHIOU",   "CG"),
    ("Marie Justine",      "BARBOZA",    "DG"),
    ("Alphonse",           "DIOUF",      "DDP"),
    ("Matu Babel",         "THIAM",      "CG"),
    ("Ibrahima",           "NDOUR",      "DDP"),
    ("Aloise Ngor Mack",   "DIAGNE",     "DDP"),
    ("Binta Ouleymatou",   "COULIBALY",  "DFC"),
    ("Fanta",              "DISSOKHO",   "DG"),
    ("Marie Madeleine",    "MANSALY",    "DG"),
    ("Pape Mamadou",       "GASSAMA",    "DFC"),
    ("Ndeye Khady",        "NDIAYE",     "DDP"),
    ("Mouhamed Djim",      "KANE",       "DDP"),
    ("Pape Macoura",       "DIA",        "DDP"),
    ("Fatou",              "DIAKHATE",   "DFC"),
    ("Mor",                "FALL",       "DFC"),
    ("Astou",              "LEYE",       "DPEX"),
    ("Moussa",             "BALDE",      "DDP"),
    ("Ibrahima Sory",      "NOBA",       "DDP"),
    ("Cheikh Tahirou",     "DOUCOURE",   "DG"),
    ("Ababacar dit Bacar", "MBENGUE",    "DPEX"),
    ("Cheikhou M Fallilou","DIALLO",     "DFC"),
    ("Abdou Aziz",         "MBAYE",      "DFC"),
    ("Bassirou",           "KANE",       "DFC"),
    ("Wokha",              "BA",         "DDP"),
    ("Cheikh Ahmeth Tidiane","NDIAYE",   "DDP"),
    ("Alassane Oumar",     "BOCOUM",     "DPEX"),
    ("Ndiaye Waly",        "DIAKHATE",   "DPEX"),
    ("Fatoumata",          "KANE",       "DG"),
    ("Boubacar",           "DIOP",       "DFC"),
    ("Mor",                "MBENGUE",    "DFC"),
    ("Cheikh",             "GUEYE",      "DG"),
    ("Fatou Kinet",        "CISSE",      "DG"),
    ("Ousseynou",          "SALL",       "DDP"),
    ("Moussa",             "WADE",       "DDP"),
    ("Papa Ousmane",       "FALL",       "DDP"),
    ("Rose Marie Helene",  "CORREA",     "DDP"),
    ("Cheikh Tidiane",     "DIAGNE",     "DDP"),
    ("Abdou Aziz",         "SOW",        "DDP"),
    ("Mohamed Idriss",     "DIOP",       "DDP"),
    ("Barnabe Vincent",    "COLY",       "DDP"),
    ("Abdoulahi",          "CISSE",      "DDP"),
    ("Mouhamed",           "NIANG",      "DG"),
    ("Mame Bineta",        "MBENGUE",    "DG"),
    ("Tabara Seynabou Gaye","SY",        "CG"),
    ("Afioune",            "DIAGNE",     "DPEX"),
    ("Pape Abdoulaye",     "TOURE",      "DG"),
]

DIRECTIONS = {
    "DG":   "Direction Générale",
    "DPEX": "Direction de la Production et de l'Exploitation",
    "DDP":  "Direction du Développement et des Projets",
    "DFC":  "Direction Financière et de la Comptabilité",
    "CG":   "Contrôle de Gestion",
}


def slugify_simple(text):
    """Normalize accented characters and lowercase."""
    nfkd = unicodedata.normalize('NFKD', text)
    ascii_str = nfkd.encode('ascii', 'ignore').decode('ascii')
    return ascii_str.lower().replace(' ', '.').replace('-', '.').replace("'", '').replace('.', '_', )


class Command(BaseCommand):
    help = "Importe les employés depuis la liste du personnel"

    def handle(self, *args, **options):
        annee = date.today().year

        # 1. Ensure departments exist
        self.stdout.write("Creation des directions...")
        depts = {}
        for code, nom in DIRECTIONS.items():
            dept, created = Departement.objects.get_or_create(code=code, defaults={"nom": nom})
            depts[code] = dept
            if created:
                self.stdout.write(f"  + {code}: {nom}")

        # 2. Get leave types for balances
        types_conge = {t.code: t for t in TypeConge.objects.all()}

        # 3. Import employees
        self.stdout.write("Import des employes...")
        created_count = 0
        skipped_count = 0
        used_usernames = set(Employe.objects.values_list('username', flat=True))

        for prenom, nom, direction in EMPLOYES:
            dept = depts.get(direction)

            # Build a unique username: prenom_nom (normalized)
            base = slugify_simple(f"{prenom}_{nom}")
            username = base
            counter = 2
            while username in used_usernames:
                username = f"{base}{counter}"
                counter += 1
            used_usernames.add(username)

            email = f"{username}@petrosen.sn"

            if Employe.objects.filter(email=email).exists():
                skipped_count += 1
                continue

            mot_de_passe = get_random_string(12)
            emp = Employe.objects.create_user(
                username=username,
                email=email,
                password=mot_de_passe,
                first_name=prenom,
                last_name=nom,
            )
            emp.role = "employe"
            emp.departement = dept
            emp.actif = True
            emp.save()
            self.stdout.write(f"    mot de passe : {mot_de_passe}")

            # Create annual leave balance (24 days acquired, 0 taken)
            if "annuel" in types_conge:
                SoldeConge.objects.get_or_create(
                    employe=emp,
                    type_conge=types_conge["annuel"],
                    annee=annee,
                    defaults={"jours_acquis": 24, "jours_pris": 0},
                )

            created_count += 1
            self.stdout.write(f"  + {prenom} {nom} ({direction})")

        self.stdout.write(f"\n{created_count} employes crees, {skipped_count} ignores (deja existants).")
        self.stdout.write(
            "Un mot de passe aleatoire a ete genere pour chaque nouveau compte (affiche ci-dessus). "
            "Transmettez-les individuellement et demandez leur changement des la premiere connexion."
        )
