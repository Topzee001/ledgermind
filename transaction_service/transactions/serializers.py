"""
Transaction serializers.
"""
from rest_framework import serializers
from .models import Transaction
from categories.serializers import CategorySerializer
from categories.models import Category

class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction CRUD operations."""
    category_detail = CategorySerializer(source='category', read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', allow_null=True, required=False
    )

    class Meta:
        model = Transaction
        fields = [
            'id', 'business_id', 'category_id', 'category_detail', 'type',
            'amount', 'description', 'date', 'ai_categorized', 'source',
            'reference', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'ai_categorized', 'source']
        
    def validate(self, attrs):
        """Additional validations."""
        if attrs.get('type') not in ['income', 'expense']:
            raise serializers.ValidationError({"type": "Must be either 'income' or 'expense'."})
        return attrs

class TransactionUploadSerializer(serializers.Serializer):
    """Serializer for CSV/Batch uploads."""
    business_id = serializers.UUIDField()
    file = serializers.FileField()
