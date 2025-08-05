from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class UserProfile(models.Model):
    PROGRAM_CHOICES = [
        ('MECHANICAL', 'BSc. Mechanical Engineering'),
        ('ELECTRICAL', 'BSc. Electrical Engineering'),
        ('CIVIL', 'BSc. Civil Engineering'),
        ('TEXTILE_DESIGN', 'BSc. Textile Design'),
        ('TEXTILE_ENGINEERING', 'BSc. Textile Engineering'),
        ('INDUSTRIAL', 'BSc. Industrial Engineering'),
        ('GEOMATIC', 'BSc. Geomatic Engineering'),
        ('CHEMICAL', 'BSc. Chemical Engineering'),
        ('ARCHITECTURE', 'Bachelor of Architecture'),
        ('QUANTITY_SURVEYING', 'Bachelor of Science in Quantity Surveying'),
    ]
    
    PT_PHASE_CHOICES = [
        ('PT1', 'Practical Training 1'),
        ('PT2', 'Practical Training 2'),
        ('PT3', 'Practical Training 3'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    student_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    program = models.CharField(max_length=20, choices=PROGRAM_CHOICES, blank=True, null=True)
    year_of_study = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(4)], blank=True, null=True)
    pt_phase = models.CharField(max_length=3, choices=PT_PHASE_CHOICES, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    supervisor_name = models.CharField(max_length=100, blank=True, null=True)
    supervisor_email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True)
    company_name = models.CharField(max_length=200, blank=True, null=True)
    company_region = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.student_id or 'No ID'}"
    
    def get_program_display(self):
        return dict(self.PROGRAM_CHOICES).get(self.program, self.program)
    
    def get_pt_phase_display(self):
        return dict(self.PT_PHASE_CHOICES).get(self.pt_phase, self.pt_phase) 