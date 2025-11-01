"""
Django Management Command: Generate Test Data for Performance Testing

Usage:
    python manage.py generate_test_data --size small
    python manage.py generate_test_data --size medium
    python manage.py generate_test_data --size large
    python manage.py generate_test_data --size xlarge
    python manage.py generate_test_data --custom 2000 50

Sizes:
    small:  50 pekerjaan, 10 tahapan
    medium: 500 pekerjaan, 30 tahapan
    large:  2000 pekerjaan, 52 tahapan (weekly for 1 year)
    xlarge: 5000 pekerjaan, 100 tahapan
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from detail_project.models import Project, Pekerjaan, TahapPelaksanaan, PekerjaanTahapan
from datetime import datetime, timedelta
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate test data for performance testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--size',
            type=str,
            choices=['small', 'medium', 'large', 'xlarge'],
            help='Predefined data size'
        )
        parser.add_argument(
            '--custom',
            nargs=2,
            type=int,
            metavar=('PEKERJAAN_COUNT', 'TAHAPAN_COUNT'),
            help='Custom number of pekerjaan and tahapan'
        )
        parser.add_argument(
            '--user',
            type=str,
            default='admin',
            help='Username of project owner (default: admin)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing test projects before generating'
        )

    def handle(self, *args, **options):
        # Determine size
        size_config = {
            'small': (50, 10),
            'medium': (500, 30),
            'large': (2000, 52),
            'xlarge': (5000, 100)
        }

        if options['size']:
            pekerjaan_count, tahapan_count = size_config[options['size']]
            size_name = options['size'].upper()
        elif options['custom']:
            pekerjaan_count, tahapan_count = options['custom']
            size_name = 'CUSTOM'
        else:
            raise CommandError('Please specify --size or --custom')

        # Get user
        try:
            user = User.objects.get(username=options['user'])
        except User.DoesNotExist:
            raise CommandError(f'User "{options["user"]}" not found')

        # Clear existing test projects
        if options['clear']:
            self.stdout.write('Clearing existing test projects...')
            Project.objects.filter(nama__startswith='[TEST]').delete()

        # Generate
        self.stdout.write(self.style.SUCCESS(
            f'\n=== Generating {size_name} Test Project ===\n'
        ))
        self.stdout.write(f'Pekerjaan: {pekerjaan_count}')
        self.stdout.write(f'Tahapan: {tahapan_count}')
        self.stdout.write(f'Owner: {user.username}\n')

        try:
            with transaction.atomic():
                project = self.create_project(user, size_name, pekerjaan_count, tahapan_count)
                self.stdout.write('✓ Project created')

                tahapan_list = self.create_tahapan(project, tahapan_count)
                self.stdout.write(f'✓ {len(tahapan_list)} Tahapan created')

                pekerjaan_list = self.create_pekerjaan(project, pekerjaan_count)
                self.stdout.write(f'✓ {len(pekerjaan_list)} Pekerjaan created')

                assignment_count = self.create_assignments(pekerjaan_list, tahapan_list)
                self.stdout.write(f'✓ {assignment_count} Assignments created')

            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Successfully created test project: {project.nama}'
            ))
            self.stdout.write(f'Project ID: {project.id}')
            self.stdout.write(f'URL: /detail-project/{project.id}/kelola-tahapan/')

        except Exception as e:
            raise CommandError(f'Failed to generate test data: {e}')

    def create_project(self, user, size_name, pekerjaan_count, tahapan_count):
        """Create test project"""
        now = datetime.now()
        project = Project.objects.create(
            nama=f'[TEST] Performance Test - {size_name} ({pekerjaan_count}P x {tahapan_count}T)',
            deskripsi=f'Auto-generated test project for performance benchmarking',
            user=user,
            tanggal_mulai=now.date(),
            tanggal_selesai=(now + timedelta(days=365)).date(),
            lokasi='Test Location',
            no_kontrak='TEST-001',
        )
        return project

    def create_tahapan(self, project, count):
        """Create tahapan (time periods)"""
        tahapan_list = []
        start_date = project.tanggal_mulai

        # Generate weekly tahapan
        days_per_tahap = max(7, 365 // count)

        for i in range(count):
            tahap_start = start_date + timedelta(days=i * days_per_tahap)
            tahap_end = tahap_start + timedelta(days=days_per_tahap - 1)

            # Don't exceed project end date
            if tahap_end > project.tanggal_selesai:
                tahap_end = project.tanggal_selesai

            tahapan = TahapPelaksanaan.objects.create(
                project=project,
                nama=f'Week {i + 1}: {tahap_start.strftime("%d %b")} - {tahap_end.strftime("%d %b")}',
                urutan=i + 1,
                deskripsi=f'Auto-generated tahapan {i + 1}',
                tanggal_mulai=tahap_start,
                tanggal_selesai=tahap_end,
                is_auto_generated=True,
                generation_mode='weekly'
            )
            tahapan_list.append(tahapan)

            if tahap_end >= project.tanggal_selesai:
                break

        return tahapan_list

    def create_pekerjaan(self, project, count):
        """Create pekerjaan (work items) with hierarchy"""
        pekerjaan_list = []

        # Create hierarchical structure
        # 10% = level 1 (main categories)
        # 30% = level 2 (sub-categories)
        # 60% = level 3 (leaf nodes - actual work items)

        level1_count = max(10, count // 10)
        level2_count = max(30, count * 3 // 10)
        level3_count = count - level1_count - level2_count

        categories = [
            'Pekerjaan Persiapan',
            'Pekerjaan Tanah',
            'Pekerjaan Struktur',
            'Pekerjaan Arsitektur',
            'Pekerjaan Mekanikal',
            'Pekerjaan Elektrikal',
            'Pekerjaan Plumbing',
            'Pekerjaan Finishing',
            'Pekerjaan Landscape',
            'Pekerjaan Lain-lain'
        ]

        sub_categories = [
            'Mobilisasi', 'Demobilisasi', 'Galian', 'Urugan', 'Pondasi',
            'Sloof', 'Kolom', 'Balok', 'Plat Lantai', 'Tangga', 'Dinding',
            'Plesteran', 'Acian', 'Pengecatan', 'Kusen', 'Pintu', 'Jendela',
            'Atap', 'Plafon', 'Keramik', 'Sanitary', 'Kabel', 'Lampu'
        ]

        units = ['m²', 'm³', 'm\'', 'unit', 'ls', 'kg', 'set', 'bh', 'titik']

        # Level 1 - Main categories
        for i in range(level1_count):
            cat_name = categories[i % len(categories)]
            pekerjaan = Pekerjaan.objects.create(
                project=project,
                kode_pekerjaan=f'{i + 1}',
                uraian=f'{cat_name} {i // len(categories) + 1}',
                satuan='',
                volume=0,
                is_parent=True,
                level=1,
                urutan=i + 1
            )
            pekerjaan_list.append(pekerjaan)

        # Level 2 - Sub-categories
        for i in range(level2_count):
            parent = random.choice(pekerjaan_list[:level1_count])
            sub_name = sub_categories[i % len(sub_categories)]

            pekerjaan = Pekerjaan.objects.create(
                project=project,
                parent=parent,
                kode_pekerjaan=f'{parent.kode_pekerjaan}.{i + 1}',
                uraian=f'{sub_name} {i // len(sub_categories) + 1}',
                satuan='',
                volume=0,
                is_parent=True,
                level=2,
                urutan=len(pekerjaan_list) + 1
            )
            pekerjaan_list.append(pekerjaan)

        # Level 3 - Leaf nodes (actual work)
        for i in range(level3_count):
            # Pick a random level 2 parent, or level 1 if no level 2 exists
            potential_parents = pekerjaan_list[level1_count:level1_count + level2_count]
            if not potential_parents:
                potential_parents = pekerjaan_list[:level1_count]

            parent = random.choice(potential_parents)
            unit = random.choice(units)
            volume = round(random.uniform(10, 1000), 2)

            pekerjaan = Pekerjaan.objects.create(
                project=project,
                parent=parent,
                kode_pekerjaan=f'{parent.kode_pekerjaan}.{i + 1}',
                uraian=f'Detail Work Item {i + 1}',
                satuan=unit,
                volume=volume,
                is_parent=False,
                level=3,
                urutan=len(pekerjaan_list) + 1
            )
            pekerjaan_list.append(pekerjaan)

        return pekerjaan_list

    def create_assignments(self, pekerjaan_list, tahapan_list):
        """Create pekerjaan-tahapan assignments (progress distribution)"""
        if not tahapan_list:
            return 0

        assignment_count = 0

        # Only assign to leaf nodes (non-parent pekerjaan)
        leaf_pekerjaan = [p for p in pekerjaan_list if not p.is_parent]

        for pekerjaan in leaf_pekerjaan:
            # Randomly distribute progress across 2-5 tahapan
            num_tahapan = random.randint(2, min(5, len(tahapan_list)))
            selected_tahapan = random.sample(tahapan_list, num_tahapan)

            # Generate random proportions that sum to 100%
            proportions = self.generate_random_proportions(num_tahapan)

            for tahapan, proportion in zip(selected_tahapan, proportions):
                PekerjaanTahapan.objects.create(
                    pekerjaan=pekerjaan,
                    tahapan=tahapan,
                    proporsi_volume=proportion
                )
                assignment_count += 1

        return assignment_count

    def generate_random_proportions(self, count):
        """Generate random numbers that sum to 100"""
        # Generate random splits
        splits = sorted([random.uniform(0, 100) for _ in range(count - 1)])
        splits = [0] + splits + [100]

        # Calculate proportions
        proportions = [splits[i + 1] - splits[i] for i in range(count)]

        # Round and adjust to ensure sum = 100
        proportions = [round(p, 2) for p in proportions]
        diff = 100 - sum(proportions)
        proportions[0] += diff  # Adjust first proportion

        return proportions
