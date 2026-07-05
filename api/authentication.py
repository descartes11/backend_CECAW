import jwt
from datetime import datetime, timezone, timedelta
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import User


def generate_access_token(user):
    payload = {
        'user_id':    user.id,
        'user_code':  user.code,
        'role_name':  user.role_name,
        'agence_code': user.agence_code,
        'exp': datetime.now(timezone.utc) + settings.JWT_ACCESS_TOKEN_LIFETIME,
        'iat': datetime.now(timezone.utc),
        'type': 'access',
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def generate_refresh_token(user):
    payload = {
        'user_id': user.id,
        'exp': datetime.now(timezone.utc) + timedelta(days=1),
        'iat': datetime.now(timezone.utc),
        'type': 'refresh',
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    # Stockage en base pour pouvoir invalider
    user.remember_token = token
    user.save()
    return token


def decode_token(token):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed('Token expiré. Reconnectez-vous.')
    except jwt.InvalidTokenError:
        raise AuthenticationFailed('Token invalide.')


class CustomJWTAuthentication(BaseAuthentication):
    """
    Lit : Authorization: Bearer <access_token>
    """
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]
        payload = decode_token(token)

        if payload.get('type') != 'access':
            raise AuthenticationFailed('Fournissez votre access token.')

        try:
            user = User.objects.get(id=payload['user_id'], deleted_at__isnull=True)
        except User.DoesNotExist:
            raise AuthenticationFailed('Utilisateur introuvable.')

        return (user, token)