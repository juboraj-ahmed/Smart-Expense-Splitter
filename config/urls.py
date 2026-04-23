"""
URL configuration for Smart Expense Splitter project.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_nested import routers

from apps.accounts import views as account_views
from apps.groups import views as group_views
from apps.expenses import views as expense_views

# Initialize router
router = routers.SimpleRouter()

# ========================
# Accounts Routes
# ========================
router.register(r'users', account_views.UserViewSet, basename='user')

# ========================
# Groups Routes
# ========================
groups_router = routers.NestedSimpleRouter(router, r'users', lookup='user')
router.register(r'groups', group_views.GroupViewSet, basename='group')

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API v1
    path('api/v1/', include([
        # Authentication
        path('auth/register/', account_views.RegisterView.as_view(), name='register'),
        path('auth/login/', account_views.LoginView.as_view(), name='login'),
        path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
        
        # Router URLs
        path('', include(router.urls)),
        
        # Groups nested routes
        path('groups/<int:group_id>/balances/', group_views.GroupBalancesView.as_view(), name='group-balances'),
        path('groups/<int:group_id>/expenses/', expense_views.GroupExpensesView.as_view(), name='group-expenses'),
        path('groups/<int:group_id>/settlements/', expense_views.GroupSettlementsView.as_view(), name='group-settlements'),
        path('groups/<int:group_id>/add_member/', group_views.AddMemberView.as_view(), name='add-member'),
        
        # Expenses
        path('expenses/', expense_views.ExpenseViewSet.as_view({'post': 'create', 'get': 'list'}), name='expense-list'),
        path('expenses/create_equal_split/', expense_views.CreateEqualSplitView.as_view(), name='create-equal-split'),
        path('expenses/<int:pk>/', expense_views.ExpenseViewSet.as_view({'get': 'retrieve'}), name='expense-detail'),
        
        # Settlements/Payments
        path('settlements/', expense_views.SettlementViewSet.as_view({'post': 'create', 'get': 'list'}), name='settlement-list'),
        path('settlements/<int:pk>/', expense_views.SettlementViewSet.as_view({'get': 'retrieve'}), name='settlement-detail'),
        path('settlements/<int:pk>/confirm/', expense_views.SettlementViewSet.as_view({'post': 'confirm'}), name='settlement-confirm'),
        
        # Trust Score
        path('users/<int:user_id>/trust-score/', account_views.TrustScoreView.as_view(), name='trust-score'),
        path('users/<int:user_id>/balance_with/<int:other_user_id>/', expense_views.BalanceBetweenUsersView.as_view(), name='balance-between-users'),

        # Dashboard and Notifications
        path('dashboard/', expense_views.DashboardView.as_view(), name='dashboard'),
        path('notifications/', expense_views.NotificationListView.as_view(), name='notifications'),
    ])),
]

# API Root (for browsable API)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse

class APIRootView(APIView):
    """
    Root API endpoint providing navigation to all available endpoints.
    """
    def get(self, request, format=None):
        return Response({
            'auth': {
                'register': reverse('register', request=request),
                'login': reverse('login', request=request),
                'token_refresh': reverse('token_refresh', request=request),
            },
            'users': reverse('user-list', request=request),
            'groups': reverse('group-list', request=request),
            'expenses': reverse('expense-list', request=request),
            'settlements': reverse('settlement-list', request=request),
        })

urlpatterns.insert(0, path('api/v1/root/', APIRootView.as_view(), name='api-root'))
