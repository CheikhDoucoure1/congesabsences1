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
        return self.role in ('manager', 'rh', 'admin')

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

    class Meta:
        unique_together = ['employe', 'type_conge', 'annee']
        verbose_name = "Solde de congé"

    def __str__(self):
        return f"{self.employe} - {self.type_conge} ({self.annee})"

    @property
    def jours_restants(self):
        return self.jours_acquis + self.jours_reportes - self.jours_pris

    @property
    def pourcentage_utilise(self):
        total = float(self.jours_acquis + self.jours_reportes)
        if total == 0:
            return 0
        return int((float(self.jours_pris) / total) * 100)


class DemandeConge(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
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
    date_traitement = models.DateTimeField(null=True, blank=True)
    traite_par = models.ForeignKey(
        Employe, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='demandes_traitees'
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
            'approuve': 'success',
            'rejete': 'danger',
            'annule': 'secondary',
        }.get(self.statut, 'secondary')

    @property
    def statut_label(self):
        return dict(self.STATUT_CHOICES).get(self.statut, '')


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
