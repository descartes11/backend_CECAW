from datetime import date
import uuid

from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404


from .models import User , Client , Commerciaux,Prets ,Compte ,Produits,Recus,Transaction,Operation
from .serializers import UserSerializer, UserListSerializer ,ClientSerializer, ClientListSerializer,CommerciauxSerializer,CommerciauxListSerializer
from .serializers import  PretsSerializer, PretsListSerializer,CompteSerializer,CompteListSerializer,CompteBalanceSerializer ,ProduitsSerializer,ProduitsListSerializer, OperationSerializer, OperationListSerializer
from .serializers import RecusSerializer,RecusListSerializer,RecusCancelSerializer
from .serializers import TransactionSerializer,TransactionListSerializer,TransactionAmountSerializer,TransactionValidateBatchSerializer
from django.db.models import Sum, Count



from django.contrib.auth.hashers import check_password
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import AuthenticationFailed
from .authentication import generate_access_token, generate_refresh_token, decode_token
from django.db.models import Q  # ← pour corriger is_cancelled


# ✅ LOGIN — retourne access + refresh JWT
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    code     = request.data.get('code')
    password = request.data.get('password')

    if not code or not password:
        return Response(
            {'error': "Les champs 'code' et 'password' sont requis."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(code=code, deleted_at__isnull=True)
    except User.DoesNotExist:
        return Response({'error': 'Utilisateur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

    if not check_password(password, user.password):
        return Response({'error': 'Mot de passe incorrect.'}, status=status.HTTP_401_UNAUTHORIZED)

    access  = generate_access_token(user)
    refresh = generate_refresh_token(user)  # ← stocké dans remember_token

    return Response({
        'access':      access,   # ← JWT valide 30 min
        'refresh':     refresh,  # ← JWT valide 1 jour
        'user_code':   user.code,
        'role_name':   user.role_name,
        'agence_code': user.agence_code,
    }, status=status.HTTP_200_OK)


# ✅ REFRESH — échange le refresh contre un nouveau access
@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    refresh_token = request.data.get('refresh')

    if not refresh_token:
        return Response(
            {'error': "Le champ 'refresh' est requis."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        payload = decode_token(refresh_token)
    except AuthenticationFailed as e:
        return Response({'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

    if payload.get('type') != 'refresh':
        return Response(
            {'error': 'Token invalide. Fournissez votre refresh token.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(
            id=payload['user_id'],
            remember_token=refresh_token,  # ← vérifie que le token n'est pas révoqué
            deleted_at__isnull=True
        )
    except User.DoesNotExist:
        return Response(
            {'error': 'Refresh token révoqué ou utilisateur introuvable.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Rotation automatique : nouveau refresh à chaque appel
    new_access  = generate_access_token(user)
    new_refresh = generate_refresh_token(user)  # ← l'ancien est remplacé en base

    return Response({
        'access':  new_access,
        'refresh': new_refresh,
    }, status=status.HTTP_200_OK)


# ✅ LOGOUT — révoque le refresh token
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    request.user.remember_token = None
    request.user.save()
    return Response({'message': 'Déconnexion réussie.'}, status=status.HTTP_200_OK)




@api_view(['GET', 'POST'])
def user_list(request):
    """
    GET  /api/users/      → Liste tous les utilisateurs non supprimés
    POST /api/users/      → Crée un nouvel utilisateur
    """
    if request.method == 'GET':
        users = User.objects.filter(deleted_at__isnull=True)

        # Filtres optionnels via query params
        agence_code = request.query_params.get('agence_code')
        role_name   = request.query_params.get('role_name')
        dik         = request.query_params.get('dik')

        if agence_code:
            users = users.filter(agence_code=agence_code)
        if role_name:
            users = users.filter(role_name=role_name)
        if dik is not None:
            users = users.filter(dik=dik.lower() == 'true')

        serializer = UserListSerializer(users, many=True)
        return Response({
            'count': users.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def user_detail(request, pk):
    """
    GET    /api/users/<pk>/  → Détail d'un utilisateur
    PUT    /api/users/<pk>/  → Mise à jour complète
    PATCH  /api/users/<pk>/  → Mise à jour partielle
    DELETE /api/users/<pk>/  → Suppression logique (soft delete)
    """
    user = get_object_or_404(User, pk=pk, deleted_at__isnull=True)

    if request.method == 'GET':
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = UserSerializer(user, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        # Soft delete : on renseigne deleted_at plutôt que de supprimer la ligne
        user.deleted_at = timezone.now()
        user.save()
        return Response(
            {'message': f"Utilisateur '{user.code}' supprimé avec succès."},
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
def user_by_code(request, code):
    """
    GET /api/users/code/<code>/  → Récupère un utilisateur par son code
    """
    user = get_object_or_404(User, code=code, deleted_at__isnull=True)
    serializer = UserSerializer(user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def users_by_agence(request, agence_code):
    """
    GET /api/users/agence/<agence_code>/  → Liste les utilisateurs d'une agence
    """
    users = User.objects.filter(agence_code=agence_code, deleted_at__isnull=True)
    serializer = UserListSerializer(users, many=True)
    return Response({
        'agence_code': agence_code,
        'count': users.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def client_list(request):
    """
    GET  /api/clients/  → Liste tous les clients non supprimés
    POST /api/clients/  → Crée un nouveau client

    Filtres disponibles en GET (query params) :
        ?agence_code=C-03
        ?sale_agent_code=C-03-012
        ?active=true
        ?gender=F
        ?user_code=sonkwa
    """
    if request.method == 'GET':
        clients = Client.objects.filter(deleted_at__isnull=True)

        # --- Filtres optionnels ---
        agence_code      = request.query_params.get('agence_code')
        sale_agent_code  = request.query_params.get('sale_agent_code')
        active           = request.query_params.get('active')
        gender           = request.query_params.get('gender')
        user_code        = request.query_params.get('user_code')

        if agence_code:
            clients = clients.filter(agence_code=agence_code)
        if sale_agent_code:
            clients = clients.filter(sale_agent_code=sale_agent_code)
        if active is not None:
            clients = clients.filter(active=active.lower() == 'true')
        if gender:
            clients = clients.filter(gender=gender.upper())
        if user_code:
            clients = clients.filter(user_code=user_code)

        serializer = ClientListSerializer(clients, many=True)
        return Response({
            'count': clients.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = ClientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def client_detail(request, pk):
    """
    GET    /api/clients/<pk>/  → Détail d'un client
    PUT    /api/clients/<pk>/  → Mise à jour complète
    PATCH  /api/clients/<pk>/  → Mise à jour partielle
    DELETE /api/clients/<pk>/  → Suppression logique (soft delete)
    """
    client = get_object_or_404(Client, pk=pk, deleted_at__isnull=True)

    if request.method == 'GET':
        serializer = ClientSerializer(client)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = ClientSerializer(client, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        # Soft delete : on renseigne deleted_at plutôt que de supprimer la ligne
        client.deleted_at = timezone.now()
        client.save()
        return Response(
            {'message': f"Client '{client.code}' supprimé avec succès."},
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
def client_by_code(request, code):
    """
    GET /api/clients/code/<code>/
    Récupère un client par son code unique (ex: CL-C-03-000001)
    """
    client = get_object_or_404(Client, code=code, deleted_at__isnull=True)
    serializer = ClientSerializer(client)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def clients_by_agence(request, agence_code):
    """
    GET /api/clients/agence/<agence_code>/
    Liste tous les clients d'une agence donnée
    """
    clients = Client.objects.filter(agence_code=agence_code, deleted_at__isnull=True)
    serializer = ClientListSerializer(clients, many=True)
    return Response({
        'agence_code': agence_code,
        'count': clients.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def clients_by_agent(request, sale_agent_code):
    """
    GET /api/clients/agent/<sale_agent_code>/
    Liste tous les clients d'un agent commercial donné
    """
    clients = Client.objects.filter(sale_agent_code=sale_agent_code, deleted_at__isnull=True)
    serializer = ClientListSerializer(clients, many=True)
    return Response({
        'sale_agent_code': sale_agent_code,
        'count': clients.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PATCH'])
def client_toggle_active(request, pk):
    """
    PATCH /api/clients/<pk>/toggle-active/
    Active ou désactive un client rapidement sans PUT complet
    """
    client = get_object_or_404(Client, pk=pk, deleted_at__isnull=True)
    client.active = not client.active

    # Si on désactive, on enregistre la date de départ
    if not client.active:
        client.departure_at = timezone.now().date()
    else:
        client.departure_at = None

    client.save()
    return Response({
        'id': client.id,
        'code': client.code,
        'active': client.active,
        'departure_at': client.departure_at,
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def commerciaux_list(request):
    """
    GET  /api/commerciaux/  → Liste tous les commerciaux non supprimés
    POST /api/commerciaux/  → Crée un nouveau commercial

    Filtres disponibles en GET (query params) :
        ?agence_code=C-03
        ?user_code=sonkwa
        ?active=true
        ?connect=false
    """
    if request.method == 'GET':
        commerciaux = Commerciaux.objects.filter(deleted_at__isnull=True)

        # --- Filtres optionnels ---
        agence_code = request.query_params.get('agence_code')
        user_code   = request.query_params.get('user_code')
        active      = request.query_params.get('active')
        connect     = request.query_params.get('connect')

        if agence_code:
            commerciaux = commerciaux.filter(agence_code=agence_code)
        if user_code:
            commerciaux = commerciaux.filter(user_code=user_code)
        if active is not None:
            commerciaux = commerciaux.filter(active=active.lower() == 'true')
        if connect is not None:
            commerciaux = commerciaux.filter(connect=connect.lower() == 'true')

        serializer = CommerciauxListSerializer(commerciaux, many=True)
        return Response({
            'count': commerciaux.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = CommerciauxSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def commerciaux_detail(request, pk):
    """
    GET    /api/commerciaux/<pk>/  → Détail d'un commercial
    PUT    /api/commerciaux/<pk>/  → Mise à jour complète
    PATCH  /api/commerciaux/<pk>/  → Mise à jour partielle
    DELETE /api/commerciaux/<pk>/  → Suppression logique (soft delete)
    """
    commercial = get_object_or_404(Commerciaux, pk=pk, deleted_at__isnull=True)

    if request.method == 'GET':
        serializer = CommerciauxSerializer(commercial)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = CommerciauxSerializer(commercial, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        commercial.deleted_at = timezone.now()
        commercial.save()
        return Response(
            {'message': f"Commercial '{commercial.code}' supprimé avec succès."},
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
def commerciaux_by_code(request, code):
    """
    GET /api/commerciaux/code/<code>/
    Récupère un commercial par son code unique (ex: C-03-001)
    """
    commercial = get_object_or_404(Commerciaux, code=code, deleted_at__isnull=True)
    serializer = CommerciauxSerializer(commercial)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def commerciaux_by_agence(request, agence_code):
    """
    GET /api/commerciaux/agence/<agence_code>/
    Liste tous les commerciaux d'une agence donnée
    """
    commerciaux = Commerciaux.objects.filter(
        agence_code=agence_code,
        deleted_at__isnull=True
    )
    serializer = CommerciauxListSerializer(commerciaux, many=True)
    return Response({
        'agence_code': agence_code,
        'count': commerciaux.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def clients_of_commercial(request, pk):
    """
    GET /api/commerciaux/<pk>/clients/
    Liste tous les clients rattachés à un commercial (via sale_agent_code)
    Lien entre Commerciaux.code et Client.sale_agent_code
    """
    commercial = get_object_or_404(Commerciaux, pk=pk, deleted_at__isnull=True)
    clients = Client.objects.filter(
        sale_agent_code=commercial.code,
        deleted_at__isnull=True
    )
    serializer = ClientListSerializer(clients, many=True)
    return Response({
        'commercial_code': commercial.code,
        'commercial_name': f"{commercial.firstname} {commercial.name}",
        'count': clients.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PATCH'])
def commerciaux_toggle_active(request, pk):
    """
    PATCH /api/commerciaux/<pk>/toggle-active/
    Active ou désactive un commercial rapidement
    """
    commercial = get_object_or_404(Commerciaux, pk=pk, deleted_at__isnull=True)
    commercial.active = not commercial.active
    commercial.save()
    return Response({
        'id': commercial.id,
        'code': commercial.code,
        'active': commercial.active,
    }, status=status.HTTP_200_OK)
    
@api_view(['GET', 'POST'])
def prets_list(request):
    """
    GET  /api/prets/  → Liste tous les prêts non supprimés
    POST /api/prets/  → Crée un nouveau prêt

    Filtres disponibles en GET (query params) :
        ?agence_code=C-03
        ?customer_code=CL-C-03-000326
        ?manager_code=MOGUE-P
        ?user_code=sonkwa
        ?status=paid
        ?product_loan_code=PCR-01
        ?backdated=false
    """
    if request.method == 'GET':
        prets = Prets.objects.filter(deleted_at__isnull=True)

        # --- Filtres optionnels ---
        agence_code        = request.query_params.get('agence_code')
        customer_code      = request.query_params.get('customer_code')
        manager_code       = request.query_params.get('manager_code')
        user_code          = request.query_params.get('user_code')
        pret_status        = request.query_params.get('status')
        product_loan_code  = request.query_params.get('product_loan_code')
        backdated          = request.query_params.get('backdated')

        if agence_code:
            prets = prets.filter(agence_code=agence_code)
        if customer_code:
            prets = prets.filter(customer_code=customer_code)
        if manager_code:
            prets = prets.filter(manager_code=manager_code)
        if user_code:
            prets = prets.filter(user_code=user_code)
        if pret_status:
            prets = prets.filter(status=pret_status)
        if product_loan_code:
            prets = prets.filter(product_loan_code=product_loan_code)
        if backdated is not None:
            prets = prets.filter(backdated=backdated.lower() == 'true')

        serializer = PretsListSerializer(prets, many=True)
        return Response({
            'count': prets.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        data = request.data.copy()
        
        data.setdefault('agence_code', getattr(request.user, 'agence_code', ''))
        data.setdefault('user_code',   getattr(request.user, 'code', ''))
        data.setdefault('status',      'pending')
        data.setdefault('working_date_day', date.today().isoformat())
        data.setdefault('effective_date',   date.today().isoformat())
        
        mois_annee = date.today().strftime('%m%Y')
        reference = f"PRT-{mois_annee}-{uuid.uuid4().hex[:6].upper()}"
        while Prets.objects.filter(reference=reference).exists():
            reference = f"PRT-{mois_annee}-{uuid.uuid4().hex[:6].upper()}"
        data['reference'] = reference
        
        serializer = PretsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def prets_detail(request, pk):
    """
    GET    /api/prets/<pk>/  → Détail d'un prêt
    PUT    /api/prets/<pk>/  → Mise à jour complète
    PATCH  /api/prets/<pk>/  → Mise à jour partielle
    DELETE /api/prets/<pk>/  → Suppression logique (soft delete)
    """
    pret = get_object_or_404(Prets, pk=pk, deleted_at__isnull=True)

    if request.method == 'GET':
        serializer = PretsSerializer(pret)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = PretsSerializer(pret, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        pret.deleted_at = timezone.now()
        pret.save()
        return Response(
            {'message': f"Prêt '{pret.reference}' supprimé avec succès."},
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
def prets_by_reference(request, reference):
    """
    GET /api/prets/reference/<reference>/
    Récupère un prêt par sa référence unique (ex: PRT-C03-052023-2618)
    """
    pret = get_object_or_404(Prets, reference=reference, deleted_at__isnull=True)
    serializer = PretsSerializer(pret)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def prets_by_client(request, customer_code):
    """
    GET /api/prets/client/<customer_code>/
    Liste tous les prêts d'un client donné
    """
    prets = Prets.objects.filter(
        customer_code=customer_code,
        deleted_at__isnull=True
    )
    serializer = PretsListSerializer(prets, many=True)
    return Response({
        'customer_code': customer_code,
        'count': prets.count(),
        'total_amount': sum(p.amount for p in prets),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def prets_by_agence(request, agence_code):
    """
    GET /api/prets/agence/<agence_code>/
    Liste tous les prêts d'une agence
    """
    prets = Prets.objects.filter(
        agence_code=agence_code,
        deleted_at__isnull=True
    )
    serializer = PretsListSerializer(prets, many=True)
    return Response({
        'agence_code': agence_code,
        'count': prets.count(),
        'total_amount': sum(p.amount for p in prets),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def prets_by_status(request, pret_status):
    """
    GET /api/prets/status/<status>/
    Liste tous les prêts selon leur statut
    Statuts valides : pending | active | paid | cancelled | overdue
    """
    valid_statuses = ['pending', 'active', 'paid', 'cancelled', 'overdue']
    if pret_status not in valid_statuses:
        return Response(
            {'error': f"Statut invalide. Valeurs acceptées : {', '.join(valid_statuses)}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    prets = Prets.objects.filter(status=pret_status, deleted_at__isnull=True)
    serializer = PretsListSerializer(prets, many=True)
    return Response({
        'status': pret_status,
        'count': prets.count(),
        'total_amount': sum(p.amount for p in prets),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PATCH'])
def prets_change_status(request, pk):
    """
    PATCH /api/prets/<pk>/change-status/
    Change le statut d'un prêt rapidement.

    Body attendu :
    {
        "status": "active"   ← pending | active | paid | cancelled | overdue
    }
    """
    pret = get_object_or_404(Prets, pk=pk, deleted_at__isnull=True)

    new_status = request.data.get('status')
    valid_statuses = ['pending', 'active', 'paid', 'cancelled', 'overdue']

    if not new_status:
        return Response(
            {'error': "Le champ 'status' est requis."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if new_status not in valid_statuses:
        return Response(
            {'error': f"Statut invalide. Valeurs acceptées : {', '.join(valid_statuses)}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    pret.status = new_status
    pret.status_date = timezone.now().date()
    pret.save()

    return Response({
        'id': pret.id,
        'reference': pret.reference,
        'status': pret.status,
        'status_date': pret.status_date,
    }, status=status.HTTP_200_OK)
    

@api_view(['GET', 'POST'])
def compte_list(request):
    """
    GET  /api/comptes/  → Liste tous les comptes non supprimés
    POST /api/comptes/  → Crée un nouveau compte

    Filtres disponibles en GET (query params) :
        ?agence_code=C-03
        ?customer_code=CL-C-03-000326
        ?sale_agent_code=C-03-012
        ?user_code=Tchatchoua
        ?active=true
        ?can_take_loans=false
        ?is_negative=true       ← filtre les comptes avec solde négatif
    """
    if request.method == 'GET':
        comptes = Compte.objects.filter(deleted_at__isnull=True)

        # --- Filtres optionnels ---
        agence_code      = request.query_params.get('agence_code')
        customer_code    = request.query_params.get('customer_code')
        sale_agent_code  = request.query_params.get('sale_agent_code')
        user_code        = request.query_params.get('user_code')
        active           = request.query_params.get('active')
        can_take_loans   = request.query_params.get('can_take_loans')
        is_negative      = request.query_params.get('is_negative')

        if agence_code:
            comptes = comptes.filter(agence_code=agence_code)
        if customer_code:
            comptes = comptes.filter(customer_code=customer_code)
        if sale_agent_code:
            comptes = comptes.filter(sale_agent_code=sale_agent_code)
        if user_code:
            comptes = comptes.filter(user_code=user_code)
        if active is not None:
            comptes = comptes.filter(active=active.lower() == 'true')
        if can_take_loans is not None:
            comptes = comptes.filter(can_take_loans=can_take_loans.lower() == 'true')
        if is_negative is not None:
            if is_negative.lower() == 'true':
                comptes = comptes.filter(balance__lt=0)
            else:
                comptes = comptes.filter(balance__gte=0)

        # Totaux agrégés
        totaux = comptes.aggregate(
            total_balance=Sum('balance'),
            total_standby=Sum('standby_balance')
        )

        serializer = CompteListSerializer(comptes, many=True)
        return Response({
            'count': comptes.count(),
            'total_balance': totaux['total_balance'] or 0,
            'total_standby_balance': totaux['total_standby'] or 0,
            'results': serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = CompteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def compte_detail(request, pk):
    """
    GET    /api/comptes/<pk>/  → Détail d'un compte
    PUT    /api/comptes/<pk>/  → Mise à jour complète
    PATCH  /api/comptes/<pk>/  → Mise à jour partielle
    DELETE /api/comptes/<pk>/  → Suppression logique (soft delete)
    """
    compte = get_object_or_404(Compte, pk=pk, deleted_at__isnull=True)

    if request.method == 'GET':
        serializer = CompteSerializer(compte)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = CompteSerializer(compte, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        compte.deleted_at = timezone.now()
        compte.save()
        return Response(
            {'message': f"Compte '{compte.number}' supprimé avec succès."},
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
def compte_by_number(request, number):
    """
    GET /api/comptes/number/<number>/
    Récupère un compte par son numéro unique (ex: 571000-C03-000000-00)
    """
    compte = get_object_or_404(Compte, number=number, deleted_at__isnull=True)
    serializer = CompteSerializer(compte)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def comptes_by_client(request, customer_code):
    """
    GET /api/comptes/client/<customer_code>/
    Liste tous les comptes d'un client donné avec le total des soldes
    """
    comptes = Compte.objects.filter(
        customer_code=customer_code,
        deleted_at__isnull=True
    )
    totaux = comptes.aggregate(
        total_balance=Sum('balance'),
        total_standby=Sum('standby_balance')
    )
    serializer = CompteListSerializer(comptes, many=True)
    return Response({
        'customer_code': customer_code,
        'count': comptes.count(),
        'total_balance': totaux['total_balance'] or 0,
        'total_standby_balance': totaux['total_standby'] or 0,
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def comptes_by_agence(request, agence_code):
    """
    GET /api/comptes/agence/<agence_code>/
    Liste tous les comptes d'une agence avec le total des soldes
    """
    comptes = Compte.objects.filter(
        agence_code=agence_code,
        deleted_at__isnull=True
    )
    totaux = comptes.aggregate(
        total_balance=Sum('balance'),
        total_standby=Sum('standby_balance')
    )
    serializer = CompteListSerializer(comptes, many=True)
    return Response({
        'agence_code': agence_code,
        'count': comptes.count(),
        'total_balance': totaux['total_balance'] or 0,
        'total_standby_balance': totaux['total_standby'] or 0,
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PATCH'])
def compte_update_balance(request, pk):
    """
    PATCH /api/comptes/<pk>/update-balance/
    Met à jour uniquement le solde d'un compte.

    Body attendu :
    {
        "balance": "-287514383.00",
        "standby_balance": "0.00"   ← optionnel
    }
    """
    compte = get_object_or_404(Compte, pk=pk, deleted_at__isnull=True)
    serializer = CompteBalanceSerializer(data=request.data)

    if serializer.is_valid():
        compte.balance = serializer.validated_data['balance']
        if 'standby_balance' in serializer.validated_data:
            compte.standby_balance = serializer.validated_data['standby_balance']
        compte.save()
        return Response({
            'id': compte.id,
            'number': compte.number,
            'balance': compte.balance,
            'standby_balance': compte.standby_balance,
            'available_balance': compte.available_balance,
            'is_negative': compte.is_negative,
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
def compte_toggle_active(request, pk):
    """
    PATCH /api/comptes/<pk>/toggle-active/
    Active ou désactive un compte rapidement
    """
    compte = get_object_or_404(Compte, pk=pk, deleted_at__isnull=True)
    compte.active = not compte.active
    compte.save()
    return Response({
        'id': compte.id,
        'number': compte.number,
        'active': compte.active,
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def produits_list(request):
    """
    GET  /api/produits/  → Liste tous les produits non supprimés
    POST /api/produits/  → Crée un nouveau produit

    Filtres disponibles en GET (query params) :
        ?is_active=true
        ?is_paid=false
        ?is_commission_paid=true
        ?user_code=sonkwa
    """
    if request.method == 'GET':
        produits = Produits.objects.filter(deleted_at__isnull=True)

        # --- Filtres optionnels ---
        is_active          = request.query_params.get('is_active')
        is_paid            = request.query_params.get('is_paid')
        is_commission_paid = request.query_params.get('is_commission_paid')
        user_code          = request.query_params.get('user_code')

        if is_active is not None:
            produits = produits.filter(is_active=is_active.lower() == 'true')
        if is_paid is not None:
            produits = produits.filter(is_paid=is_paid.lower() == 'true')
        if is_commission_paid is not None:
            produits = produits.filter(is_commission_paid=is_commission_paid.lower() == 'true')
        if user_code:
            produits = produits.filter(user_code=user_code)

        serializer = ProduitsListSerializer(produits, many=True)
        return Response({
            'count': produits.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = ProduitsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def produits_detail(request, pk):
    """
    GET    /api/produits/<pk>/  → Détail d'un produit
    PUT    /api/produits/<pk>/  → Mise à jour complète
    PATCH  /api/produits/<pk>/  → Mise à jour partielle
    DELETE /api/produits/<pk>/  → Suppression logique (soft delete)
    """
    produit = get_object_or_404(Produits, pk=pk, deleted_at__isnull=True)

    if request.method == 'GET':
        serializer = ProduitsSerializer(produit)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = ProduitsSerializer(produit, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        produit.deleted_at = timezone.now()
        produit.save()
        return Response(
            {'message': f"Produit '{produit.code}' supprimé avec succès."},
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
def produits_by_code(request, code):
    """
    GET /api/produits/code/<code>/
    Récupère un produit par son code unique (ex: PCO-01, PCR-01, PASR-01)
    """
    produit = get_object_or_404(Produits, code=code, deleted_at__isnull=True)
    serializer = ProduitsSerializer(produit)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def prets_of_produit(request, pk):
    """
    GET /api/produits/<pk>/prets/
    Liste tous les prêts utilisant ce produit (product_loan_code)
    Lien : Produits.code → Prets.product_loan_code
    """
    produit = get_object_or_404(Produits, pk=pk, deleted_at__isnull=True)
    prets = Prets.objects.filter(
        product_loan_code=produit.code,
        deleted_at__isnull=True
    )
    serializer = PretsListSerializer(prets, many=True)
    return Response({
        'produit_code': produit.code,
        'produit_name': produit.name,
        'count': prets.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def comptes_of_produit(request, pk):
    """
    GET /api/produits/<pk>/comptes/
    Liste tous les comptes liés à ce produit (product_loan_code)
    Lien : Produits.code → Compte.product_loan_code
    """
    produit = get_object_or_404(Produits, pk=pk, deleted_at__isnull=True)
    comptes = Compte.objects.filter(
        product_loan_code=produit.code,
        deleted_at__isnull=True
    )
    serializer = CompteListSerializer(comptes, many=True)
    return Response({
        'produit_code': produit.code,
        'produit_name': produit.name,
        'count': comptes.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PATCH'])
def produits_toggle_active(request, pk):
    """
    PATCH /api/produits/<pk>/toggle-active/
    Active ou désactive un produit rapidement
    """
    produit = get_object_or_404(Produits, pk=pk, deleted_at__isnull=True)
    produit.is_active = not produit.is_active
    produit.save()
    return Response({
        'id': produit.id,
        'code': produit.code,
        'is_active': produit.is_active,
    }, status=status.HTTP_200_OK)
    

@api_view(['GET', 'POST'])
def recus_list(request):
    """
    GET  /api/recus/  → Liste tous les reçus non supprimés
    POST /api/recus/  → Crée un nouveau reçu

    Filtres disponibles en GET (query params) :
        ?agence_code=C-03
        ?sale_agent_code=C-03-026
        ?user_code=TCHIEUKO-G
        ?is_use=true
        ?is_cancelled=true      ← filtre les reçus annulés (cancel_by renseigné)
    """
    if request.method == 'GET':
        recus = Recus.objects.filter(deleted_at__isnull=True)

        # --- Filtres optionnels ---
        agence_code     = request.query_params.get('agence_code')
        sale_agent_code = request.query_params.get('sale_agent_code')
        user_code       = request.query_params.get('user_code')
        is_use          = request.query_params.get('is_use')
        is_cancelled    = request.query_params.get('is_cancelled')

        if agence_code:
            recus = recus.filter(agence_code=agence_code)
        if sale_agent_code:
            recus = recus.filter(sale_agent_code=sale_agent_code)
        if user_code:
            recus = recus.filter(user_code=user_code)
        if is_use is not None:
            recus = recus.filter(is_use=is_use.lower() == 'true')
        if is_cancelled is not None:
            if is_cancelled.lower() == 'true':
                recus = recus.exclude(cancel_by__isnull=True).exclude(cancel_by='')
            else:
                recus = recus.filter(Q(cancel_by__isnull=True) | Q(cancel_by=''))

        serializer = RecusListSerializer(recus, many=True)
        return Response({
            'count': recus.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = RecusSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def recus_detail(request, pk):
    """
    GET    /api/recus/<pk>/  → Détail d'un reçu
    PUT    /api/recus/<pk>/  → Mise à jour complète
    PATCH  /api/recus/<pk>/  → Mise à jour partielle
    DELETE /api/recus/<pk>/  → Suppression logique (soft delete)
    """
    recu = get_object_or_404(Recus, pk=pk, deleted_at__isnull=True)

    if request.method == 'GET':
        serializer = RecusSerializer(recu)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = RecusSerializer(recu, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        recu.deleted_at = timezone.now()
        recu.save()
        return Response(
            {'message': f"Reçu '{recu.number}' supprimé avec succès."},
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
def recus_by_number(request, number):
    """
    GET /api/recus/number/<number>/
    Récupère un reçu par son numéro unique (ex: 4831165A)
    """
    recu = get_object_or_404(Recus, number=number, deleted_at__isnull=True)
    serializer = RecusSerializer(recu)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def recus_by_agence(request, agence_code):
    """
    GET /api/recus/agence/<agence_code>/
    Liste tous les reçus d'une agence donnée
    """
    recus = Recus.objects.filter(
        agence_code=agence_code,
        deleted_at__isnull=True
    )
    serializer = RecusListSerializer(recus, many=True)
    return Response({
        'agence_code': agence_code,
        'count': recus.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def recus_by_agent(request, sale_agent_code):
    """
    GET /api/recus/agent/<sale_agent_code>/
    Liste tous les reçus d'un agent commercial donné
    """
    recus = Recus.objects.filter(
        sale_agent_code=sale_agent_code,
        deleted_at__isnull=True
    )
    serializer = RecusListSerializer(recus, many=True)
    return Response({
        'sale_agent_code': sale_agent_code,
        'count': recus.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PATCH'])
def recus_cancel(request, pk):
    """
    PATCH /api/recus/<pk>/cancel/
    Annule un reçu en renseignant cancel_by et en passant is_use à False.

    Body attendu :
    {
        "cancel_by": "TCHIEUKO-G",
        "detail": "Erreur de saisie"   ← optionnel
    }
    """
    recu = get_object_or_404(Recus, pk=pk, deleted_at__isnull=True)

    # Vérifier que le reçu n'est pas déjà annulé
    if recu.is_cancelled:
        return Response(
            {'error': f"Ce reçu est déjà annulé par '{recu.cancel_by}'."},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = RecusCancelSerializer(data=request.data)
    if serializer.is_valid():
        recu.cancel_by = serializer.validated_data['cancel_by']
        recu.is_use    = False
        if 'detail' in serializer.validated_data:
            recu.detail = serializer.validated_data['detail']
        recu.save()
        return Response({
            'id':          recu.id,
            'number':      recu.number,
            'is_use':      recu.is_use,
            'is_cancelled': recu.is_cancelled,
            'cancel_by':   recu.cancel_by,
            'detail':      recu.detail,
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def transaction_list(request):
    """
    GET  /api/transactions/
        Liste les transactions avec filtres.
    """
    if request.method == 'GET':
        transactions = Transaction.objects.filter(deleted_at__isnull=True)

        sale_agent_code  = request.query_params.get('sale_agent_code')
        agence_code      = request.query_params.get('agence_code')
        txn_status       = request.query_params.get('status')
        working_date_day = request.query_params.get('working_date_day')

        if sale_agent_code:
            transactions = transactions.filter(sale_agent_code=sale_agent_code)
        if agence_code:
            transactions = transactions.filter(agence_code=agence_code)
        if txn_status:
            transactions = transactions.filter(status=txn_status)
        if working_date_day:
            transactions = transactions.filter(working_date_day=working_date_day)

        agg = transactions.aggregate(total=Sum('amount'), count=Count('id'))

        return Response({
            'count':        agg['count'] or 0,
            'total_amount': agg['total'] or 0,
            'results':      TransactionListSerializer(transactions, many=True).data,
        })

    elif request.method == 'POST':
        serializer = TransactionSerializer(data=request.data)
        if serializer.is_valid():
            transaction = serializer.save(status='pending')
            return Response(
                TransactionSerializer(transaction).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'DELETE'])
def transaction_detail(request, pk):
    """
    GET    /api/transactions/<pk>/
        Détail complet d'une transaction.

    """
    transaction = get_object_or_404(Transaction, pk=pk, deleted_at__isnull=True)

    if request.method == 'GET':
        return Response(TransactionSerializer(transaction).data)

    elif request.method == 'DELETE':
        if transaction.status == 'validated':
            return Response(
                {'error': "Impossible de supprimer une transaction déjà validée."},
                status=status.HTTP_400_BAD_REQUEST
            )
        transaction.deleted_at = timezone.now()
        transaction.status     = 'cancelled'
        transaction.save()
        return Response(
            {'message': f"Transaction '{transaction.reference}' supprimée."},
            status=status.HTTP_200_OK
        )


@api_view(['PATCH'])
def transaction_update_amount(request, pk):
    """
    PATCH /api/transactions/<pk>/update-amount/
    """
    transaction = get_object_or_404(Transaction, pk=pk, deleted_at__isnull=True)

    if transaction.status == 'validated':
        return Response(
            {'error': "Impossible de modifier une transaction déjà validée."},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = TransactionAmountSerializer(data=request.data)
    if serializer.is_valid():
        transaction.amount = serializer.validated_data['amount']
        transaction.save(update_fields=['amount', 'updated_at'])
        return Response({
            'id':        transaction.id,
            'reference': transaction.reference,
            'amount':    transaction.amount,
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['PATCH'])
def transaction_validate_batch(request):
    """
    PATCH /api/transactions/validate-batch/
    
    """
    serializer = TransactionValidateBatchSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    ids          = serializer.validated_data['ids']
    validated_by = serializer.validated_data['validated_by']
    now          = timezone.now()

    updated = Transaction.objects.filter(
        id__in         = ids,
        status         = 'pending',
        deleted_at__isnull = True,
    ).update(
        status       = 'validated',
        validated_by = validated_by,
        validated_at = now,
    )

    total = Transaction.objects.filter(
        id__in  = ids,
        status  = 'validated',
    ).aggregate(total=Sum('amount'))['total'] or 0

    return Response({
        'validated_count': updated,
        'total_amount':    total,
        'message':         f"{updated} transaction(s) validée(s) avec succès.",
    })


@api_view(['GET'])
def transaction_agent_today(request, sale_agent_code):
    """
    GET /api/transactions/agent/<sale_agent_code>/today/

    """
    today = date.today()

    transactions = Transaction.objects.filter(
        sale_agent_code  = sale_agent_code,
        working_date_day = today,
        status           = 'pending',
        deleted_at__isnull = True,
    )

    agg = transactions.aggregate(total=Sum('amount'), count=Count('id'))

    return Response({
        'sale_agent_code': sale_agent_code,
        'date':            today.isoformat(),
        'count':           agg['count'] or 0,
        'total_amount':    agg['total'] or 0,
        'results':         TransactionListSerializer(transactions, many=True).data,
    })
    
    

@api_view(['GET', 'POST'])
def operation_list(request):
    """
    GET  /api/operations/
        ?type_operation=retrait|versement
        ?agence_code=C-03
        ?customer_code=CL-C-03-000326
        ?working_date_day=2026-05-14

    POST /api/operations/
        → Enregistrement immédiat, aucune validation requise.
        Body minimal :
        {
            "type_operation": "versement",
            "customer_code":  "CL-C-03-000326",
            "customer_name":  "JIOKENG Paul",
            "compte_number":  "571000-C03-000326-00",
            "amount":         50000
        }
    """
    if request.method == 'GET':
        operations = Operation.objects.filter(deleted_at__isnull=True)

        type_op          = request.query_params.get('type_operation')
        agence_code      = request.query_params.get('agence_code')
        customer_code    = request.query_params.get('customer_code')
        working_date_day = request.query_params.get('working_date_day')

        if type_op:
            operations = operations.filter(type_operation=type_op)
        if agence_code:
            operations = operations.filter(agence_code=agence_code)
        if customer_code:
            operations = operations.filter(customer_code=customer_code)
        if working_date_day:
            operations = operations.filter(working_date_day=working_date_day)

        agg = operations.aggregate(total=Sum('amount'), count=Count('id'))

        return Response({
            'count':        agg['count'] or 0,
            'total_amount': agg['total'] or 0,
            'results':      OperationListSerializer(operations, many=True).data,
        })
   
    elif request.method == 'POST':
        serializer = OperationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data           = serializer.validated_data
        type_op        = data.get('type_operation')
        compte_number  = data.get('compte_number')
        montant        = data.get('amount')

        # ── 1. Récupérer le compte si fourni ──────────────────────────
        compte = None
        if compte_number:
            try:
                compte = Compte.objects.get(number=compte_number, deleted_at__isnull=True)
            except Compte.DoesNotExist:
                return Response(
                    {'error': f"Compte '{compte_number}' introuvable."},
                    status=status.HTTP_404_NOT_FOUND
                )

        # ── 2. Vérification solde suffisant pour un retrait ───────────
        if type_op == 'retrait' and compte:
            if compte.available_balance < montant:
                return Response(
                    {
                        'error': "Solde insuffisant.",
                        'solde_disponible': str(compte.available_balance),
                        'montant_demande':  str(montant),
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # ── 3. Sauvegarder l'opération ────────────────────────────────
        operation = serializer.save()

        # ── 4. Mettre à jour le solde du compte ───────────────────────
        if compte:
            if type_op == 'versement':
                compte.balance += montant
            elif type_op == 'retrait':
                compte.balance -= montant
            compte.save(update_fields=['balance', 'updated_at'])
        
        prefix       = 'RTR' if type_op == 'retrait' else 'VRS'
        recu_number  = f"{prefix}-{date.today().strftime('%m%Y')}-{uuid.uuid4().hex[:6].upper()}"
        while Recus.objects.filter(number=recu_number).exists():
            recu_number = f"{prefix}-{date.today().strftime('%m%Y')}-{uuid.uuid4().hex[:6].upper()}"

        recu = Recus.objects.create(
            number           = recu_number,
            is_use           = True,
            detail           = f"{type_op.upper()} de {montant} FCFA — Compte {compte_number}",
            working_date_day = date.today(),
            agence_code      = data.get('agence_code'),
            user_code        = data.get('user_code'),
        )
        
        
        operation.recu_number = recu.number
        operation.save(update_fields=['recu_number'])

        # ── 5. Retourner l'opération + le nouveau solde ───────────────
        response_data = OperationSerializer(operation).data
        if compte:
            response_data['nouveau_solde']    = str(compte.balance)
            response_data['solde_disponible'] = str(compte.available_balance)
        response_data['recu'] = {                                        # ← NOUVEAU
            'number':           recu.number,
            'working_date_day': str(recu.working_date_day),
            'detail':           recu.detail,
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

@api_view(['GET', 'DELETE'])
def operation_detail(request, pk):
    """
    GET    /api/operations/<pk>/
    DELETE /api/operations/<pk>/  → soft delete uniquement
    """
    operation = get_object_or_404(Operation, pk=pk, deleted_at__isnull=True)

    if request.method == 'GET':
        return Response(OperationSerializer(operation).data)

    elif request.method == 'DELETE':
        operation.deleted_at = timezone.now()
        operation.save()
        return Response(
            {'message': f"Opération '{operation.reference}' supprimée."},
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
def operations_by_client(request, customer_code):
    """
    GET /api/operations/client/<customer_code>/
        ?type_operation=retrait|versement
    """
    operations = Operation.objects.filter(
        customer_code=customer_code,
        deleted_at__isnull=True,
    )

    type_op = request.query_params.get('type_operation')
    if type_op:
        operations = operations.filter(type_operation=type_op)

    agg = operations.aggregate(total=Sum('amount'), count=Count('id'))
    return Response({
        'customer_code': customer_code,
        'count':         agg['count'] or 0,
        'total_amount':  agg['total'] or 0,
        'results':       OperationListSerializer(operations, many=True).data,
    })


@api_view(['GET'])
def operations_by_agence(request, agence_code):
    """
    GET /api/operations/agence/<agence_code>/
        ?type_operation=retrait|versement
        ?working_date_day=2026-05-14
    """
    operations = Operation.objects.filter(
        agence_code=agence_code,
        deleted_at__isnull=True,
    )

    type_op          = request.query_params.get('type_operation')
    working_date_day = request.query_params.get('working_date_day')
    if type_op:
        operations = operations.filter(type_operation=type_op)
    if working_date_day:
        operations = operations.filter(working_date_day=working_date_day)

    agg = operations.aggregate(total=Sum('amount'), count=Count('id'))
    return Response({
        'agence_code':  agence_code,
        'count':        agg['count'] or 0,
        'total_amount': agg['total'] or 0,
        'results':      OperationListSerializer(operations, many=True).data,
    })