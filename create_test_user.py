from django.contrib.auth.models import User
from apps.users.models import UserProfile

username = 'logintest'
email = 'logintest@test.com'
password = 'TestPass123!'

user, created = User.objects.get_or_create(username=username, defaults={'email': email})
if created or not user.check_password(password):
    user.set_password(password)
    user.save()

profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'year_of_study': 3})

print(f'User: {username}')
print(f'Password: {password}')
print(f'Email: {email}')
print(f'Created: {created}')
