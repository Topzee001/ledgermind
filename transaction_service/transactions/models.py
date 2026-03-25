"""
Transaction model.
"""
import uuid
from django.db import models
from categories.models import Category


class Transaction(models.Model):
    """
    Financial transaction record.
    Linked to a business (by UUID from User Service) and a category.
    """
    TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    SOURCE_CHOICES = [
        ('manual', 'Manual Entry'),
        ('csv', 'CSV Upload'),
        ('api', 'API Import'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business_id = models.UUIDField(db_index=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField(blank=True)
    date = models.DateField()
    ai_categorized = models.BooleanField(default=False)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='manual')
    reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transactions'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.type}: {self.amount} - {self.description[:50]}"
