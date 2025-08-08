from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserBalance


@receiver(post_save, sender=User)
def create_user_balance(sender, instance, created, **kwargs):
    """Create UserBalance when a new user is created."""
    if created:
        UserBalance.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_balance(sender, instance, **kwargs):
    """Save UserBalance when user is updated."""
    try:
        instance.balance.save()
    except UserBalance.DoesNotExist:
        UserBalance.objects.create(user=instance)
