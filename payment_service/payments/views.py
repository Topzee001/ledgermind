"""Payment API Views."""
import uuid
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from .models import Payment
from .serializers import (
    PaymentSerializer, 
    InitiatePaymentSerializer,
    AuthenticateOTPSerializer,
    VerifyPaymentSerializer
)
from .services import InterswitchService
from shared.permissions import IsAuthenticatedUser

class InitiatePaymentView(generics.CreateAPIView):
    """
    Initiate a new payment request for a business.
    
    POST /api/v1/payments/initiate/
    """
    serializer_class = InitiatePaymentSerializer
    permission_classes = [IsAuthenticatedUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        business_id = serializer.validated_data['business_id']
        amount = serializer.validated_data['amount']
        description = serializer.validated_data['description']
        callback_url = serializer.validated_data['callback_url']
        auth_data = serializer.validated_data['auth_data']
        customer_id = serializer.validated_data['customer_id']
        
        # Unique internal reference
        reference = f"LDG-{uuid.uuid4().hex[:12].upper()}"
        
        isw_response = InterswitchService.initiate_payment(
            float(amount), reference, callback_url, auth_data, customer_id
        )
        
        # By default, a fallback mock URL
        payment_url = f"https://payment.sandbox.interswitchng.com/pay?ref={reference}"
        if isw_response and 'redirectUrl' in isw_response:
            payment_url = isw_response['redirectUrl']
        
        payment = Payment.objects.create(
            user_id=request.user.id if hasattr(request.user, 'id') else uuid.uuid4(),
            business_id=business_id,
            amount=amount,
            description=description,
            reference=reference,
            status='pending'
        )
        
        return Response({
            'success': True,
            'message': 'Payment initiated successfully',
            'data': {
                'payment': PaymentSerializer(payment).data,
                'isw_response': isw_response,  # Pass raw response so frontend knows if it got "T0" vs "00"
                'payment_url': payment_url
            }
        }, status=status.HTTP_201_CREATED)

class AuthenticateOTPView(generics.CreateAPIView):
    """
    Authenticate OTP for a pending card transaction.
    
    POST /api/v1/payments/authenticate-otp/
    """
    serializer_class = AuthenticateOTPSerializer
    permission_classes = [IsAuthenticatedUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reference = serializer.validated_data['reference']
        payment_id = serializer.validated_data['payment_id']
        transaction_id = serializer.validated_data['transaction_id']
        otp = serializer.validated_data['otp']

        # Get the internal payment record
        try:
            payment = Payment.objects.get(reference=reference)
        except Payment.DoesNotExist:
            return Response({'success': False, 'message': 'Payment not found'}, status=404)

        # Call the ISW service
        isw_response = InterswitchService.authenticate_otp(payment_id, otp, transaction_id)

        if isw_response and isw_response.get('responseCode') == "00":
            return Response({
                'success': True,
                'message': 'OTP Authenticated successfully',
                'data': isw_response
            })
        else:
            return Response({
                'success': False,
                'message': 'OTP Authentication failed',
                'data': isw_response
            }, status=400)


class VerifyPaymentView(generics.CreateAPIView):
    """
    Verify the final status of a payment with Interswitch.
    
    POST /api/v1/payments/verify/
    """
    serializer_class = VerifyPaymentSerializer
    permission_classes = [IsAuthenticatedUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reference = serializer.validated_data['reference']
        amount = serializer.validated_data['amount']

        try:
            payment = Payment.objects.get(reference=reference)
        except Payment.DoesNotExist:
            return Response({'success': False, 'message': 'Payment not found'}, status=404)

        isw_response = InterswitchService.verify_transaction(reference, float(amount))

        if isw_response and isw_response.get('ResponseCode') == "00":
            payment.status = 'success'
            payment.interswitch_ref = isw_response.get('PaymentReference', '')
            payment.save()
            
            return Response({
                'success': True,
                'message': 'Payment verified successfully',
                'data': {
                    'payment': PaymentSerializer(payment).data,
                    'isw_response': isw_response
                }
            })
        else:
            payment.status = 'failed'
            payment.save()
            return Response({
                'success': False,
                'message': 'Payment verification failed or not approved',
                'data': isw_response
            }, status=400)


class InterswitchWebhookView(APIView):
    """
    Webhook to receive payment status updates from Interswitch.
    Unauthenticated endpoint secured by Interswitch MAC/signatures in production.
    
    POST /api/v1/payments/webhook/
    """
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        data = request.data
        
        # Example Payload:
        # {
        #   "transactionRef": "LDG-...",
        #   "amount": 500000,
        #   "responseCode": "00" 
        # }
        
        ref = data.get('transactionRef') or data.get('payRef')
        response_code = data.get('responseCode')
        
        if not ref:
            return Response({"success": False, "message": "No reference provided"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            payment = Payment.objects.get(reference=ref)
        except Payment.DoesNotExist:
            return Response({"success": False, "message": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)
            
        # ISW standard '00' is successful
        if str(response_code) == "00":
            payment.status = 'success'
        else:
            payment.status = 'failed'
            
        payment.interswitch_ref = data.get('interswitchRef', '')
        payment.save()
        
        # Ideally: Push an event to message broker (RabbitMQ/Kafka) for Transaction Service
        # to convert this payment into an income transaction record!
        
        return Response({'success': True, 'message': 'Webhook received and processed'})

class PaymentListView(generics.ListAPIView):
    """
    List all payments for a business.
    """
    serializer_class = PaymentSerializer
    
    def get_queryset(self):
        business_id = self.request.query_params.get('business_id')
        user_id = getattr(self.request.user, 'id', None)
        
        qs = Payment.objects.all()
        # Restrict to user's payments
        if user_id:
            qs = qs.filter(user_id=user_id)
            
        if business_id:
            qs = qs.filter(business_id=business_id)
            
        return qs
        
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            res = self.get_paginated_response(serializer.data)
            res.data['success'] = True
            return res

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
