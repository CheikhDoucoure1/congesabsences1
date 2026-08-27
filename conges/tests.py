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

from .models import Departement, DemandeConge, Employe, TypeConge
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
        self.manager_a = _employe('manager_a', role='manager', manager=self.drh)
        self.manager_b = _employe('manager_b', role='manager', manager=self.drh)
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
