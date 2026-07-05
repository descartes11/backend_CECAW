from django.contrib import admin
from django.urls import path
from api import views


urlpatterns = [
    path('auth/login/',   views.login,         name='login'),
    path('auth/refresh/', views.token_refresh, name='token-refresh'),
    path('auth/logout/',  views.logout,        name='logout'),
    
    
    path('users/', views.user_list, name='user-list'),
    path('users/<int:pk>/', views.user_detail, name='user-detail'),
    path('users/code/<str:code>/', views.user_by_code, name='user-by-code'),
    path('users/agence/<str:agence_code>/', views.users_by_agence, name='users-by-agence'),
    
    
    path('clients/',                                views.client_list,          name='client-list'),
    path('clients/<int:pk>/',                       views.client_detail,        name='client-detail'),
    path('clients/code/<str:code>/',                views.client_by_code,       name='client-by-code'),
    path('clients/agence/<str:agence_code>/',       views.clients_by_agence,    name='clients-by-agence'),
    path('clients/agent/<str:sale_agent_code>/',    views.clients_by_agent,     name='clients-by-agent'),
    path('clients/<int:pk>/toggle-active/',         views.client_toggle_active, name='client-toggle-active'),
    
    path('commerciaux/',                              views.commerciaux_list,          name='commerciaux-list'),
    path('commerciaux/<int:pk>/',                     views.commerciaux_detail,        name='commerciaux-detail'),
    path('commerciaux/code/<str:code>/',              views.commerciaux_by_code,       name='commerciaux-by-code'),
    path('commerciaux/agence/<str:agence_code>/',     views.commerciaux_by_agence,     name='commerciaux-by-agence'),
    path('commerciaux/<int:pk>/clients/',             views.clients_of_commercial,     name='commerciaux-clients'),
    path('commerciaux/<int:pk>/toggle-active/',       views.commerciaux_toggle_active, name='commerciaux-toggle-active'),
    
    path('prets/',                                        views.prets_list,           name='prets-list'),
    path('prets/<int:pk>/',                               views.prets_detail,         name='prets-detail'),
    path('prets/reference/<str:reference>/',              views.prets_by_reference,   name='prets-by-reference'),
    path('prets/client/<str:customer_code>/',             views.prets_by_client,      name='prets-by-client'),
    path('prets/agence/<str:agence_code>/',               views.prets_by_agence,      name='prets-by-agence'),
    path('prets/status/<str:pret_status>/',               views.prets_by_status,      name='prets-by-status'),
    path('prets/<int:pk>/change-status/',                 views.prets_change_status,  name='prets-change-status'),
    
    path('comptes/',                                       views.compte_list,           name='compte-list'),
    path('comptes/<int:pk>/',                              views.compte_detail,         name='compte-detail'),
    path('comptes/number/<str:number>/',                   views.compte_by_number,      name='compte-by-number'),
    path('comptes/client/<str:customer_code>/',            views.comptes_by_client,     name='comptes-by-client'),
    path('comptes/agence/<str:agence_code>/',              views.comptes_by_agence,     name='comptes-by-agence'),
    path('comptes/<int:pk>/update-balance/',               views.compte_update_balance, name='compte-update-balance'),
    path('comptes/<int:pk>/toggle-active/',                views.compte_toggle_active,  name='compte-toggle-active'),
    
    path('produits/',                              views.produits_list,          name='produits-list'),
    path('produits/<int:pk>/',                     views.produits_detail,        name='produits-detail'),
    path('produits/code/<str:code>/',              views.produits_by_code,       name='produits-by-code'),
    path('produits/<int:pk>/prets/',               views.prets_of_produit,       name='produits-prets'),
    path('produits/<int:pk>/comptes/',             views.comptes_of_produit,     name='produits-comptes'),
    path('produits/<int:pk>/toggle-active/',       views.produits_toggle_active, name='produits-toggle-active'),
    
    path('recus/',                                  views.recus_list,       name='recus-list'),
    path('recus/<int:pk>/',                         views.recus_detail,     name='recus-detail'),
    path('recus/number/<str:number>/',              views.recus_by_number,  name='recus-by-number'),
    path('recus/agence/<str:agence_code>/',         views.recus_by_agence,  name='recus-by-agence'),
    path('recus/agent/<str:sale_agent_code>/',      views.recus_by_agent,   name='recus-by-agent'),
    path('recus/<int:pk>/cancel/',                  views.recus_cancel,     name='recus-cancel'),
    
    path('transactions/',                                      views.transaction_list,           name='transaction-list'),
    path('transactions/<int:pk>/',                             views.transaction_detail,         name='transaction-detail'),
    path('transactions/<int:pk>/update-amount/',               views.transaction_update_amount,  name='transaction-update-amount'),
    path('transactions/validate-batch/',                       views.transaction_validate_batch, name='transaction-validate-batch' ),
    path('transactions/agent/<str:sale_agent_code>/today/',    views.transaction_agent_today,    name='transaction-agent-today'),
    
    path('operations/',                             views.operation_list,         name='operation-list'),
    path('operations/<int:pk>/',                    views.operation_detail,       name='operation-detail'),
    path('operations/client/<str:customer_code>/',  views.operations_by_client,   name='operations-by-client'),
    path('operations/agence/<str:agence_code>/',    views.operations_by_agence,   name='operations-by-agence'),
]


