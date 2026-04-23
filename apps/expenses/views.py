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
from django.db.models import Sum, Q
from decimal import Decimal

from apps.expenses.models import Expense, Split, Payment, Notification
from apps.groups.models import Group, Membership
from apps.accounts.models import User
from apps.expenses.serializers import (
    ExpenseSerializer,
    CreateExpenseWithSplitsSerializer,
    CreateEqualSplitSerializer,
    PaymentSerializer,
)
from apps.expenses.services import (
    ExpenseService,
    SettlementService,
    TrustScoreService,
)

def format_standard_response(transaction_id, status_val, amount, timestamp, message, data=None):
    response = {
        "transaction_id": str(transaction_id) if transaction_id else None,
        "status": status_val,
        "amount": str(amount) if amount else "0.00",
        "timestamp": timestamp.isoformat() if timestamp else None,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return response

class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Expense.objects.filter(
            group__memberships__user=self.request.user
        ).select_related('paid_by').prefetch_related('splits')
    
    def create(self, request, *args, **kwargs):
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
            return Response(
                format_standard_response(
                    transaction_id=expense.transaction_id,
                    status_val="COMPLETED",
                    amount=expense.amount,
                    timestamp=expense.created_at,
                    message="Expense created successfully",
                    data=output_serializer.data
                ),
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CreateEqualSplitView(APIView):
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
            return Response(
                format_standard_response(
                    transaction_id=expense.transaction_id,
                    status_val="COMPLETED",
                    amount=expense.amount,
                    timestamp=expense.created_at,
                    message="Equal split expense created successfully",
                    data=output_serializer.data
                ),
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class GroupExpensesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        if not Membership.objects.filter(group=group, user=request.user).exists():
            return Response({'error': 'You are not a member of this group'}, status=status.HTTP_403_FORBIDDEN)
        
        expenses = Expense.objects.filter(group=group).select_related('paid_by').prefetch_related('splits').order_by('-created_at')
        serializer = ExpenseSerializer(expenses, many=True)
        return Response({'count': expenses.count(), 'results': serializer.data})

class SettlementViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(
            group__memberships__user=self.request.user
        ).select_related('from_user', 'to_user')
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = PaymentSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        try:
            group = get_object_or_404(Group, id=serializer.validated_data.get('group_id'))
            to_user = get_object_or_404(User, id=serializer.validated_data.get('to_user_id'), is_active=True)
            amount = serializer.validated_data.get('amount')
            
            payment = SettlementService.record_settlement(
                from_user=request.user,
                to_user=to_user,
                group=group,
                amount=amount,
                description=serializer.validated_data.get('description', ''),
            )
            
            output_serializer = PaymentSerializer(payment)
            return Response(
                format_standard_response(
                    transaction_id=payment.transaction_id,
                    status_val="PENDING",
                    amount=payment.amount,
                    timestamp=payment.created_at,
                    message="Settlement payment recorded and pending confirmation",
                    data=output_serializer.data
                ),
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        try:
            payment = self.get_object()
            if payment.to_user != request.user:
                return Response({"error": "Only the recipient can confirm the payment."}, status=status.HTTP_403_FORBIDDEN)
            
            payment.status = 'COMPLETED'
            payment.save()
            
            TrustScoreService.recalculate_score(payment.from_user)
            
            return Response(
                format_standard_response(
                    transaction_id=payment.transaction_id,
                    status_val="COMPLETED",
                    amount=payment.amount,
                    timestamp=payment.updated_at,
                    message="Transaction successful"
                )
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class GroupSettlementsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        if not Membership.objects.filter(group=group, user=request.user).exists():
            return Response({'error': 'You are not a member of this group'}, status=status.HTTP_403_FORBIDDEN)
        
        payments = Payment.objects.filter(group=group).select_related('from_user', 'to_user').order_by('-created_at')
        serializer = PaymentSerializer(payments, many=True)
        return Response({'count': payments.count(), 'results': serializer.data})

class BalanceBetweenUsersView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, user_id, other_user_id):
        group_id = request.query_params.get('group_id')
        if not group_id:
            return Response({'error': 'group_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        group = get_object_or_404(Group, id=group_id)
        if not Membership.objects.filter(group=group, user=request.user).exists():
            return Response({'error': 'You are not a member of this group'}, status=status.HTTP_403_FORBIDDEN)
        
        user1 = get_object_or_404(User, id=user_id, is_active=True)
        user2 = get_object_or_404(User, id=other_user_id, is_active=True)
        
        balance = SettlementService.calculate_balance_between_users(user1, user2, group)
        
        return Response({
            'from_user': {'id': user1.id, 'username': user1.username},
            'to_user': {'id': user2.id, 'username': user2.username},
            'group_id': group.id,
            'net_balance': str(balance),
            'details': {
                'interpretation': f'{user1.username} owes {user2.username}' if balance < 0 else f'{user2.username} owes {user1.username}',
                'amount': str(abs(balance)),
            }
        })

class DashboardView(APIView):
    """
    GET /api/v1/dashboard/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        groups = Group.objects.filter(memberships__user=user)
        
        total_owed = Decimal('0.00')
        total_to_receive = Decimal('0.00')
        
        for group in groups:
            bal = SettlementService.calculate_user_balance(user, group)
            if bal < 0:
                total_owed += abs(bal)
            elif bal > 0:
                total_to_receive += bal
                
        recent_payments = Payment.objects.filter(
            Q(from_user=user) | Q(to_user=user)
        ).order_by('-created_at')[:5]
        
        recent_txns = []
        for p in recent_payments:
            direction = "SENT" if p.from_user == user else "RECEIVED"
            recent_txns.append({
                "transaction_id": str(p.transaction_id),
                "type": direction,
                "other_user": p.to_user.username if direction == "SENT" else p.from_user.username,
                "amount": str(p.amount),
                "status": p.status,
                "timestamp": p.created_at.isoformat()
            })
            
        return Response({
            "trust_score": user.trust_score,
            "financial_summary": {
                "total_owed": str(total_owed),
                "total_to_receive": str(total_to_receive),
                "net_position": str(total_to_receive - total_owed)
            },
            "recent_transactions": recent_txns
        })

class NotificationListView(APIView):
    """
    GET /api/v1/notifications/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
        data = [{
            "id": n.id,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat()
        } for n in notifications]
        
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"notifications": data})
