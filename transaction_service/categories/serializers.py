"""Category serializers."""
from rest_framework import serializers
from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'type', 'description', 'is_default', 'business_id', 'created_at']
        read_only_fields = ['id', 'created_at']
