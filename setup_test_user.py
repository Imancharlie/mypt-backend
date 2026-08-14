import django
django.setup()

from django.contrib.auth.models import User
from apps.users.models import UserProfile

username = 'logintest'
email = 'logintest@test.com'
password = 'TestPass123!'

user, created = User.objects.get_or_create(username=username, defaults={'email': email})
user.set_password(password)
user.save()

profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'year_of_study': 3})

print(f'user={username}')
print(f'pass={password}')
