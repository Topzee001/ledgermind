"""Payment models."""
import uuid
from django.db import models
from django.utils import timezone

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    business_id = models.UUIDField(db_index=True)
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    
    status = models.CharField(
        max_length=20, 
        choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed')],
        default='pending'
    )
    
    description = models.CharField(max_length=255)
    
    reference = models.CharField(max_length=100, unique=True)
    interswitch_ref = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} - {self.status}"
