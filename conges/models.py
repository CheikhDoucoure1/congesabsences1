from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from datetime import date, timedelta


class Departement(models.Model):
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)

    class Meta:
        verbose_name = "Département"
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Employe(AbstractUser):
    ROLE_CHOICES = [
        ('employe', 'Employé'),
        ('manager', 'Manager'),
        ('rh', 'Responsable RH'),
        ('dg', 'Directeur Général'),
        ('admin', 'Administrateur'),
    ]

    matricule = models.CharField(max_length=20, unique=True, null=True, blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    poste = models.CharField(max_length=100, blank=True)
    departement = models.ForeignKey(Departement, on_delete=models.SET_NULL, null=True, blank=True)
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordonnes')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employe')
    date_embauche = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Employé"
        verbose_name_plural = "Employés"

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    @property
    def initiales(self):
        f = self.first_name[0].upper() if self.first_name else ''
        l = self.last_name[0].upper() if self.last_name else ''
        return f"{f}{l}" or self.username[:2].upper()

    @property
    def is_manager_or_above(self):
        return self.role in ('manager', 'rh', 'dg', 'admin')

    @property
    def is_dg(self):
        return self.role == 'dg'

    def get_solde(self, type_conge):
        try:
            return self.soldes.get(type_conge=type_conge, annee=date.today().year)
        except SoldeConge.DoesNotExist:
            return None


class TypeConge(models.Model):
    CATEGORIE_CHOICES = [
        ('conge', 'Congé'),
        ('absence', 'Absence'),
    ]

    code = models.CharField(max_length=30, unique=True)
    libelle = models.CharField(max_length=100)
    categorie = models.CharField(max_length=10, choices=CATEGORIE_CHOICES, default='conge')
    couleur = models.CharField(max_length=7, default='#2196F3')
    icone = models.CharField(max_length=50, default='fa-calendar')
    jours_max = models.PositiveIntegerField(default=30)
    necessite_justificatif = models.BooleanField(default=False)
    decompte_weekend = models.BooleanField(default=False)
    actif = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Type de congé"
        verbose_name_plural = "Types de congé"
        ordering = ['categorie', 'libelle']

    def __str__(self):
        return self.libelle


class SoldeConge(models.Model):
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='soldes')
    type_conge = models.ForeignKey(TypeConge, on_delete=models.CASCADE)
    annee = models.PositiveIntegerField(default=2025)
    jours_acquis = models.DecimalField(max_digits=6, decimal_places=1, default=0, validators=[MinValueValidator(0)])
    jours_pris = models.DecimalField(max_digits=6, decimal_places=1, default=0, validators=[MinValueValidator(0)])
    jours_reportes = models.DecimalField(max_digits=6, decimal_places=1, default=0, validators=[MinValueValidator(0)])
    jours_supplementaires = models.DecimalField(max_digits=6, decimal_places=1, default=0, validators=[MinValueValidator(0)])

    class Meta:
        unique_together = ['employe', 'type_conge', 'annee']
        verbose_name = "Solde de congé"

    def __str__(self):
        return f"{self.employe} - {self.type_conge} ({self.annee})"

    @property
    def jours_restants(self):
        return self.jours_acquis + self.jours_reportes + self.jours_supplementaires - self.jours_pris

    @property
    def pourcentage_utilise(self):
        total = float(self.jours_acquis + self.jours_reportes + self.jours_supplementaires)
        if total == 0:
            return 0
        return int((float(self.jours_pris) / total) * 100)


def _annee_courante():
    return date.today().year


class CongeSupplementaire(models.Model):
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='conges_supplementaires')
    type_conge = models.ForeignKey(TypeConge, on_delete=models.CASCADE)
    annee = models.PositiveIntegerField(default=_annee_courante)
    nombre_jours = models.DecimalField(max_digits=5, decimal_places=1, validators=[MinValueValidator(0.5)])
    motif = models.CharField(max_length=255, blank=True)
    accorde_par = models.ForeignKey(
        Employe, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='conges_supplementaires_accordes'
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Congé supplémentaire"
        verbose_name_plural = "Congés supplémentaires"
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.employe.get_full_name()} +{self.nombre_jours}j ({self.type_conge})"


class DemandeConge(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('validee_manager', 'Validée par le manager - en attente du RH'),
        ('validee', 'Validée par le RH - en attente du DG'),
        ('approuve', 'Approuvé'),
        ('rejete', 'Rejeté'),
        ('annule', 'Annulé'),
    ]
    DEMI_JOURNEE_CHOICES = [
        ('matin', 'Matin'),
        ('apres_midi', 'Après-midi'),
    ]

    reference = models.CharField(max_length=20, unique=True, blank=True)
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='demandes')
    type_conge = models.ForeignKey(TypeConge, on_delete=models.CASCADE)
    interimaire = models.ForeignKey(
        Employe, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='remplacements'
    )
    date_debut = models.DateField()
    date_fin = models.DateField()
    demi_journee = models.BooleanField(default=False)
    periode_demi_journee = models.CharField(max_length=10, choices=DEMI_JOURNEE_CHOICES, blank=True)
    nombre_jours = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    motif = models.TextField(blank=True)
    justificatif = models.FileField(upload_to='justificatifs/', null=True, blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    date_soumission = models.DateTimeField(auto_now_add=True)
    valide_par = models.ForeignKey(
        Employe, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='demandes_validees',
        help_text="Manager ayant effectué la première validation."
    )
    date_validation = models.DateTimeField(null=True, blank=True)
    commentaire_validation = models.TextField(blank=True)
    valide_par_rh = models.ForeignKey(
        Employe, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='demandes_validees_rh',
        help_text="Responsable RH ayant validé la demande avant transmission au DG."
    )
    date_validation_rh = models.DateTimeField(null=True, blank=True)
    commentaire_validation_rh = models.TextField(blank=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    traite_par = models.ForeignKey(
        Employe, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='demandes_traitees',
        help_text="DG ayant approuvé/rejeté définitivement la demande, ou auteur du rejet."
    )
    commentaire_traitement = models.TextField(blank=True)

    class Meta:
        verbose_name = "Demande de congé"
        verbose_name_plural = "Demandes de congé"
        ordering = ['-date_soumission']

    def __str__(self):
        return f"{self.reference} - {self.employe.get_full_name()} ({self.statut})"

    def save(self, *args, **kwargs):
        if not self.reference:
            from django.utils import timezone
            annee = timezone.now().year
            count = DemandeConge.objects.filter(
                date_soumission__year=annee
            ).count() + 1
            self.reference = f"DEM-{annee}-{count:04d}"
        if not self.nombre_jours:
            self.nombre_jours = self.calculer_jours()
        super().save(*args, **kwargs)

    def calculer_jours(self):
        if self.demi_journee:
            return 0.5
        if not self.date_debut or not self.date_fin:
            return 0
        if self.type_conge and not self.type_conge.decompte_weekend:
            jours = 0
            current = self.date_debut
            while current <= self.date_fin:
                if current.weekday() < 5:
                    jours += 1
                current += timedelta(days=1)
            return jours
        return (self.date_fin - self.date_debut).days + 1

    @property
    def statut_css(self):
        return {
            'en_attente': 'warning',
            'validee_manager': 'primary',
            'validee': 'info',
            'approuve': 'success',
            'rejete': 'danger',
            'annule': 'secondary',
        }.get(self.statut, 'secondary')

    @property
    def statut_label(self):
        return dict(self.STATUT_CHOICES).get(self.statut, '')


class Recrutement(models.Model):
    TYPE_CONTRAT_CHOICES = [
        ('cdi', 'CDI'),
        ('cdd', 'CDD'),
        ('stage', 'Stage'),
        ('consultant', 'Consultant'),
    ]
    SOURCE_CHOICES = [
        ('candidature_spontanee', 'Candidature spontanée'),
        ('cooptation', 'Cooptation'),
        ('cabinet_recrutement', 'Cabinet de recrutement'),
        ('site_emploi', "Site d'emploi"),
        ('reseau_social', 'Réseau social'),
        ('autre', 'Autre'),
    ]
    STATUT_CHOICES = [
        ('essai', "Période d'essai"),
        ('confirme', 'Confirmé'),
        ('rompu', "Rompu pendant la période d'essai"),
    ]

    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='recrutements')
    type_contrat = models.CharField(max_length=20, choices=TYPE_CONTRAT_CHOICES, default='cdi')
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='essai')
    date_embauche = models.DateField(default=date.today)
    periode_essai_fin = models.DateField(null=True, blank=True)
    contrat_signe = models.BooleanField(default=False)
    visite_medicale_effectuee = models.BooleanField(default=False)
    dossier_complet = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    responsable_rh = models.ForeignKey(
        Employe, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='recrutements_geres'
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Recrutement"
        verbose_name_plural = "Recrutements"
        ordering = ['-date_embauche']

    def __str__(self):
        return f"{self.employe.get_full_name()} ({self.get_statut_display()})"

    @property
    def statut_css(self):
        return {
            'essai': 'warning',
            'confirme': 'success',
            'rompu': 'danger',
        }.get(self.statut, 'secondary')


class Depart(models.Model):
    TYPE_DEPART_CHOICES = [
        ('demission', 'Démission'),
        ('licenciement', 'Licenciement'),
        ('fin_contrat', 'Fin de contrat'),
        ('retraite', 'Retraite'),
        ('rupture_conventionnelle', 'Rupture conventionnelle'),
        ('deces', 'Décès'),
        ('autre', 'Autre'),
    ]
    STATUT_CHOICES = [
        ('planifie', 'Planifié'),
        ('en_cours', 'En cours'),
        ('finalise', 'Finalisé'),
    ]

    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='departs')
    type_depart = models.CharField(max_length=30, choices=TYPE_DEPART_CHOICES, default='demission')
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='planifie')
    date_annonce = models.DateField(default=date.today)
    date_depart = models.DateField(help_text="Dernier jour de travail effectif")
    preavis_jours = models.PositiveIntegerField(null=True, blank=True)
    motif = models.TextField(blank=True)
    entretien_sortie_effectue = models.BooleanField(default=False)
    solde_tout_compte_effectue = models.BooleanField(default=False)
    materiel_restitue = models.BooleanField(default=False)
    commentaire = models.TextField(blank=True)
    traite_par = models.ForeignKey(
        Employe, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='departs_traites'
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Départ"
        verbose_name_plural = "Départs"
        ordering = ['-date_depart']

    def __str__(self):
        return f"{self.employe.get_full_name()} - {self.get_type_depart_display()}"

    @property
    def statut_css(self):
        return {
            'planifie': 'info',
            'en_cours': 'warning',
            'finalise': 'secondary',
        }.get(self.statut, 'secondary')


class Notification(models.Model):
    destinataire = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='notifications')
    titre = models.CharField(max_length=200)
    message = models.TextField()
    lien = models.CharField(max_length=200, blank=True)
    lue = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.destinataire} - {self.titre}"


class HistoriqueModification(models.Model):
    TYPE_CHOICES = [
        ('demande_modifiee', 'Modification de demande de congé'),
        ('conge_supplementaire', 'Congé supplémentaire accordé'),
        ('solde_modifie', 'Modification de solde'),
    ]

    type_action = models.CharField(max_length=30, choices=TYPE_CHOICES)
    auteur = models.ForeignKey(
        Employe, on_delete=models.SET_NULL, null=True,
        related_name='modifications_effectuees'
    )
    employe_concerne = models.ForeignKey(
        Employe, on_delete=models.CASCADE, related_name='historique_modifications'
    )
    demande = models.ForeignKey(
        DemandeConge, on_delete=models.SET_NULL, null=True, blank=True, related_name='historique'
    )
    description = models.TextField()
    date_action = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historique de modification"
        verbose_name_plural = "Historique des modifications"
        ordering = ['-date_action']

    def __str__(self):
        return f"{self.get_type_action_display()} - {self.employe_concerne} ({self.date_action:%d/%m/%Y})"
