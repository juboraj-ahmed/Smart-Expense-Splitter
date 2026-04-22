"""
Views for expenses app.
Handles expense creation, splits, settlements, and balance calculations.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal

from apps.expenses.models import Expense, Split, Payment
from apps.groups.models import Group, Membership
from apps.accounts.models import User
from apps.expenses.serializers import (
    ExpenseSerializer,
    CreateExpenseWithSplitsSerializer,
    CreateEqualSplitSerializer,
    PaymentSerializer,
    BalanceBetweenUsersSerializer,
    GroupBalancesSerializer,
)
from apps.expenses.services import (
    ExpenseService,
    SettlementService,
    TrustScoreService,
)


class ExpenseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing expenses.
    
    POST /api/v1/expenses/ - Create new expense
    GET /api/v1/expenses/ - List user's expenses
    GET /api/v1/expenses/{id}/ - Get expense details
    """
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Only return expenses from groups user is member of."""
        return Expense.objects.filter(
            group__memberships__user=self.request.user
        ).select_related('paid_by').prefetch_related('splits')
    
    def create(self, request, *args, **kwargs):
        """
        Create expense with splits.
        
        Request:
        {
          "group_id": 5,
          "amount": "300.00",
          "description": "Hotel",
          "splits": [
            {"user_id": 1, "amount": "100.00"},
            {"user_id": 2, "amount": "100.00"},
            {"user_id": 3, "amount": "100.00"}
          ]
        }
        """
        serializer = CreateExpenseWithSplitsSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            expense = ExpenseService.create_expense_with_splits(
                group_id=serializer.validated_data['group'].id,
                paid_by=request.user,
                amount=serializer.validated_data['amount'],
                description=serializer.validated_data.get('description', ''),
                category=serializer.validated_data.get('category', 'other'),
                splits_data=serializer.validated_data['splits'],
            )
            
            output_serializer = ExpenseSerializer(expense)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CreateEqualSplitView(APIView):
    """
    POST /api/v1/expenses/create_equal_split/
    
    Convenience endpoint to split expense equally among participants.
    Handles rounding by allocating remainder to last participant.
    
    Request:
    {
      "group_id": 5,
      "amount": "120.00",
      "description": "Pizza",
      "category": "food",
      "participant_ids": [1, 2, 3, 4]
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = CreateEqualSplitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            expense = ExpenseService.create_equal_splits(
                group_id=serializer.validated_data['group_id'],
                paid_by=request.user,
                amount=serializer.validated_data['amount'],
                description=serializer.validated_data.get('description', ''),
                category=serializer.validated_data.get('category', 'other'),
                participant_ids=serializer.validated_data['participant_ids'],
            )
            
            output_serializer = ExpenseSerializer(expense)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class GroupExpensesView(APIView):
    """
    GET /api/v1/groups/{group_id}/expenses/?limit=10&category=food
    
    List expenses in a group with pagination and filtering.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, group_id):
        # Get group and check membership
        group = get_object_or_404(Group, id=group_id)
        if not Membership.objects.filter(group=group, user=request.user).exists():
            return Response(
                {'error': 'You are not a member of this group'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get expenses
        expenses = Expense.objects.filter(group=group).select_related(
            'paid_by'
        ).prefetch_related('splits').order_by('-created_at')
        
        # Filter by category if provided
        category = request.query_params.get('category')
        if category:
            expenses = expenses.filter(category=category)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        limit = min(int(request.query_params.get('limit', 20)), 100)
        
        total = expenses.count()
        start = (page - 1) * limit
        expenses = expenses[start:start + limit]
        
        serializer = ExpenseSerializer(expenses, many=True)
        
        return Response({
            'count': total,
            'page': page,
            'limit': limit,
            'results': serializer.data,
        })


class SettlementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing settlements (payments).
    
    POST /api/v1/settlements/ - Record payment
    GET /api/v1/settlements/ - List payments
    GET /api/v1/settlements/{id}/ - Get payment details
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Only return payments for groups user is member of."""
        return Payment.objects.filter(
            group__memberships__user=self.request.user
        ).select_related('from_user', 'to_user')
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Record settlement payment.
        
        Request:
        {
          "group_id": 5,
          "to_user_id": 2,
          "amount": "75.50",
          "description": "Payment for hotel"
        }
        """
        serializer = PaymentSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        group_id = serializer.validated_data.get('group_id')
        to_user_id = serializer.validated_data.get('to_user_id')
        amount = serializer.validated_data.get('amount')
        description = serializer.validated_data.get('description', '')
        
        try:
            # Get users and group
            group = get_object_or_404(Group, id=group_id)
            to_user = get_object_or_404(User, id=to_user_id, is_active=True)
            
            # Record settlement
            payment = SettlementService.record_settlement(
                from_user=request.user,
                to_user=to_user,
                group=group,
                amount=amount,
                description=description,
            )
            
            output_serializer = PaymentSerializer(payment)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        try:
            payment = self.get_object()
            if payment.to_user != request.user:
                return Response(
                    {"error": "Only the recipient can confirm the payment."}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            payment.status = 'accepted'
            payment.save()
            return Response({"status": "Payment confirmed", "id": payment.id})
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class GroupSettlementsView(APIView):
    """
    GET /api/v1/groups/{group_id}/settlements/?limit=10
    
    List all settlements (payments) in a group.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, group_id):
        # Get group and check membership
        group = get_object_or_404(Group, id=group_id)
        if not Membership.objects.filter(group=group, user=request.user).exists():
            return Response(
                {'error': 'You are not a member of this group'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get payments
        payments = Payment.objects.filter(group=group).select_related(
            'from_user', 'to_user'
        ).order_by('-created_at')
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        limit = min(int(request.query_params.get('limit', 20)), 100)
        
        total = payments.count()
        start = (page - 1) * limit
        payments = payments[start:start + limit]
        
        serializer = PaymentSerializer(payments, many=True)
        
        return Response({
            'count': total,
            'page': page,
            'limit': limit,
            'results': serializer.data,
        })


class BalanceBetweenUsersView(APIView):
    """
    GET /api/v1/users/{user_id}/balance_with/{other_user_id}/?group_id=5
    
    Get balance between two specific users in a group.
    
    Response:
    {
      "from_user": {...},
      "to_user": {...},
      "group_id": 5,
      "net_balance": -75.50,  # Negative = from_user owes to_user
      "details": {...}
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, user_id, other_user_id):
        # Get group
        group_id = request.query_params.get('group_id')
        if not group_id:
            return Response(
                {'error': 'group_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        group = get_object_or_404(Group, id=group_id)
        
        # Check user is member
        if not Membership.objects.filter(group=group, user=request.user).exists():
            return Response(
                {'error': 'You are not a member of this group'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get users
        user1 = get_object_or_404(User, id=user_id, is_active=True)
        user2 = get_object_or_404(User, id=other_user_id, is_active=True)
        
        # Check both are members of group
        for user in [user1, user2]:
            if not Membership.objects.filter(group=group, user=user).exists():
                return Response(
                    {'error': f'{user.username} is not a member of this group'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Calculate balance
        balance = SettlementService.calculate_balance_between_users(user1, user2, group)
        
        # Get detailed metrics
        u1_paid_u2 = Split.objects.filter(
            user=user2,
            expense__paid_by=user1,
            expense__group=group
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        u2_paid_u1 = Split.objects.filter(
            user=user1,
            expense__paid_by=user2,
            expense__group=group
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        return Response({
            'from_user': {'id': user1.id, 'username': user1.username},
            'to_user': {'id': user2.id, 'username': user2.username},
            'group_id': group.id,
            'net_balance': str(balance),
            'details': {
                'total_paid_by_from_user': str(u1_paid_u2),
                'total_paid_by_to_user': str(u2_paid_u1),
                'interpretation': f'{user1.username} owes {user2.username}' if balance < 0 else f'{user2.username} owes {user1.username}',
                'amount': str(abs(balance)),
            }
        })
