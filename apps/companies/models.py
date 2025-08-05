from django.db import models


class Company(models.Model):
    INDUSTRY_CHOICES = [
        ('MANUFACTURING', 'Manufacturing'),
        ('CONSTRUCTION', 'Construction'),
        ('TECHNOLOGY', 'Technology'),
        ('AUTOMOTIVE', 'Automotive'),
        ('ENERGY', 'Energy & Utilities'),
        ('TELECOMMUNICATIONS', 'Telecommunications'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=200, unique=True)
    address = models.TextField(blank=True, null=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    industry_type = models.CharField(max_length=20, choices=INDUSTRY_CHOICES, default='OTHER', blank=True, null=True)
    established_year = models.IntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'companies'
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_industry_display(self):
        return dict(self.INDUSTRY_CHOICES).get(self.industry_type, self.industry_type) 