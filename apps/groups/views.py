"""
Views for groups app.
Handles group creation, management, and member operations.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from apps.groups.models import Group, Membership
from apps.groups.serializers import (
    GroupSerializer,
    GroupCreateSerializer,
    AddMemberSerializer,
    MembershipSerializer,
)
from apps.expenses.services import SettlementService

User = get_user_model()


class GroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing groups.
    
    GET /api/v1/groups/ - List user's groups
    POST /api/v1/groups/ - Create new group
    GET /api/v1/groups/{id}/ - Get group details
    """
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Only return groups the user is a member of.
        
        This is a critical security check: users should not see
        other groups they're not part of.
        """
        return Group.objects.filter(
            memberships__user=self.request.user
        ).distinct()
    
    def get_serializer_class(self):
        """Use different serializer for creation."""
        if self.action == 'create':
            return GroupCreateSerializer
        return GroupSerializer
    
    def get_serializer_context(self):
        """Pass request to serializers for context."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def create(self, request, *args, **kwargs):
        """
        Create new group.
        Creator is automatically added as admin member.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create group with creator
        group = Group.objects.create(
            created_by=request.user,
            **serializer.validated_data
        )
        
        # Add creator as admin
        Membership.objects.create(
            group=group,
            user=request.user,
            role='admin'
        )
        
        # Return group details
        output_serializer = GroupSerializer(group, context=self.get_serializer_context())
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
    
    def list(self, request, *args, **kwargs):
        """
        List groups with pagination and search.
        
        Query parameters:
        - search: Filter by group name
        - page: Page number (default 1)
        """
        return super().list(request, *args, **kwargs)


class AddMemberView(APIView):
    """
    POST /api/v1/groups/{group_id}/add_member/
    
    Add a user to a group.
    
    Request:
    {
      "user_id": 3,
      "role": "member"  # or "admin"
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, group_id):
        # Get group (verify user is member/admin)
        group = get_object_or_404(Group, id=group_id)
        
        # Check if requester is admin in group
        is_admin = Membership.objects.filter(
            group=group,
            user=request.user,
            role='admin'
        ).exists()
        
        if not is_admin and request.user != group.created_by:
            return Response(
                {'error': 'Only group admins can add members'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate input
        serializer = AddMemberSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user_id = serializer.validated_data['user_id']
        role = serializer.validated_data.get('role', 'member')
        
        # Get user
        try:
            user_to_add = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return Response(
                {'error': 'User does not exist'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already member
        if Membership.objects.filter(group=group, user=user_to_add).exists():
            return Response(
                {'error': f'{user_to_add.username} is already a member'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add member
        membership = Membership.objects.create(
            group=group,
            user=user_to_add,
            role=role
        )
        
        return Response(
            {
                'message': 'User added successfully',
                'member': {
                    'id': user_to_add.id,
                    'username': user_to_add.username,
                    'role': role,
                }
            },
            status=status.HTTP_201_CREATED
        )


class GroupBalancesView(APIView):
    """
    GET /api/v1/groups/{group_id}/balances/
    
    Get all balances in a group.
    Shows who paid what, who owes what, and net balance per user.
    
    Response:
    {
      "group_id": 5,
      "total_expenses": 850.00,
      "balances": [
        {
          "user": {...},
          "total_paid": 450.00,
          "total_owes": 300.00,
          "net_balance": 150.00
        }
      ]
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, group_id):
        # Get group
        group = get_object_or_404(Group, id=group_id)
        
        # Check membership
        if not Membership.objects.filter(group=group, user=request.user).exists():
            return Response(
                {'error': 'You are not a member of this group'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get balances
        balances = SettlementService.get_group_balances(group)
        
        from django.db.models import Sum
        from apps.expenses.models import Expense
        
        total_expenses = Expense.objects.filter(group=group).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        return Response({
            'group_id': group.id,
            'group_name': group.name,
            'total_expenses': str(total_expenses),
            'balances': balances,
        })
