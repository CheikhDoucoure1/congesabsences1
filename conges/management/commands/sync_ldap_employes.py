"""Pre-provision a local shell account for every real Active Directory user
— not just the ones who have already logged in at least once.

Why: the "supérieur direct" search bar on the leave request form only
searches local Employe rows. Without this command, someone who has never
logged into the app yet simply doesn't show up there, even though they
are a real employee in AD. Run this periodically (e.g. a nightly cron
job) to keep the local roster in step with the directory.

A pre-provisioned account has no usable local password — exactly like an
account created by an actual LDAP login (see conges/ldap_hooks.py). When
that real person logs in via LDAP for the first time, django-auth-ldap's
get_or_create matches them by username and adopts this same row (updates
attributes, does not create a duplicate) — so any notification or email
sent to them beforehand (e.g. because they were picked as someone's
supérieur) is already sitting there waiting.

Existing accounts (already logged in before, or created by RH by hand)
only get their name/email refreshed from AD — role, manager, matricule,
actif and any local password some RH may have deliberately set are never
touched by this command.

Usage: python manage.py sync_ldap_employes
"""
import ldap
from ldap.controls import SimplePagedResultsControl

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from conges.models import Employe

TAILLE_PAGE = 500


def _connexion_ldap():
    conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
    conn.set_option(ldap.OPT_REFERRALS, 0)
    conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 15)
    conn.set_option(ldap.OPT_TIMEOUT, 15)
    ca_cert = getattr(settings, 'AUTH_LDAP_CONNECTION_OPTIONS', {}).get(ldap.OPT_X_TLS_CACERTFILE)
    if ca_cert:
        conn.set_option(ldap.OPT_X_TLS_CACERTFILE, ca_cert)
        conn.set_option(ldap.OPT_X_TLS_NEWCTX, 0)
    if getattr(settings, 'AUTH_LDAP_START_TLS', False):
        conn.start_tls_s()
    conn.simple_bind_s(settings.AUTH_LDAP_BIND_DN, settings.AUTH_LDAP_BIND_PASSWORD)
    return conn


def rechercher_utilisateurs_ad(conn, base_dn, filtre, attrs):
    """Yields (dn, attrs_dict) for every matching entry, paging through
    results (RFC 2696) so this doesn't silently truncate at whatever the
    DC's default result-size cap is (often 1000)."""
    controle_page = SimplePagedResultsControl(True, size=TAILLE_PAGE, cookie='')
    while True:
        msgid = conn.search_ext(base_dn, ldap.SCOPE_SUBTREE, filtre, attrs, serverctrls=[controle_page])
        _, resultats, _, controles = conn.result3(msgid)
        for dn, entree in resultats:
            if dn is not None:  # ignore les continuations/référentiels
                yield dn, entree

        controles_page = [c for c in controles if c.controlType == SimplePagedResultsControl.controlType]
        if not controles_page or not controles_page[0].cookie:
            break
        controle_page.cookie = controles_page[0].cookie


def _valeur(entree, attribut):
    valeurs = entree.get(attribut)
    if not valeurs:
        return ''
    return valeurs[0].decode('utf-8', errors='replace').strip()


class Command(BaseCommand):
    help = "Crée/actualise un compte local (sans mot de passe utilisable) pour chaque utilisateur Active Directory actif"

    def handle(self, *args, **options):
        if not getattr(settings, 'AUTH_LDAP_ENABLED', False):
            raise CommandError("LDAP n'est pas activé (DJANGO_LDAP_ENABLED) — rien à synchroniser.")

        attr_map = settings.AUTH_LDAP_USER_ATTR_MAP
        attrs = ['sAMAccountName', attr_map['first_name'], attr_map['last_name'], attr_map['email']]
        # Comptes utilisateurs réels, actifs uniquement (bit ACCOUNTDISABLE,
        # 0x2, absent de userAccountControl) — pas les groupes, ordinateurs,
        # comptes de service désactivés, etc.
        filtre = '(&(objectClass=user)(objectCategory=person)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))'

        try:
            conn = _connexion_ldap()
        except ldap.LDAPError as e:
            raise CommandError(f"Connexion LDAP impossible : {e}")

        try:
            entrees = list(rechercher_utilisateurs_ad(conn, settings.AUTH_LDAP_BASE_DN, filtre, attrs))
        except ldap.LDAPError as e:
            raise CommandError(f"Recherche LDAP impossible : {e}")
        finally:
            conn.unbind_s()

        self.stdout.write(f"{len(entrees)} compte(s) trouvé(s) dans l'annuaire.")
        crees, actualises, ignores = 0, 0, 0

        for dn, entree in entrees:
            username = _valeur(entree, 'sAMAccountName')
            email = _valeur(entree, attr_map['email'])
            prenom = _valeur(entree, attr_map['first_name'])
            nom = _valeur(entree, attr_map['last_name'])
            if not username or not email:
                ignores += 1
                continue

            try:
                emp = Employe.objects.get(username=username)
                changement = False
                for champ, valeur in (('first_name', prenom), ('last_name', nom), ('email', email)):
                    if valeur and getattr(emp, champ) != valeur:
                        setattr(emp, champ, valeur)
                        changement = True
                if changement:
                    emp.save()
                    actualises += 1
            except Employe.DoesNotExist:
                Employe.objects.create_user(
                    username=username,
                    email=email,
                    password=None,  # -> set_unusable_password(), comme un vrai login LDAP
                    first_name=prenom,
                    last_name=nom,
                )
                crees += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n{crees} compte(s) créé(s), {actualises} actualisé(s), "
            f"{ignores} ignoré(s) (sans identifiant ou email exploitable)."
        ))
