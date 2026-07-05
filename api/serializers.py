from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import User , Client ,Commerciaux , Prets, Compte, Produits , Recus , Operation


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le modèle User.
    """
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [ 'id','code','name','firstname','phone','password','dik','remember_token','role_name',
                 'agence_code','created_at','updated_at','deleted_at',
        ]
        
        
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True},
            'remember_token': {'write_only': True},
            'username':       {'required': False},
        }

    def create(self, validated_data):
        
        if 'code' in validated_data and not validated_data.get('username'):
            validated_data['username'] = validated_data['code']
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)
  
    def update(self, instance, validated_data):
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        return super().update(instance, validated_data)
    


class UserListSerializer(serializers.ModelSerializer):
    """
    Serializer allégé pour les listes (sans données sensibles).
    """
    class Meta:
        model = User
        fields = [
            'id',
            'code',
            'name',
            'firstname',
            'phone',
            'dik',
            'role_name',
            'agence_code',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClientSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le modèle Client.
    Utilisé pour les opérations CREATE, UPDATE et GET détail.
    """

    class Meta:
        model = Client
        fields = ['id','code','old_code','name','firstname','gender','civility','born_at','born_in',
            'father_name','father_firstname','mother_name','mother_firstname','pid','type_pid','delivered_at',
            'activity','place','address','phone','password','active','connect','departure_at','user_code','agence_code',
            'sale_agent_code','working_date_day','created_at','updated_at','deleted_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True},  # Ne jamais retourner le mot de passe
        }


class ClientListSerializer(serializers.ModelSerializer):
    """
    Serializer allégé pour les listes de clients.
    Retourne uniquement les champs essentiels pour éviter des réponses trop lourdes.
    """

    class Meta:
        model = Client
        fields = [ 'id', 'code','old_code','name','firstname','gender','phone','active','agence_code',
            'sale_agent_code','created_at',
        ]
        read_only_fields = ['id', 'created_at']

class CommerciauxSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le modèle Commerciaux.
    Utilisé pour CREATE, UPDATE et GET détail.
    Inclut tous les comptes CB et les informations complètes.
    """

    class Meta:
        model = Commerciaux
        fields = ['id','code','old_code','name','firstname','phone','cni','active','connect','agence_code','user_code',
                 'sale_agent_id','code_collect','cb_commitment_acc','cb_commitment_acc_name','cb_transaction_acc',
                 'cb_transaction_acc_name','cb_excess_acc','cb_excess_acc_name','cb_deficit_acc','cb_deficit_acc_name',
                 'cb_salary_acc','cb_salary_acc_name','created_at','updated_at','deleted_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CommerciauxListSerializer(serializers.ModelSerializer):
    """
    Serializer allégé pour les listes.
    Sans les comptes CB pour alléger les réponses.
    """

    class Meta:
        model = Commerciaux
        fields = ['id','code','old_code','name','firstname','phone','cni',
                  'active','connect','agence_code','user_code','sale_agent_id','created_at',
        ]
        read_only_fields = ['id', 'created_at']


class PretsSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le modèle Prets.
    Utilisé pour CREATE, UPDATE et GET détail.
    """

    class Meta:
        model = Prets
        fields = ['id','reference','amount','number_of_due_dates','status','status_date','backdated','effective_date',
                  'first_due_date','last_due_date','working_date_day','refund_account','periodicity_name','product_loan_code',
                  'product_insurance_code','customer_code','agence_code','manager_code','user_code','created_at','updated_at',
                  'deleted_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'reference':          {'required': False, 'allow_blank': True, 'allow_null': True},
            'status':             {'required': False, 'allow_blank': True},
            'status_date':        {'required': False, 'allow_null': True},
            'backdated':          {'required': False, 'allow_null': True},
            'effective_date':     {'required': False, 'allow_null': True},
            'first_due_date':     {'required': False, 'allow_null': True},
            'last_due_date':      {'required': False, 'allow_null': True},
            'working_date_day':   {'required': False, 'allow_null': True},
            'refund_account':     {'required': False, 'allow_blank': True, 'allow_null': True},
            'product_insurance_code': {'required': False, 'allow_blank': True, 'allow_null': True},
            'agence_code':        {'required': False, 'allow_blank': True},
            'user_code':          {'required': False, 'allow_blank': True},
        }

    def validate_amount(self, value):
        """Le montant doit être strictement positif."""
        if value <= 0:
            raise serializers.ValidationError("Le montant du prêt doit être supérieur à 0.")
        return value

    def validate_number_of_due_dates(self, value):
        """Le nombre d'échéances doit être au moins 1."""
        if value < 1:
            raise serializers.ValidationError("Le nombre d'échéances doit être au moins 1.")
        return value

    def validate(self, data):
        """Vérifie que first_due_date est avant last_due_date."""
        first = data.get('first_due_date')
        last  = data.get('last_due_date')
        if first and last and first > last:
            raise serializers.ValidationError({
                'first_due_date': "La première échéance ne peut pas être après la dernière."
            })
        return data


class PretsListSerializer(serializers.ModelSerializer):
    """
    Serializer allégé pour les listes de prêts.
    Retourne les champs essentiels uniquement.
    """

    class Meta:
        model = Prets
        fields = ['id','reference','amount','number_of_due_dates','status','effective_date','first_due_date',
                  'last_due_date','periodicity_name','customer_code','agence_code','manager_code','created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CompteSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le modèle Compte.
    Utilisé pour CREATE, UPDATE et GET détail.
    Inclut les propriétés calculées is_negative et available_balance.
    """

    # Champs calculés (read-only)
    is_negative       = serializers.BooleanField(read_only=True)
    available_balance = serializers.DecimalField(
        max_digits=20, decimal_places=2, read_only=True
    )

    class Meta:
        model = Compte
        fields = ['id','number','name','active','can_take_loans','balance','standby_balance','is_negative','available_balance',  
                  'working_date_day','max_date_op','customer_code','sale_agent_code','insurer_code','agence_code','user_code',
                   'product_loan_code','created_at','updated_at','deleted_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_negative', 'available_balance']


class CompteListSerializer(serializers.ModelSerializer):
    """
    Serializer allégé pour les listes de comptes.
    Sans les champs secondaires pour alléger les réponses.
    """

    is_negative       = serializers.BooleanField(read_only=True)
    available_balance = serializers.DecimalField(
        max_digits=20, decimal_places=2, read_only=True
    )

    class Meta:
        model = Compte
        fields = ['id','number','name','active','can_take_loans','balance','standby_balance','is_negative','available_balance',
                  'agence_code','customer_code','sale_agent_code','created_at',
        ]
        read_only_fields = ['id', 'created_at', 'is_negative', 'available_balance']


class CompteBalanceSerializer(serializers.Serializer):
    """
    Serializer dédié pour la mise à jour du solde uniquement.
    Utilisé par l'endpoint PATCH /api/comptes/<pk>/update-balance/
    """
    balance         = serializers.DecimalField(max_digits=20, decimal_places=2, required=True)
    standby_balance = serializers.DecimalField(max_digits=20, decimal_places=2, required=False)
    
    
class ProduitsSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le modèle Produits.
    Utilisé pour CREATE, UPDATE et GET détail.
    """

    class Meta:
        model = Produits
        fields = ['id','code','name','duration','commission_rate','pay_rate','is_active','is_paid','is_commission_paid',
                  'user_code','created_at','updated_at','deleted_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_duration(self, value):
        """La durée doit être au moins 1."""
        if value < 1:
            raise serializers.ValidationError("La durée doit être au moins 1 mois.")
        return value

    def validate_commission_rate(self, value):
        """Le taux de commission doit être entre 0 et 100."""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Le taux de commission doit être entre 0 et 100.")
        return value

    def validate_pay_rate(self, value):
        """Le taux de paiement doit être entre 0 et 100."""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Le taux de paiement doit être entre 0 et 100.")
        return value


class ProduitsListSerializer(serializers.ModelSerializer):
    """
    Serializer allégé pour les listes de produits.
    """

    class Meta:
        model = Produits
        fields = ['id','code','name','duration','commission_rate','pay_rate','is_active','is_paid','is_commission_paid',
                  'user_code','created_at',
        ]
        read_only_fields = ['id', 'created_at']


class RecusSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour le modèle Recus.
    Utilisé pour CREATE, UPDATE et GET détail.
    Inclut le champ calculé is_cancelled.
    """

    is_cancelled = serializers.BooleanField(read_only=True)

    class Meta:
        model = Recus
        fields = [
            'id',
            'number',
            'is_use',
            'is_cancelled',     # calculé : True si cancel_by est renseigné
            'cancel_by',
            'detail',
            'working_date_day',
            'agence_code',
            'sale_agent_code',
            'user_code',
            'created_at',
            'updated_at',
            'deleted_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_cancelled']

    def validate(self, data):
        """
        Si cancel_by est renseigné, is_use doit être False.
        On ne peut pas annuler un reçu et le marquer comme utilisé en même temps.
        """
        cancel_by = data.get('cancel_by', getattr(self.instance, 'cancel_by', None))
        is_use    = data.get('is_use',    getattr(self.instance, 'is_use',    True))

        if cancel_by and is_use:
            raise serializers.ValidationError({
                'is_use': "Un reçu annulé (cancel_by renseigné) ne peut pas être marqué comme utilisé."
            })
        return data


class RecusListSerializer(serializers.ModelSerializer):
    """
    Serializer allégé pour les listes de reçus.
    """

    is_cancelled = serializers.BooleanField(read_only=True)

    class Meta:
        model = Recus
        fields = [
            'id',
            'number',
            'is_use',
            'is_cancelled',
            'cancel_by',
            'agence_code',
            'sale_agent_code',
            'user_code',
            'working_date_day',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'is_cancelled']


class RecusCancelSerializer(serializers.Serializer):
    """
    Serializer dédié pour l'annulation d'un reçu.
    Utilisé par PATCH /api/recus/<pk>/cancel/
    """
    cancel_by = serializers.CharField(max_length=100, required=True)
    detail    = serializers.CharField(required=False, allow_blank=True)

from rest_framework import serializers
from .models import Transaction


# ==============================================================================
# SERIALIZER COMPLET — CREATE / UPDATE / GET détail
# ==============================================================================

class TransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model  = Transaction
        fields = [
            'id',
            'reference',
            'code',
            'customer_name',
            'product_code',
            'product_name',
            'compte_number',
            'recu_number',
            'amount',
            'status',
            'sale_agent_code',
            'customer_code',
            'agence_code',
            'user_code',
            'validated_by',
            'working_date_day',
            'validated_at',
            # Horodatage
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'reference', 'created_at', 'updated_at']
        extra_kwargs = {
            'status':            {'required': False},
            'customer_code':     {'required': False, 'allow_null': True, 'allow_blank': True},
            'agence_code':       {'required': False, 'allow_null': True, 'allow_blank': True},
            'user_code':         {'required': False, 'allow_null': True, 'allow_blank': True},
            'validated_by':      {'required': False, 'allow_null': True},
            'validated_at':      {'required': False, 'allow_null': True},
            'working_date_day':  {'required': False, 'allow_null': True},
            'customer_name':     {'required': False, 'allow_null': True, 'allow_blank': True},
            'product_code':      {'required': False, 'allow_null': True, 'allow_blank': True},
            'product_name':      {'required': False, 'allow_null': True, 'allow_blank': True},
            'compte_number':     {'required': False, 'allow_null': True, 'allow_blank': True},
            'recu_number':       {'required': False, 'allow_null': True, 'allow_blank': True},
        }

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être supérieur à 0 FCFA.")
        return value


class TransactionListSerializer(serializers.ModelSerializer):
    

    class Meta:
        model  = Transaction
        fields = [
            'id',
            'reference',
            'code',
            'customer_name',
            'product_code',
            'product_name',
            'compte_number',
            'recu_number',
            'amount',
            'status',
            'sale_agent_code',
            'working_date_day',
            'created_at',
        ]
        read_only_fields = ['id', 'reference', 'created_at']



class TransactionAmountSerializer(serializers.Serializer):
    """
    Utilisé pour : PATCH /api/transactions/<pk>/update-amount/
    Correspond à l'input éditable dans la colonne "Montant (FCFA)" du tableau.

    Body : { "amount": 7500 }
    """
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être supérieur à 0 FCFA.")
        return value


class TransactionValidateBatchSerializer(serializers.Serializer):

    ids          = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        help_text="Liste des IDs de transactions à valider"
    )
    validated_by = serializers.CharField(
        max_length=100,
        help_text="User.code de la caissière qui valide"
    )
    
    
class OperationSerializer(serializers.ModelSerializer):

    class Meta:
        model  = Operation
        fields = [
            'id', 'reference', 'type_operation',
            'customer_code', 'customer_name',
            'compte_number', 'recu_number',
            'amount',
            'agence_code', 'user_code',
            'working_date_day',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'reference', 'created_at', 'updated_at']
        extra_kwargs = {
            'customer_code':    {'required': False, 'allow_null': True, 'allow_blank': True},
            'customer_name':    {'required': False, 'allow_null': True, 'allow_blank': True},
            'compte_number':    {'required': False, 'allow_null': True, 'allow_blank': True},
            'recu_number':      {'required': False, 'allow_null': True, 'allow_blank': True},
            'agence_code':      {'required': False, 'allow_null': True, 'allow_blank': True},
            'user_code':        {'required': False, 'allow_null': True, 'allow_blank': True},
            'working_date_day': {'required': False, 'allow_null': True},
        }

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être supérieur à 0 FCFA.")
        return value

    def validate_type_operation(self, value):
        if value not in ('retrait', 'versement'):
            raise serializers.ValidationError("type_operation doit être 'retrait' ou 'versement'.")
        return value


class OperationListSerializer(serializers.ModelSerializer):

    class Meta:
        model  = Operation
        fields = [
            'id', 'reference', 'type_operation',
            'customer_code', 'customer_name',
            'compte_number', 'recu_number',
            'amount',
            'agence_code', 'user_code',
            'working_date_day', 'created_at',
        ]
        read_only_fields = ['id', 'reference', 'created_at']