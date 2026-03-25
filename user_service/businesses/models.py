"""
Business model for LedgerMind.
A user can own multiple businesses.
"""
import uuid
from django.db import models
from django.conf import settings


class Business(models.Model):
    """
    Business profile owned by a user.
    Each user can have multiple businesses.
    """
    INDUSTRY_CHOICES = [
        ('retail', 'Retail'),
        ('technology', 'Technology'),
        ('food_beverage', 'Food & Beverage'),
        ('healthcare', 'Healthcare'),
        ('education', 'Education'),
        ('finance', 'Finance'),
        ('construction', 'Construction'),
        ('agriculture', 'Agriculture'),
        ('logistics', 'Logistics'),
        ('entertainment', 'Entertainment'),
        ('real_estate', 'Real Estate'),
        ('consulting', 'Consulting'),
        ('freelance', 'Freelance'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='businesses',
    )
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES, default='other')
    description = models.TextField(blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'businesses'
        ordering = ['-created_at']
        verbose_name_plural = 'businesses'

    def __str__(self):
        return f"{self.name} ({self.owner.email})"
