"""
Category model for transaction categorization.
"""
import uuid
from django.db import models


class Category(models.Model):
    """
    Category for transactions.
    Can be system-default or user-created.
    """
    TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('both', 'Both'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='expense')
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    business_id = models.UUIDField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categories'
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return f"{self.name} ({self.type})"
