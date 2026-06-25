"""
Commande pour peupler la base avec les employés PETROSEN.
Usage: python manage.py populate_employes
       python manage.py populate_employes --reset  (supprime les employés existants d'abord)
"""
from django.core.management.base import BaseCommand
from datetime import date
from conges.models import Employe, Departement, TypeConge, SoldeConge


class Command(BaseCommand):
    help = 'Peuple la base avec les 72 employés PETROSEN réels'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Supprime les employés non-admin avant de recréer')

    def handle(self, *args, **options):
        if options['reset']:
            deleted = Employe.objects.filter(is_superuser=False).exclude(
                username__in=['admin', 'drh', 'manager', 'employe']
            ).delete()
            self.stdout.write(f'  {deleted[0]} employés supprimés.')

        self.stdout.write('Création/mise à jour des directions...')
        depts = {}
        for nom, code in [
            ('Direction Générale',                          'DG'),
            ('Direction de la Production et Exploitation', 'DPEX'),
            ('Direction du Développement et des Projets',  'DDP'),
            ('Direction Financière et Comptable',          'DFC'),
            ('Contrôle de Gestion',                        'CG'),
        ]:
            d, _ = Departement.objects.get_or_create(code=code, defaults={'nom': nom})
            depts[code] = d

        # (prenom, nom, email, dept_code)
        employes = [
            ('Mamoudou',              'KA',        'm.ka@petrosen.sn',         'DG'),
            ('Ndeye Rokhaya',         'DIALLO',    'nr.diallo@petrosen.sn',    'DG'),
            ('Mouhamadou M. Nabi',    'GUEYE',     'mm.gueye@petrosen.sn',     'DPEX'),
            ('Mohamed Lamine',        'SONKO',     'ml.sonko@petrosen.sn',     'DPEX'),
            ('Amsata Siga',           'DIOP',      'as.diop@petrosen.sn',      'DDP'),
            ('Arsene Frédéric',       'BOISSY',    'af.boissy@petrosen.sn',    'DPEX'),
            ('Daouda',                'TIGAMPO',   'd.tigampo@petrosen.sn',    'DPEX'),
            ('EL Hadji Mansour',      'THIAM',     'ehm.thiam@petrosen.sn',    'DPEX'),
            ('Malick Ndiaye',         'SECK',      'mn.seck@petrosen.sn',      'DG'),
            ('Sokhna Khadidiatou',    'THIOYE',    'sk.thioye@petrosen.sn',    'DDP'),
            ('Moustapha',             'DIA',       'm.dia@petrosen.sn',        'DDP'),
            ('Massare Soundiata',     'KEITA',     'ms.keita@petrosen.sn',     'DG'),
            ('Amadou Baye',           'SY',        'ab.sy@petrosen.sn',        'DPEX'),
            ('Rouguiyatou',           'KAMARA',    'r.kamara@petrosen.sn',     'DG'),
            ('Alioune',               'SECK',      'a.seck@petrosen.sn',       'DG'),
            ('Ami',                   'SYLLA',     'a.sylla@petrosen.sn',      'DDP'),
            ('Adji Dievenaba',        'MBODJI',    'ad.mbodji@petrosen.sn',    'DPEX'),
            ('Marie Antoinette',      'BIAGUI',    'ma.biagui@petrosen.sn',    'DDP'),
            ('Coumba Ndofférié',      'DIOUF',     'cn.diouf@petrosen.sn',     'DFC'),
            ('Amadou Moctar',         'WADJI',     'am.wadji@petrosen.sn',     'DFC'),
            ('Massiré',               'KEITA',     'm.keita@petrosen.sn',      'DFC'),
            ('Ibrahima',              'KANTE',     'i.kante@petrosen.sn',      'DFC'),
            ('Mamadou',               'SENE',      'm.sene@petrosen.sn',       'DFC'),
            ('Ndiome',                'NDIONE',    'n.ndione@petrosen.sn',     'DFC'),
            ('Mansour',               'BAKHOUM',   'm.bakhoum@petrosen.sn',    'CG'),
            ('Mame Gnagna',           'AW',        'mg.aw@petrosen.sn',        'DG'),
            ('Noé Séckou Omar',       'DIEDHIOU',  'nso.diedhiou@petrosen.sn', 'CG'),
            ('Marie Justine',         'BARBOZA',   'mj.barboza@petrosen.sn',   'DG'),
            ('Alphonse',              'DIOUF',     'a.diouf@petrosen.sn',      'DDP'),
            ('Maty Babel',            'THIAM',     'mb.thiam@petrosen.sn',     'CG'),
            ('Ibrahima',              'NDOUR',     'i.ndour@petrosen.sn',      'DDP'),
            ('Aloise Ngor Mack',      'DIAGNE',    'anm.diagne@petrosen.sn',   'DDP'),
            ('Binta Ouleymatou',      'COULIBALY', 'bo.coulibaly@petrosen.sn', 'DFC'),
            ('Fanta',                 'CISSOKHO',  'f.cissokho@petrosen.sn',   'DG'),
            ('Marie Madeleine',       'MANSALY',   'mm.mansaly@petrosen.sn',   'DG'),
            ('Pape Mamadou',          'GASSAMA',   'pm.gassama@petrosen.sn',   'DFC'),
            ('Ndeye Khady',           'NDIAYE',    'nk.ndiaye@petrosen.sn',    'DDP'),
            ('Mouhamed Djim',         'KANE',      'md.kane@petrosen.sn',      'DDP'),
            ('Pape Macoura',          'DIA',       'pm.dia@petrosen.sn',       'DDP'),
            ('Fatou',                 'DIAKHATE',  'f.diakhate@petrosen.sn',   'DFC'),
            ('Mor',                   'FALL',      'm.fall@petrosen.sn',       'DFC'),
            ('Astou',                 'LEYE',      'a.leye@petrosen.sn',       'DPEX'),
            ('Moussa',                'BALDE',     'm.balde@petrosen.sn',      'DDP'),
            ('Ibrahima Sory',         'NOBA',      'is.noba@petrosen.sn',      'DDP'),
            ('Cheikh Tahirou',        'DOUCOURE',  'cdoucoure@petrosen.sn',    'DG'),
            ('Ababacar dit Bacar',    'MBENGUE',   'ab.mbengue@petrosen.sn',   'DPEX'),
            ('Cheikhou M Falilou',    'DIALLO',    'cmf.diallo@petrosen.sn',   'DFC'),
            ('Abdou Aziz',            'MBAYE',     'aa.mbaye@petrosen.sn',     'DFC'),
            ('Bassirou',              'KANE',      'b.kane@petrosen.sn',       'DFC'),
            ('Wokha',                 'BA',        'w.ba@petrosen.sn',         'DDP'),
            ('Cheikh Ahmeth Tidiane', 'NDIAYE',    'cat.ndiaye@petrosen.sn',   'DDP'),
            ('Alassane Oumar',        'BOCOUM',    'ao.bocoum@petrosen.sn',    'DPEX'),
            ('Ndiaye Waly',           'DIAKHATE',  'nw.diakhate@petrosen.sn',  'DPEX'),
            ('Fatoumata',             'KANE',      'f.kane@petrosen.sn',       'DG'),
            ('Boubacar',              'DIOP',      'b.diop@petrosen.sn',       'DFC'),
            ('Mor',                   'MBENGUE',   'm.mbengue@petrosen.sn',    'DFC'),
            ('Cheikh',                'GUEYE',     'c.gueye@petrosen.sn',      'DG'),
            ('Fatou Kinet',           'CISSE',     'fk.cisse@petrosen.sn',     'DG'),
            ('Ousseynou',             'SALL',      'o.sall@petrosen.sn',       'DDP'),
            ('Moussa',                'WADE',      'm.wade@petrosen.sn',       'DDP'),
            ('Papa Ousmane',          'FALL',      'po.fall@petrosen.sn',      'DDP'),
            ('Rose Marie Hélène',     'CORREA',    'rmh.correa@petrosen.sn',   'DDP'),
            ('Cheikh Tidiane',        'DIAGNE',    'ct.diagne@petrosen.sn',    'DDP'),
            ('Abdou Aziz',            'SOW',       'aa.sow@petrosen.sn',       'DDP'),
            ('Mohamed Idriss',        'DIOP',      'mi.diop@petrosen.sn',      'DDP'),
            ('Barnabé Vincent',       'COLY',      'bv.coly@petrosen.sn',      'DDP'),
            ('Abdoulahi',             'CISSE',     'a.cisse@petrosen.sn',      'DDP'),
            ('Mouhamed',              'NIANG',     'm.niang@petrosen.sn',      'DG'),
            ('Mame Bineta',           'MBENGUE',   'mb.mbengue@petrosen.sn',   'DG'),
            ('Tabara Seynabou Gaye',  'SY',        'tsg.sy@petrosen.sn',       'CG'),
            ('Alioune',               'DIAGNE',    'a.diagne@petrosen.sn',     'DPEX'),
            ('Pape Abdoulaye',        'TOURE',     'pa.toure@petrosen.sn',     'DG'),
        ]

        self.stdout.write(f'Traitement de {len(employes)} employés...')
        created_map = {}
        annee = date.today().year
        type_annuel = TypeConge.objects.filter(code='annuel').first()

        for prenom, nom, email, dept_code in employes:
            username = email.split('@')[0]
            dept = depts.get(dept_code)
            try:
                if Employe.objects.filter(email=email).exists():
                    emp = Employe.objects.get(email=email)
                    emp.first_name = prenom
                    emp.last_name = nom
                    emp.departement = dept
                    emp.actif = True
                    emp.save()
                    created_map[email] = emp
                    self.stdout.write(f'  ~ {prenom} {nom} — mis à jour')
                else:
                    if Employe.objects.filter(username=username).exists():
                        username = email.replace('@', '_').replace('.', '_')
                    emp = Employe.objects.create_user(
                        username=username,
                        email=email,
                        password='Petrosen2025!',
                        first_name=prenom,
                        last_name=nom,
                    )
                    emp.departement = dept
                    emp.role = 'employe'
                    emp.actif = True
                    emp.save()
                    created_map[email] = emp
                    self.stdout.write(f'  + {prenom} {nom}')

                if type_annuel:
                    SoldeConge.objects.get_or_create(
                        employe=created_map[email],
                        type_conge=type_annuel,
                        annee=annee,
                        defaults={'jours_acquis': 24, 'jours_pris': 0}
                    )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ {prenom} {nom} ({email}) : {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'\n{len(created_map)} employes crees/mis a jour avec succes.\n'
            f'Mot de passe par defaut : Petrosen2025!\n'
            f'Directions : DG, DPEX, DDP, DFC, CG'
        ))
