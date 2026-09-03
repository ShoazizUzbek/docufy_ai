import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import Organization

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates the demo organization + admin user, and the MinIO bucket, for local dev.'

    def handle(self, *args, **options):
        org, created = Organization.objects.get_or_create(
            slug='demo-org', defaults={'name': 'Demo Organization'},
        )
        self.stdout.write(self.style.SUCCESS(
            f'{"Created" if created else "Found"} organization: {org.name}'
        ))

        email = 'admin@docufy.ai'
        password = 'ChangeMe123!'
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'organization': org,
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
            },
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {email} / {password}'))
        else:
            self.stdout.write(self.style.WARNING(f'Admin user already exists: {email}'))

        self._ensure_bucket()

    def _ensure_bucket(self):
        client = boto3.client(
            's3',
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        try:
            client.head_bucket(Bucket=bucket)
            self.stdout.write(self.style.WARNING(f'MinIO bucket already exists: {bucket}'))
        except ClientError:
            client.create_bucket(Bucket=bucket)
            self.stdout.write(self.style.SUCCESS(f'Created MinIO bucket: {bucket}'))
