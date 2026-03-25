"""
Business serializers.
"""
from rest_framework import serializers
from .models import Business


class BusinessSerializer(serializers.ModelSerializer):
    """Serializer for Business CRUD operations."""
    owner_email = serializers.ReadOnlyField(source='owner.email')

    class Meta:
        model = Business
        fields = [
            'id', 'name', 'industry', 'description', 'address',
            'phone', 'email', 'website', 'owner_email',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Set the owner to the authenticated user."""
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class BusinessListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing businesses."""
    class Meta:
        model = Business
        fields = ['id', 'name', 'industry', 'created_at']
