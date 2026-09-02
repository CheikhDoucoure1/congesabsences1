"""Regression tests for the access-control and input-validation fixes.

These pin down the behaviours found during the security review: without
them, a future refactor could silently reopen the same holes.
"""
from datetime import date, timedelta

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Departement, DemandeConge, Employe, HistoriqueModification, SoldeConge, TypeConge
from .validators import EXTENSIONS_JUSTIFICATIF, TAILLE_MAX_JUSTIFICATIF, valider_fichier
from .views import LOGIN_MAX_TENTATIVES, _next_url_sure, _roles_autorises_pour


def _employe(username, role='employe', manager=None, **extra):
    emp = Employe.objects.create_user(
        username=username, email=f'{username}@petrosen.sn', password='x' * 12,
        first_name=username, last_name='Test',
    )
    emp.role = role
    emp.manager = manager
    emp.actif = True
    for k, v in extra.items():
        setattr(emp, k, v)
    emp.save()
    return emp


def _type_conge():
    return TypeConge.objects.create(code='annuel', libelle='Congé annuel', jours_max=24)


class AccessControlTests(TestCase):
    """Findings #1/#2 — a manager must be scoped to their own team."""

    def setUp(self):
        self.type_conge = _type_conge()
        self.drh = _employe('drh', role='rh')
        self.manager_a = _employe('manager_a', role='employe', manager=self.drh)
        self.manager_b = _employe('manager_b', role='employe', manager=self.drh)
        self.emp_a = _employe('emp_a', role='employe', manager=self.manager_a)
        self.emp_b = _employe('emp_b', role='employe', manager=self.manager_b)
        self.demande_b = DemandeConge.objects.create(
            employe=self.emp_b, type_conge=self.type_conge,
            date_debut=date.today() + timedelta(days=5),
            date_fin=date.today() + timedelta(days=6),
        )

    def test_manager_ne_voit_pas_la_demande_dune_autre_equipe(self):
        self.client.force_login(self.manager_a)
        resp = self.client.get(reverse('detail_demande', args=[self.demande_b.id]))
        self.assertEqual(resp.status_code, 404)

    def test_manager_ne_peut_pas_traiter_la_demande_dune_autre_equipe(self):
        self.client.force_login(self.manager_a)
        resp = self.client.post(
            reverse('traiter_demande', args=[self.demande_b.id]),
            {'action': 'approuver', 'commentaire': ''},
        )
        self.assertEqual(resp.status_code, 404)
        self.demande_b.refresh_from_db()
        self.assertEqual(self.demande_b.statut, 'en_attente')

    def test_manager_voit_bien_la_demande_de_sa_propre_equipe(self):
        demande_a = DemandeConge.objects.create(
            employe=self.emp_a, type_conge=self.type_conge,
            date_debut=date.today() + timedelta(days=5),
            date_fin=date.today() + timedelta(days=6),
        )
        self.client.force_login(self.manager_a)
        resp = self.client.get(reverse('detail_demande', args=[demande_a.id]))
        self.assertEqual(resp.status_code, 200)

    def test_personne_ne_peut_traiter_sa_propre_demande(self):
        demande_drh = DemandeConge.objects.create(
            employe=self.drh, type_conge=self.type_conge,
            date_debut=date.today() + timedelta(days=5),
            date_fin=date.today() + timedelta(days=6),
        )
        self.client.force_login(self.drh)
        self.client.post(
            reverse('traiter_demande', args=[demande_drh.id]),
            {'action': 'approuver', 'commentaire': ''},
        )
        demande_drh.refresh_from_db()
        self.assertEqual(demande_drh.statut, 'en_attente')

    def test_justificatif_non_accessible_a_un_manager_hors_equipe(self):
        fichier = SimpleUploadedFile('note.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        self.demande_b.justificatif = fichier
        self.demande_b.save()
        self.client.force_login(self.manager_a)
        resp = self.client.get(reverse('voir_justificatif', args=[self.demande_b.id]))
        self.assertEqual(resp.status_code, 404)


class RoleEscalationTests(TestCase):
    """Finding #8 — rh must not be able to grant admin/dg."""

    def test_rh_ne_peut_pas_sattribuer_le_role_admin(self):
        rh = _employe('un_rh', role='rh')
        self.assertNotIn('admin', _roles_autorises_pour(rh))
        self.assertNotIn('dg', _roles_autorises_pour(rh))

    def test_admin_peut_attribuer_nimporte_quel_role(self):
        admin = _employe('un_admin', role='admin')
        self.assertIn('admin', _roles_autorises_pour(admin))
        self.assertIn('dg', _roles_autorises_pour(admin))


class OpenRedirectTests(TestCase):
    """Finding #7 — ?next= must never leave the app's own host."""

    def test_url_externe_rejetee(self):
        factory_request = self.client.get('/connexion/').wsgi_request
        self.assertEqual(_next_url_sure(factory_request, 'https://evil.example.com/'), 'tableau_de_bord')

    def test_chemin_local_accepte(self):
        factory_request = self.client.get('/connexion/').wsgi_request
        self.assertEqual(_next_url_sure(factory_request, '/mes-demandes/'), '/mes-demandes/')


class LoginThrottleTests(TestCase):
    """Finding #12 — brute-force protection on the login form."""

    def setUp(self):
        cache.clear()
        _employe('bob', role='employe')

    def test_blocage_apres_trop_de_tentatives_echouees(self):
        for _ in range(LOGIN_MAX_TENTATIVES):
            self.client.post(reverse('connexion'), {'email': 'bob@petrosen.sn', 'password': 'mauvais'})
        resp = self.client.post(
            reverse('connexion'), {'email': 'bob@petrosen.sn', 'password': 'x' * 12}, follow=True
        )
        # Even with the correct password, the account stays logged out once throttled.
        self.assertFalse(resp.context['request'].user.is_authenticated if 'request' in resp.context else False)


class FileValidatorTests(TestCase):
    """Finding #6 — server-side file type/size checks."""

    def test_extension_non_autorisee_rejetee(self):
        fichier = SimpleUploadedFile('malware.exe', b'x' * 10, content_type='application/octet-stream')
        with self.assertRaises(ValidationError):
            valider_fichier(fichier, EXTENSIONS_JUSTIFICATIF, TAILLE_MAX_JUSTIFICATIF)

    def test_fichier_trop_volumineux_rejete(self):
        fichier = SimpleUploadedFile('note.pdf', b'x' * (TAILLE_MAX_JUSTIFICATIF + 1), content_type='application/pdf')
        with self.assertRaises(ValidationError):
            valider_fichier(fichier, EXTENSIONS_JUSTIFICATIF, TAILLE_MAX_JUSTIFICATIF)

    def test_fichier_valide_accepte(self):
        fichier = SimpleUploadedFile('note.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        valider_fichier(fichier, EXTENSIONS_JUSTIFICATIF, TAILLE_MAX_JUSTIFICATIF)  # ne doit pas lever


class SoldeInsuffisantTests(TestCase):
    """Une demande ne doit pas pouvoir dépasser le solde restant de
    l'employé pour ce type de congé (§ revue de workflow)."""

    def setUp(self):
        self.type_conge = _type_conge()
        chef = _employe('chef_sarah', role='employe')
        self.employe = _employe('sarah', role='employe', manager=chef)
        SoldeConge.objects.create(
            employe=self.employe, type_conge=self.type_conge, annee=date.today().year,
            jours_acquis=24, jours_pris=22,  # il ne reste que 2 jours
        )

    def _soumettre(self, debut, fin):
        self.client.force_login(self.employe)
        return self.client.post(reverse('nouvelle_demande'), {
            'type_conge': self.type_conge.id,
            'date_debut': debut.isoformat(),
            'date_fin': fin.isoformat(),
        })

    def test_demande_qui_depasse_le_solde_est_refusee(self):
        debut = date.today() + timedelta(days=10)
        fin = debut + timedelta(days=9)  # dépasse largement les 2 jours restants
        self._soumettre(debut, fin)
        self.assertFalse(DemandeConge.objects.filter(employe=self.employe).exists())

    def test_demande_dans_la_limite_du_solde_est_acceptee(self):
        # Choisit deux jours ouvrés consécutifs pour rester dans le solde de 2j.
        debut = date.today() + timedelta(days=10)
        while debut.weekday() >= 5:
            debut += timedelta(days=1)
        fin = debut + timedelta(days=1)
        while fin.weekday() >= 5:
            fin += timedelta(days=1)
        self._soumettre(debut, fin)
        self.assertTrue(DemandeConge.objects.filter(employe=self.employe).exists())

    def test_aucun_solde_initialise_nempeche_pas_la_demande(self):
        # Un nouvel employé sans solde encore initialisé ne doit pas être
        # bloqué — c'est un problème de configuration RH, pas une fraude.
        chef = _employe('chef_nouveau', role='employe')
        autre = _employe('nouveau', role='employe', manager=chef)
        self.client.force_login(autre)
        debut = date.today() + timedelta(days=10)
        while debut.weekday() >= 5:
            debut += timedelta(days=1)
        fin = debut + timedelta(days=1)
        while fin.weekday() >= 5:
            fin += timedelta(days=1)
        self.client.post(reverse('nouvelle_demande'), {
            'type_conge': self.type_conge.id,
            'date_debut': debut.isoformat(),
            'date_fin': fin.isoformat(),
        })
        self.assertTrue(DemandeConge.objects.filter(employe=autre).exists())


class ModifierEmployeTests(TestCase):
    """L'écran 'modifier un employé' : rattachement manager/département/rôle,
    prévention des boucles hiérarchiques, désactivation, journal d'audit."""

    def setUp(self):
        self.admin = _employe('un_admin', role='admin')
        self.rh = _employe('un_rh', role='rh')
        self.dept = Departement.objects.create(nom='Production', code='PROD')
        self.chef = _employe('chef_equipe', role='employe')
        self.membre = _employe('membre_equipe', role='employe', manager=self.chef)

    def test_rh_peut_rattacher_manager_et_departement(self):
        self.client.force_login(self.rh)
        nouveau = _employe('nouveau_ldap', role='employe')  # simule un compte auto-créé par LDAP
        resp = self.client.post(reverse('modifier_employe', args=[nouveau.id]), {
            'prenom': nouveau.first_name, 'nom': nouveau.last_name,
            'poste': 'Technicien', 'role': 'employe',
            'departement': self.dept.id, 'manager': self.chef.id,
            'actif': 'on',
        })
        nouveau.refresh_from_db()
        self.assertEqual(nouveau.departement_id, self.dept.id)
        self.assertEqual(nouveau.manager_id, self.chef.id)
        self.assertTrue(HistoriqueModification.objects.filter(employe_concerne=nouveau, type_action='employe_modifie').exists())

    def test_rh_ne_peut_pas_promouvoir_quelquun_admin(self):
        self.client.force_login(self.rh)
        self.client.post(reverse('modifier_employe', args=[self.membre.id]), {
            'prenom': self.membre.first_name, 'nom': self.membre.last_name,
            'poste': '', 'role': 'admin', 'actif': 'on',
        })
        self.membre.refresh_from_db()
        self.assertNotEqual(self.membre.role, 'admin')

    def test_boucle_hierarchique_refusee(self):
        # Le chef ne peut pas être placé sous son propre subordonné.
        self.client.force_login(self.rh)
        resp = self.client.post(reverse('modifier_employe', args=[self.chef.id]), {
            'prenom': self.chef.first_name, 'nom': self.chef.last_name,
            'poste': '', 'role': 'manager', 'manager': self.membre.id, 'actif': 'on',
        })
        self.chef.refresh_from_db()
        self.assertIsNone(self.chef.manager_id)

    def test_desactivation_bloque_la_connexion(self):
        self.client.force_login(self.rh)
        self.client.post(reverse('toggle_actif_employe', args=[self.membre.id]))
        self.membre.refresh_from_db()
        self.assertFalse(self.membre.actif)
        self.assertTrue(
            HistoriqueModification.objects.filter(employe_concerne=self.membre, type_action='employe_desactive').exists()
        )
        self.client.logout()
        # client.login() n'exercerait que Django.authenticate() — le champ
        # `actif` de l'app n'est vérifié que dans la vue connexion() elle-même.
        self.client.post(reverse('connexion'), {'email': self.membre.email, 'password': 'x' * 12})
        self.assertFalse(self.client.session.get('_auth_user_id'))

    def test_reactivation(self):
        self.membre.actif = False
        self.membre.save()
        self.client.force_login(self.rh)
        self.client.post(reverse('toggle_actif_employe', args=[self.membre.id]))
        self.membre.refresh_from_db()
        self.assertTrue(self.membre.actif)

    def test_impossible_de_se_desactiver_soi_meme(self):
        self.client.force_login(self.rh)
        self.client.post(reverse('toggle_actif_employe', args=[self.rh.id]))
        self.rh.refresh_from_db()
        self.assertTrue(self.rh.actif)

    def test_employe_ne_peut_pas_acceder_a_lecran(self):
        self.client.force_login(self.membre)
        resp = self.client.get(reverse('modifier_employe', args=[self.chef.id]))
        self.assertEqual(resp.status_code, 302)  # redirigé, accès refusé


class DeclarationSuperieurTests(TestCase):
    """Un employé sans manager assigné (typiquement un compte LDAP tout
    juste auto-créé) doit pouvoir en indiquer un à sa première demande —
    mais jamais en changer une fois qu'il en a déjà un."""

    def setUp(self):
        self.type_conge = _type_conge()
        self.chef = _employe('chef', role='employe')
        self.autre_chef = _employe('autre_chef', role='employe')
        self.rh = _employe('rh_verif', role='rh')
        self.sans_manager = _employe('nouveau_ldap', role='employe')  # manager=None

    def _dates_valides(self):
        debut = date.today() + timedelta(days=10)
        while debut.weekday() >= 5:
            debut += timedelta(days=1)
        fin = debut + timedelta(days=1)
        while fin.weekday() >= 5:
            fin += timedelta(days=1)
        return debut, fin

    def test_champ_requis_si_pas_de_manager(self):
        self.client.force_login(self.sans_manager)
        debut, fin = self._dates_valides()
        # Pas de "superieur" fourni -> refusé
        self.client.post(reverse('nouvelle_demande'), {
            'type_conge': self.type_conge.id,
            'date_debut': debut.isoformat(), 'date_fin': fin.isoformat(),
        })
        self.assertFalse(DemandeConge.objects.filter(employe=self.sans_manager).exists())

    def test_superieur_declare_devient_le_manager_permanent(self):
        self.client.force_login(self.sans_manager)
        debut, fin = self._dates_valides()
        self.client.post(reverse('nouvelle_demande'), {
            'type_conge': self.type_conge.id,
            'date_debut': debut.isoformat(), 'date_fin': fin.isoformat(),
            'superieur': self.chef.id,
        })
        self.sans_manager.refresh_from_db()
        self.assertEqual(self.sans_manager.manager_id, self.chef.id)
        self.assertTrue(DemandeConge.objects.filter(employe=self.sans_manager).exists())
        self.assertTrue(
            HistoriqueModification.objects.filter(
                employe_concerne=self.sans_manager, type_action='employe_modifie', auteur=self.sans_manager
            ).exists()
        )
        # Le RH est notifié pour pouvoir vérifier/corriger.
        self.assertTrue(self.rh.notifications.filter(titre__icontains='Supérieur déclaré').exists())

    def test_le_champ_napparait_plus_une_fois_le_manager_fixe(self):
        self.sans_manager.manager = self.chef
        self.sans_manager.save()
        self.client.force_login(self.sans_manager)
        resp = self.client.get(reverse('nouvelle_demande'))
        self.assertNotContains(resp, 'name="superieur"')

    def test_impossible_de_changer_de_manager_via_ce_formulaire(self):
        # Un employé qui a déjà un manager ne peut pas en indiquer un autre
        # via ce champ — il n'est simplement jamais proposé/pris en compte.
        self.sans_manager.manager = self.chef
        self.sans_manager.save()
        self.client.force_login(self.sans_manager)
        debut, fin = self._dates_valides()
        self.client.post(reverse('nouvelle_demande'), {
            'type_conge': self.type_conge.id,
            'date_debut': debut.isoformat(), 'date_fin': fin.isoformat(),
            'superieur': self.autre_chef.id,
        })
        self.sans_manager.refresh_from_db()
        self.assertEqual(self.sans_manager.manager_id, self.chef.id)  # inchangé
