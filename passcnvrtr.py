from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import get_hasher

User = get_user_model()  # get any custom user model

hasher = get_hasher('phpass')

# you got this from i.e. a WordPress database:
raw_hashes = {
    'dev1': '$P$BVPljbYAHYW5F42FOwzDCgtGjuS2ut1',
}

for username, hash in raw_hashes.items():
    user = User.objects.create(username=username)
    user.password = hasher.from_orig(hash)
    user.save()

