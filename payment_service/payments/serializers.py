from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'business_id', 'amount', 'currency', 'status', 'description', 
                  'reference', 'interswitch_ref', 'created_at']
        read_only_fields = ['id', 'status', 'reference', 'interswitch_ref', 'created_at']

class InitiatePaymentSerializer(serializers.Serializer):
    business_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField(max_length=255)
    callback_url = serializers.URLField(required=False, default="http://localhost:3000/payment-callback")
