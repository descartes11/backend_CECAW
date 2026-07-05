from datetime import date
import uuid

from django.db import models
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin

class UserManager(BaseUserManager):
    def create_user(self, code, password=None, **extra_fields):
        if not code:
            raise ValueError("Le code est obligatoire")

        user = self.model(code=code, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, code, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(code, password, **extra_fields)

class User(AbstractUser,PermissionsMixin):
    
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    firstname = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True, null=True)
    password = models.CharField(max_length=255)
    dik = models.BooleanField(default=False)
    remember_token = models.CharField(max_length=255, blank=True, null=True)
    role_name = models.CharField(max_length=100, blank=True, null=True)
    agence_code = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'users'
        ordering = ['id']
        
    USERNAME_FIELD = 'code'   
    REQUIRED_FIELDS = []
    objects = UserManager()

    def __str__(self):
        return f"{self.code} - {self.firstname} {self.name}"
    
    
    def save(self, *args, **kwargs):
    # Hash uniquement si le mot de passe est en clair
        if self.password and not self.password.startswith(('pbkdf2_', 'bcrypt', '$2b$', '$2y$', 'argon2')):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    """def save(self, *args, **kwargs):
        # Hash the password only if it's not already hashed
        if self.password and not self.password.startswith('$2y$') and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)"""
        
class Client(models.Model):
    """
    Modèle Client basé sur la structure JSON fournie et le diagramme de classes.
    
    Champs notables :
    - old_code       : ancien code du client (migration depuis l'ancien système)
    - pid            : numéro de pièce d'identité
    - type_pid       : type de pièce (CNI, Passeport, etc.)
    - delivered_at   : date de délivrance de la pièce
    - civility       : civilité (1=M, 2=Mme, etc.)
    - active/connect : statut d'activité et de connexion
    - departure_at   : date de départ (client parti/inactif)
    - user_code      : code de l'utilisateur qui a créé le client
    - sale_agent_code: code de l'agent commercial responsable
    - working_date_day: jour ouvrable du client
    """

    GENDER_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
        ('A', 'Autre'),
    ]

    # --- Identification ---
    code = models.CharField(max_length=100, unique=True)
    old_code = models.CharField(max_length=100, blank=True, null=True)

    # --- Identité ---
    name = models.CharField(max_length=150)
    firstname = models.CharField(max_length=150, blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    civility = models.CharField(max_length=10, blank=True, null=True)  # ex: "1", "2"
    born_at = models.DateField(blank=True, null=True)
    born_in = models.CharField(max_length=150, blank=True, null=True)

    # --- Filiation ---
    father_name = models.CharField(max_length=150, blank=True, null=True)
    father_firstname = models.CharField(max_length=150, blank=True, null=True)
    mother_name = models.CharField(max_length=150, blank=True, null=True)
    mother_firstname = models.CharField(max_length=150, blank=True, null=True)

    # --- Pièce d'identité ---
    pid = models.CharField(max_length=100, blank=True, null=True)
    type_pid = models.CharField(max_length=50, blank=True, null=True)
    delivered_at = models.DateField(blank=True, null=True)

    # --- Activité & localisation ---
    activity = models.CharField(max_length=150, blank=True, null=True)
    place = models.CharField(max_length=150, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)

    # --- Statuts ---
    active = models.BooleanField(default=True)
    connect = models.BooleanField(default=False)
    departure_at = models.DateField(blank=True, null=True)

    # --- Rattachement ---
    user_code = models.CharField(max_length=100, blank=True, null=True)      # Utilisateur créateur
    agence_code = models.CharField(max_length=50, blank=True, null=True)
    sale_agent_code = models.CharField(max_length=100, blank=True, null=True)

    # --- Divers ---
    working_date_day = models.CharField(max_length=20, blank=True, null=True)

    # --- Horodatage ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'clients'
        ordering = ['id']

    def __str__(self):
        return f"{self.code} - {self.firstname} {self.name}"


class Commerciaux(models.Model):
    """
    Modèle Commerciaux (Agents commerciaux) basé sur le JSON fourni et le diagramme de classes.

    Relations avec les autres modèles :
    - user_code      → FK vers User.code       (l'utilisateur qui gère ce commercial)
    - agence_code    → FK vers Agence.code      (agence de rattachement)
    - sale_agent_id  → FK vers Commerciaux.id   (agent superviseur, auto-référence)

    Comptes CB (Core Banking) :
    - cb_commitment_acc      : Compte d'engagement
    - cb_transaction_acc     : Compte d'opération
    - cb_excess_acc          : Compte d'excédent
    - cb_deficit_acc         : Compte manquant/déficit
    - cb_salary_acc          : Compte salaire (optionnel)
    Chaque compte a un champ "_name" correspondant pour le libellé.
    """

    # --- Identification ---
    code = models.CharField(max_length=100, unique=True)
    old_code = models.CharField(max_length=100, blank=True, null=True)

    # --- Identité ---
    name = models.CharField(max_length=150)
    firstname = models.CharField(max_length=150, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    cni = models.CharField(max_length=100, blank=True, null=True)  # Numéro CNI

    # --- Statuts ---
    active = models.BooleanField(default=True)
    connect = models.BooleanField(default=False)

    # --- Rattachement ---
    agence_code = models.CharField(max_length=50, blank=True, null=True)
    user_code = models.CharField(max_length=100, blank=True, null=True)   # Lié à User.code
    sale_agent_id = models.IntegerField(blank=True, null=True)             # Superviseur (auto-référence)
    code_collect = models.CharField(max_length=100, blank=True, null=True)

    # --- Comptes Core Banking ---
    cb_commitment_acc = models.CharField(max_length=50, blank=True, null=True)
    cb_commitment_acc_name = models.CharField(max_length=255, blank=True, null=True)

    cb_transaction_acc = models.CharField(max_length=50, blank=True, null=True)
    cb_transaction_acc_name = models.CharField(max_length=255, blank=True, null=True)

    cb_excess_acc = models.CharField(max_length=50, blank=True, null=True)
    cb_excess_acc_name = models.CharField(max_length=255, blank=True, null=True)

    cb_deficit_acc = models.CharField(max_length=50, blank=True, null=True)
    cb_deficit_acc_name = models.CharField(max_length=255, blank=True, null=True)

    cb_salary_acc = models.CharField(max_length=50, blank=True, null=True)
    cb_salary_acc_name = models.CharField(max_length=255, blank=True, null=True)

    # --- Horodatage ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'commerciaux'
        ordering = ['id']
        verbose_name = 'Commercial'
        verbose_name_plural = 'Commerciaux'

    def __str__(self):
        return f"{self.code} - {self.firstname} {self.name}"
    
class Prets(models.Model):
    """
    Modèle Prêts basé sur le JSON fourni et le diagramme de classes.

    Relations avec les autres modèles déjà créés :
    - customer_code      → FK vers Client.code
    - agence_code        → FK vers Agence.code
    - user_code          → FK vers User.code
    - manager_code       → FK vers User.code (responsable du prêt)
    - product_loan_code  → FK vers Produits.code
    - product_insurance_code → FK vers Produits.code (assurance)

    Statuts possibles :
        pending   → En attente
        active    → En cours
        paid      → Remboursé
        cancelled → Annulé
        overdue   → En retard
    """

    STATUS_CHOICES = [
        ('pending',   'En attente'),
        ('active',    'En cours'),
        ('paid',      'Remboursé'),
        ('cancelled', 'Annulé'),
        ('overdue',   'En retard'),
    ]

    # --- Identification ---
    reference = models.CharField(max_length=100, unique=True)

    # --- Montants ---
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    number_of_due_dates = models.IntegerField(default=1)  # Nombre d'échéances

    # --- Statut ---
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    status_date = models.DateField(blank=True, null=True)
    backdated = models.BooleanField(default=False)

    # --- Dates clés ---
    effective_date  = models.DateField(blank=True, null=True)   # Date de mise en vigueur
    first_due_date  = models.DateField(blank=True, null=True)   # Première échéance
    last_due_date   = models.DateField(blank=True, null=True)   # Dernière échéance
    working_date_day = models.DateField(blank=True, null=True)  # Jour ouvrable

    # --- Compte de remboursement ---
    refund_account = models.CharField(max_length=100, blank=True, null=True)

    # --- Périodicité ---
    periodicity_name = models.CharField(max_length=50, blank=True, null=True)
    # ex: MENSUELLE, BIMESTRIELLE, TRIMESTRIELLE, SEMESTRIELLE, ANNUELLE

    # --- Rattachement produits ---
    product_loan_code      = models.CharField(max_length=100, blank=True, null=True)  # Lié à Produits.code
    product_insurance_code = models.CharField(max_length=100, blank=True, null=True)  # Lié à Produits.code

    # --- Rattachement acteurs ---
    customer_code = models.CharField(max_length=100, blank=True, null=True)  # Lié à Client.code
    agence_code   = models.CharField(max_length=50,  blank=True, null=True)
    manager_code  = models.CharField(max_length=100, blank=True, null=True)  # Lié à User.code
    user_code     = models.CharField(max_length=100, blank=True, null=True)  # Lié à User.code

    # --- Horodatage ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'prets'
        ordering = ['-created_at']
        verbose_name = 'Prêt'
        verbose_name_plural = 'Prêts'

    def __str__(self):
        return f"{self.reference} - {self.status} - {self.amount}"
    
    def save(self, *args, **kwargs):
        # Génère la référence si elle est vide ou nulle
        today = date.today()
        
        if not self.reference:
        
            # Format : PRT-C03-042026-XXXX  (agence + mois/année + 4 chiffres aléatoires)
        
            mois_annee = today.strftime('%m%Y')
            unique_part = str(uuid.uuid4().int)[:4]
            self.reference = f"PRT-{mois_annee}-{unique_part}"
            
            # Garantir l'unicité en cas de collision
            while Prets.objects.filter(reference=self.reference).exists():
                unique_part = str(uuid.uuid4().int)[:4]
                self.reference = f"PRT-{mois_annee}-{unique_part}"
                
        if not self.effective_date:
           self.effective_date = today
           
        if self.effective_date and self.number_of_due_dates:
            from dateutil.relativedelta import relativedelta
            self.first_due_date = self.effective_date + relativedelta(months=1)
            self.last_due_date  = self.effective_date + relativedelta(months=self.number_of_due_dates)
        
        if not self.status_date:
            self.status_date = today
        if not self.working_date_day:
            self.working_date_day = today


        
        super().save(*args, **kwargs)




class Compte(models.Model):
    """
    Modèle Compte basé sur le JSON fourni et le diagramme de classes.

    Relations avec les autres modèles déjà créés :
    - customer_code      → FK vers Client.code
    - sale_agent_code    → FK vers Commerciaux.code
    - agence_code        → FK vers Agence.code
    - user_code          → FK vers User.code
    - product_loan_code  → FK vers Produits.code
    - insurer_code       → FK vers Assureur/Produits.code

    Types de comptes :
        Un compte peut être :
        - Un compte caisse agence   (customer_code vide)
        - Un compte client          (customer_code renseigné)
        - Un compte agent           (sale_agent_code renseigné)

    Balance :
        - balance         : solde actuel (peut être négatif)
        - standby_balance : solde en attente/réservé
        - can_take_loans  : indique si le compte peut souscrire des prêts
    """

    # --- Identification ---
    number = models.CharField(max_length=100, unique=True)  # ex: 571000-C03-000000-00
    name   = models.CharField(max_length=255)               # Libellé du compte

    # --- Statut ---
    active        = models.BooleanField(default=True)
    can_take_loans = models.BooleanField(default=False)

    # --- Soldes ---
    balance         = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    standby_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    # --- Dates opérationnelles ---
    working_date_day = models.DateField(blank=True, null=True)  # Jour ouvrable
    max_date_op      = models.DateField(blank=True, null=True)  # Date max d'opération

    # --- Rattachement acteurs ---
    customer_code   = models.CharField(max_length=100, blank=True, null=True)  # → Client.code
    sale_agent_code = models.CharField(max_length=100, blank=True, null=True)  # → Commerciaux.code
    insurer_code    = models.CharField(max_length=100, blank=True, null=True)  # → Assureur
    agence_code     = models.CharField(max_length=50,  blank=True, null=True)  # → Agence
    user_code       = models.CharField(max_length=100, blank=True, null=True)  # → User.code

    # --- Rattachement produit ---
    product_loan_code = models.CharField(max_length=100, blank=True, null=True)  # → Produits.code

    # --- Horodatage ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table  = 'comptes'
        ordering  = ['-created_at']
        verbose_name        = 'Compte'
        verbose_name_plural = 'Comptes'

    def __str__(self):
        return f"{self.number} - {self.name} | Solde: {self.balance}"

    @property
    def is_negative(self):
        """Retourne True si le solde est négatif."""
        return self.balance < 0

    @property
    def available_balance(self):
        """Solde disponible = balance - standby_balance."""
        return self.balance - self.standby_balance



class Produits(models.Model):
    """
    Modèle Produits basé sur le JSON fourni et le diagramme de classes.

    Relations avec les autres modèles déjà créés :
    - user_code  → FK vers User.code (utilisateur créateur)

    Ce modèle est référencé par :
    - Prets.product_loan_code      → Produits.code (produit de prêt)
    - Prets.product_insurance_code → Produits.code (produit assurance)
    - Compte.product_loan_code     → Produits.code

    Types de produits (selon le code) :
        PCO  → Produit Collecte Ordinaire
        PCR  → Produit Crédit
        PASR → Produit Assurance
    """

    # --- Identification ---
    code = models.CharField(max_length=100, unique=True)  # ex: PCO-01, PCR-01, PASR-01
    name = models.CharField(max_length=255)               # ex: COLLECTE ORDINAIRE

    # --- Paramètres financiers ---
    duration        = models.IntegerField(default=1)                              # Durée (en mois)
    commission_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Taux de commission (%)
    pay_rate        = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Taux de paiement (%)

    # --- Statuts ---
    is_active          = models.BooleanField(default=True)   # Produit actif
    is_paid            = models.BooleanField(default=False)  # Produit payé
    is_commission_paid = models.BooleanField(default=True)   # Commission payée

    # --- Rattachement ---
    user_code = models.CharField(max_length=100, blank=True, null=True)  # → User.code

    # --- Horodatage ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table            = 'produits'
        ordering            = ['code']
        verbose_name        = 'Produit'
        verbose_name_plural = 'Produits'

    def __str__(self):
        return f"{self.code} - {self.name}"
    
    

class Recus(models.Model):
    """
    Modèle Reçus basé sur le JSON fourni et le diagramme de classes.

    Relations avec les autres modèles déjà créés :
    - sale_agent_code → FK vers Commerciaux.code
    - agence_code     → FK vers Agence.code
    - user_code       → FK vers User.code
    - cancel_by       → FK vers User.code (utilisateur ayant annulé)

    Un reçu représente un document de collecte/transaction émis par un agent.

    Statuts :
        - is_use = True  → Reçu utilisé/validé
        - is_use = False → Reçu annulé ou non utilisé
        - cancel_by renseigné → Reçu annulé par cet utilisateur
    """

    # --- Identification ---
    number = models.CharField(max_length=100, unique=True)  # ex: 4831165A

    # --- Statut ---
    is_use = models.BooleanField(default=True)  # True = utilisé, False = annulé

    # --- Annulation ---
    cancel_by = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )  # → User.code de celui qui a annulé

    # --- Détails ---
    detail = models.TextField(blank=True, null=True)  # Description libre

    # --- Dates opérationnelles ---
    working_date_day = models.DateField(blank=True, null=True)

    # --- Rattachement ---
    agence_code     = models.CharField(max_length=50,  blank=True, null=True)  # → Agence
    sale_agent_code = models.CharField(max_length=100, blank=True, null=True)  # → Commerciaux.code
    user_code       = models.CharField(max_length=100, blank=True, null=True)  # → User.code

    # --- Horodatage ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table            = 'recus'
        ordering            = ['-created_at']
        verbose_name        = 'Reçu'
        verbose_name_plural = 'Reçus'

    def __str__(self):
        return f"{self.number} - {'Utilisé' if self.is_use else 'Annulé'}"

    @property
    def is_cancelled(self):
        """Retourne True si le reçu a été annulé."""
        return bool(self.cancel_by)



# ==============================================================================
# MODÈLE TRANSACTION
# ==============================================================================
# Représente une ligne de collecte saisie par la caissière pour le compte
# d'un agent commercial (Commerciaux).
#
# Relations avec les modèles existants (via codes métier, sans FK Django) :
#   sale_agent_code → Commerciaux.code
#   customer_code   → Client.code
#   compte_number   → Compte.number
#   recu_number     → Recus.number
#   product_code    → Produits.code
#   agence_code     → même valeur que l'agent
#   user_code       → User.code  (caissière qui saisit)
#   validated_by    → User.code  (caissière qui valide la tournée)
# ==============================================================================


class Transaction(models.Model):
    """
    Cycle de vie :
        pending   → saisie en cours (tournée non encore validée)
        validated → tournée clôturée via "Valider la tournée"
        cancelled → supprimée par la caissière avant validation
    """

    STATUS_CHOICES = [
        ('pending',   'En attente'),
        ('validated', 'Validé'),
        ('cancelled', 'Annulé'),
    ]

    # --- Référence unique auto-générée ---
    reference = models.CharField(max_length=100,unique=True, blank=True)

    # --- Champs du formulaire frontend ---
    code = models.CharField( max_length=100)
    customer_name = models.CharField( max_length=255, blank=True, null=True)
    product_code = models.CharField(max_length=100, blank=True, null=True)
    product_name = models.CharField(max_length=255,blank=True,null=True)
    compte_number = models.CharField(max_length=100, blank=True, null=True)
    recu_number = models.CharField(max_length=100,blank=True,null=True)
    amount = models.DecimalField(max_digits=15,decimal_places=2)

    # --- Statut ---
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # --- Contexte (rempli automatiquement côté backend) ---
    sale_agent_code = models.CharField( max_length=100)
    customer_code = models.CharField(max_length=100, blank=True, null=True)
    agence_code = models.CharField(max_length=50, blank=True,null=True)
    user_code = models.CharField( max_length=100, blank=True, null=True)
    validated_by = models.CharField(max_length=100, blank=True, null=True)

    # --- Dates ---
    working_date_day = models.DateField(blank=True,null=True)
    validated_at = models.DateTimeField(blank=True,null=True)

    # --- Horodatage standard ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table            = 'transactions'
        ordering            = ['-created_at']
        verbose_name        = 'Transaction'
        verbose_name_plural = 'Transactions'
        indexes = [
            # Requête la plus fréquente : tableau du jour pour un agent
            models.Index(
                fields=['sale_agent_code', 'working_date_day'],
                name='idx_trn_agent_date'
            ),
            # Vue superviseur : toutes les transactions d'une agence par date
            models.Index(
                fields=['agence_code', 'working_date_day'],
                name='idx_trn_agence_date'
            ),
        ]

    def __str__(self):
        return f"{self.reference} | {self.sale_agent_code} | {self.amount} FCFA | {self.status}"

    def save(self, *args, **kwargs):
        from datetime import date

        # Génère la référence si absente
        if not self.reference:
            mois_annee     = date.today().strftime('%m%Y')
            suffix         = uuid.uuid4().hex[:6].upper()
            self.reference = f"TRN-{mois_annee}-{suffix}"
            while Transaction.objects.filter(reference=self.reference).exists():
                suffix         = uuid.uuid4().hex[:6].upper()
                self.reference = f"TRN-{mois_annee}-{suffix}"

        # Date du jour par défaut
        if not self.working_date_day:
            self.working_date_day = date.today()

        super().save(*args, **kwargs)


class Operation(models.Model):

    TYPE_CHOICES = [
        ('retrait',   'Retrait'),
        ('versement', 'Versement'),
    ]

    reference      = models.CharField(max_length=100, unique=True, blank=True)
    type_operation = models.CharField(max_length=20, choices=TYPE_CHOICES)

    customer_code  = models.CharField(max_length=100, blank=True, null=True)
    customer_name  = models.CharField(max_length=255, blank=True, null=True)
    compte_number  = models.CharField(max_length=100, blank=True, null=True)
    recu_number    = models.CharField(max_length=100, blank=True, null=True)

    amount         = models.DecimalField(max_digits=15, decimal_places=2)

    agence_code    = models.CharField(max_length=50,  blank=True, null=True)
    user_code      = models.CharField(max_length=100, blank=True, null=True)

    working_date_day = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table            = 'operations'
        ordering            = ['-created_at']
        verbose_name        = 'Opération'
        verbose_name_plural = 'Opérations'
        indexes = [
            models.Index(fields=['type_operation', 'working_date_day'], name='idx_op_type_date'),
            models.Index(fields=['agence_code', 'working_date_day'],    name='idx_op_agence_date'),
            models.Index(fields=['customer_code'],                       name='idx_op_customer'),
        ]

    def __str__(self):
        return f"{self.reference} | {self.type_operation.upper()} | {self.amount} FCFA"

    def save(self, *args, **kwargs):
        from datetime import date

        if not self.reference:
            prefix         = 'RTR' if self.type_operation == 'retrait' else 'VRS'
            mois_annee     = date.today().strftime('%m%Y')
            suffix         = uuid.uuid4().hex[:6].upper()
            self.reference = f"{prefix}-{mois_annee}-{suffix}"
            while Operation.objects.filter(reference=self.reference).exists():
                suffix         = uuid.uuid4().hex[:6].upper()
                self.reference = f"{prefix}-{mois_annee}-{suffix}"

        if not self.working_date_day:
            self.working_date_day = date.today()

        super().save(*args, **kwargs)