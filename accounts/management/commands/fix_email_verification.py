"""
Management command to fix email verification for existing users.
Usage: python manage.py fix_email_verification
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress


class Command(BaseCommand):
    help = 'Fix email verification status for existing users (especially superusers)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--superusers-only',
            action='store_true',
            help='Only fix superusers',
        )
        parser.add_argument(
            '--all-users',
            action='store_true',
            help='Fix all users without verified email',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        
        if options['superusers_only']:
            users = User.objects.filter(is_superuser=True)
            self.stdout.write(f"Processing {users.count()} superusers...")
        elif options['all_users']:
            users = User.objects.all()
            self.stdout.write(f"Processing {users.count()} users...")
        else:
            # Default: fix superusers only
            users = User.objects.filter(is_superuser=True)
            self.stdout.write(f"Processing {users.count()} superusers (use --all-users for everyone)...")

        fixed_count = 0
        for user in users:
            if not user.email:
                self.stdout.write(self.style.WARNING(f"  Skipping {user.username}: no email"))
                continue
                
            email_obj, created = EmailAddress.objects.get_or_create(
                user=user,
                email=user.email,
                defaults={'verified': True, 'primary': True}
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created verified email for {user.username}"))
                fixed_count += 1
            elif not email_obj.verified:
                email_obj.verified = True
                email_obj.primary = True
                email_obj.save()
                self.stdout.write(self.style.SUCCESS(f"  Verified email for {user.username}"))
                fixed_count += 1
            else:
                self.stdout.write(f"  {user.username}: already verified")

        self.stdout.write(self.style.SUCCESS(f"\nDone! Fixed {fixed_count} users."))
