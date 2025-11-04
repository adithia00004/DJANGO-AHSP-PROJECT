"""
Management command for Celery task administration.

PHASE 5: Celery Async Tasks

Provides commands to:
- List active/scheduled tasks
- Trigger tasks manually
- View task status
- Monitor task queue
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from referensi import tasks


class Command(BaseCommand):
    help = "Celery task administration and management"

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['list', 'run', 'status', 'test'],
            help='Action to perform'
        )

        parser.add_argument(
            '--task',
            type=str,
            help='Task name to run (for run action)'
        )

        parser.add_argument(
            '--args',
            type=str,
            nargs='+',
            help='Task arguments'
        )

    def handle(self, *args, **options):
        action = options['action']

        if action == 'list':
            self.list_tasks()
        elif action == 'run':
            self.run_task(options['task'], options.get('args', []))
        elif action == 'status':
            self.check_status()
        elif action == 'test':
            self.test_celery()
        else:
            raise CommandError(f"Unknown action: {action}")

    def list_tasks(self):
        """List all available Celery tasks."""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("📋 AVAILABLE CELERY TASKS"))
        self.stdout.write("="*60 + "\n")

        available_tasks = {
            'Import Tasks': [
                ('async_import_ahsp', 'Import AHSP from file asynchronously'),
            ],
            'Audit Tasks': [
                ('cleanup_audit_logs_task', 'Cleanup old audit logs'),
                ('generate_audit_summary_task', 'Generate audit statistics'),
                ('send_audit_alerts_task', 'Send email alerts for critical events'),
            ],
            'Cache Tasks': [
                ('cache_warmup_task', 'Warm up cache with common queries'),
                ('cleanup_stale_cache_task', 'Cleanup stale cache keys'),
            ],
            'Monitoring Tasks': [
                ('health_check_task', 'Perform system health check'),
            ],
        }

        for category, task_list in available_tasks.items():
            self.stdout.write(self.style.SUCCESS(f"\n{category}:"))
            for task_name, description in task_list:
                self.stdout.write(f"  • {task_name:30} - {description}")

        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.WARNING("\n📅 SCHEDULED TASKS (Celery Beat):"))
        self.stdout.write("="*60 + "\n")

        scheduled_tasks = [
            ('cleanup-audit-logs-daily', 'Daily at 3:00 AM', 'Cleanup old audit logs'),
            ('generate-audit-summary-hourly', 'Every hour at :00', 'Generate hourly statistics'),
            ('send-audit-alerts-hourly', 'Every hour at :15', 'Send security alerts'),
            ('cache-warmup-periodic', 'Every 6 hours', 'Warm up cache'),
            ('cleanup-stale-cache-daily', 'Daily at 2:00 AM', 'Cleanup stale cache'),
        ]

        for task_name, schedule, description in scheduled_tasks:
            self.stdout.write(f"  • {task_name:35} {schedule:20} - {description}")

        self.stdout.write("\n")

    def run_task(self, task_name, task_args):
        """Run a Celery task manually."""
        if not task_name:
            raise CommandError("Please specify --task NAME to run")

        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.WARNING(f"🚀 RUNNING TASK: {task_name}"))
        self.stdout.write("="*60 + "\n")

        # Map task names to task functions
        task_map = {
            'async_import_ahsp': tasks.async_import_ahsp,
            'cleanup_audit_logs_task': tasks.cleanup_audit_logs_task,
            'generate_audit_summary_task': tasks.generate_audit_summary_task,
            'send_audit_alerts_task': tasks.send_audit_alerts_task,
            'cache_warmup_task': tasks.cache_warmup_task,
            'cleanup_stale_cache_task': tasks.cleanup_stale_cache_task,
            'health_check_task': tasks.health_check_task,
        }

        if task_name not in task_map:
            raise CommandError(f"Unknown task: {task_name}")

        task_func = task_map[task_name]

        try:
            # Execute task asynchronously
            result = task_func.delay(*task_args)

            self.stdout.write(self.style.SUCCESS(f"✅ Task queued successfully!"))
            self.stdout.write(f"Task ID: {result.id}")
            self.stdout.write(f"Task Name: {task_name}")
            self.stdout.write(f"Status: {result.status}\n")

            # Wait for result (with timeout)
            self.stdout.write("Waiting for result... (max 60s)")

            try:
                task_result = result.get(timeout=60)
                self.stdout.write(self.style.SUCCESS("\n✅ Task completed successfully!"))
                self.stdout.write(f"Result: {task_result}\n")
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"\n❌ Task failed or timed out: {exc}\n"))

        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"❌ Failed to queue task: {exc}\n"))
            raise

    def check_status(self):
        """Check Celery worker and broker status."""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("📊 CELERY STATUS"))
        self.stdout.write("="*60 + "\n")

        try:
            from config.celery import app

            # Check broker connection
            self.stdout.write("Checking broker connection...", ending=" ")
            try:
                app.connection().ensure_connection(max_retries=3, timeout=5)
                self.stdout.write(self.style.SUCCESS("✅ Connected"))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"❌ Failed: {exc}"))
                return

            # Get active workers
            self.stdout.write("Checking active workers...", ending=" ")
            inspect = app.control.inspect()
            active_workers = inspect.active()

            if active_workers:
                self.stdout.write(self.style.SUCCESS(f"✅ {len(active_workers)} worker(s) active"))

                for worker_name, tasks_list in active_workers.items():
                    self.stdout.write(f"\n  Worker: {worker_name}")
                    if tasks_list:
                        self.stdout.write(f"  Active tasks: {len(tasks_list)}")
                        for task in tasks_list[:5]:  # Show first 5
                            self.stdout.write(f"    - {task['name']}")
                    else:
                        self.stdout.write("  No active tasks")
            else:
                self.stdout.write(self.style.WARNING("⚠️  No active workers"))

            # Get scheduled tasks
            self.stdout.write("\nChecking scheduled tasks...", ending=" ")
            scheduled = inspect.scheduled()

            if scheduled:
                total_scheduled = sum(len(tasks_list) for tasks_list in scheduled.values())
                self.stdout.write(self.style.SUCCESS(f"✅ {total_scheduled} task(s) scheduled"))
            else:
                self.stdout.write(self.style.WARNING("⚠️  No scheduled tasks"))

            # Get registered tasks
            self.stdout.write("\nChecking registered tasks...", ending=" ")
            registered = inspect.registered()

            if registered:
                total_registered = sum(len(tasks_list) for tasks_list in registered.values())
                self.stdout.write(self.style.SUCCESS(f"✅ {total_registered} task(s) registered\n"))
            else:
                self.stdout.write(self.style.WARNING("⚠️  No registered tasks\n"))

        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"\n❌ Error checking status: {exc}\n"))

    def test_celery(self):
        """Test Celery is working."""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("🧪 CELERY CONNECTIVITY TEST"))
        self.stdout.write("="*60 + "\n")

        try:
            from config.celery import app

            # Test 1: Broker connection
            self.stdout.write("Test 1: Broker Connection...", ending=" ")
            try:
                app.connection().ensure_connection(max_retries=3, timeout=5)
                self.stdout.write(self.style.SUCCESS("✅ PASSED"))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"❌ FAILED: {exc}"))
                return

            # Test 2: Simple task
            self.stdout.write("Test 2: Simple Task Execution...", ending=" ")
            try:
                result = app.send_task('config.celery.debug_task')
                result.get(timeout=10)
                self.stdout.write(self.style.SUCCESS("✅ PASSED"))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"❌ FAILED: {exc}"))
                return

            # Test 3: Health check task
            self.stdout.write("Test 3: Health Check Task...", ending=" ")
            try:
                result = tasks.health_check_task.delay()
                health = result.get(timeout=30)

                if health.get('status') in ['healthy', 'degraded']:
                    self.stdout.write(self.style.SUCCESS(f"✅ PASSED ({health['status']})"))
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️  WARNING: {health['status']}"))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"❌ FAILED: {exc}"))
                return

            self.stdout.write(self.style.SUCCESS("\n✅ All tests passed!"))
            self.stdout.write("Celery is working correctly.\n")

        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"\n❌ Error during testing: {exc}\n"))


# Example usage:
# python manage.py task_admin list
# python manage.py task_admin status
# python manage.py task_admin test
# python manage.py task_admin run --task health_check_task
# python manage.py task_admin run --task cache_warmup_task
# python manage.py task_admin run --task cleanup_audit_logs_task --args 90 180
