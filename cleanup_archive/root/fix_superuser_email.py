import os
import django
from django.conf import settings

# Setup Django environment manually if run directly
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local') # Adjust if needed
# django.setup()

from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

User = get_user_model()

def fix_superusers():
    print("--- Checking Internal Superusers Email Status ---")
    superusers = User.objects.filter(is_superuser=True)
    
    if not superusers.exists():
        print("No superusers found!")
        return

    for user in superusers:
        print(f"Processing user: {user.username} ({user.email})")
        
        # Cek apakah object EmailAddress ada
        email_record, created = EmailAddress.objects.get_or_create(
            user=user, 
            email=user.email,
            defaults={'verified': True, 'primary': True}
        )
        
        if created:
            print(f"  [CREATED] EmailAddress record created (Verified=True)")
        else:
            print(f"  [FOUND] Existing record. Verified status: {email_record.verified}")
            if not email_record.verified:
                email_record.verified = True
                email_record.save()
                print(f"  [UPDATED] Forced to Verified=True")
            else:
                print(f"  [OK] Already verified.")
                
        # Double check primary flag
        if not email_record.primary:
            email_record.primary = True
            email_record.save()
            print("  [UPDATED] Set as Primary email")
            
    print("--- Done ---")

if __name__ == '__main__':
    fix_superusers()
