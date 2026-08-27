"""Server-side validation for user-uploaded files.

The HTML `accept` attribute on file inputs is a UX hint only — it is
trivially bypassed by anyone crafting their own request, so every upload
must be re-checked here before it touches disk.
"""
import re
from django.core.exceptions import ValidationError

MO = 1024 * 1024

EXTENSIONS_JUSTIFICATIF = {'pdf', 'jpg', 'jpeg', 'png'}
EXTENSIONS_AVATAR = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
EXTENSIONS_IMPORT_EXCEL = {'xlsx', 'xlsm'}

TAILLE_MAX_JUSTIFICATIF = 5 * MO
TAILLE_MAX_AVATAR = 2 * MO
TAILLE_MAX_IMPORT_EXCEL = 5 * MO

COULEUR_HEX_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')


def valider_fichier(fichier, extensions_autorisees, taille_max):
    """Raise ValidationError if `fichier` fails the extension/size check.

    `fichier` is an UploadedFile (from request.FILES). Extension is
    validated against an allow-list (not a deny-list) and the declared
    size is capped — both trivially spoofable individually, but combined
    with Django's ImageField content sniffing (for avatars) this closes
    the obvious "rename a script to .pdf" / "upload a 500MB file" paths.
    """
    nom = fichier.name or ''
    ext = nom.rsplit('.', 1)[-1].lower() if '.' in nom else ''
    if ext not in extensions_autorisees:
        raise ValidationError(
            "Extension de fichier non autorisée (.%s). Extensions acceptées : %s."
            % (ext or '?', ', '.join(sorted(extensions_autorisees)))
        )
    if fichier.size > taille_max:
        raise ValidationError(
            "Le fichier est trop volumineux (%.1f Mo, maximum %.0f Mo)."
            % (fichier.size / MO, taille_max / MO)
        )
