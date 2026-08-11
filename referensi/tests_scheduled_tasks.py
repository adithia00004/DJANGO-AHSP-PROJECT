"""Guard: every task on the beat schedule must actually run.

`celery_beat` was misconfigured for months, so nothing in the `beat_schedule` of
`config/celery.py` was ever dispatched. That let broken code sit undetected in
`referensi/tasks.py`: it referenced `SecurityAuditLog.SEVERITY_HIGH` and
`SecurityAuditLog.EVENT_IMPORT`, neither of which exists on the model, and it
omitted the required `category` field. The moment beat started working, the
hourly alert task began failing with:

    AttributeError: type object 'SecurityAuditLog' has no attribute 'SEVERITY_HIGH'

Unit-testing each task's logic would not have caught that -- the failure was in
names resolved only when the code actually executes. So this executes them, and
it walks the schedule itself rather than a hand-copied list, which also catches
a schedule entry pointing at a task name that no longer exists.

Celery's registry is populated lazily, so the modules have to be imported before
anything is looked up; without that step both checks pass vacuously.
"""

from django.test import TestCase

from config.celery import app as celery_app


class ScheduledTasksExecuteTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Autodiscovery is lazy: without this the registry is empty and every
        # lookup below silently returns None.
        celery_app.loader.import_default_modules()

    def _schedule(self):
        return sorted(celery_app.conf.beat_schedule.items())

    def test_schedule_is_not_empty(self):
        self.assertGreater(
            len(self._schedule()),
            0,
            "beat_schedule is empty, so the checks below would pass vacuously.",
        )

    def test_every_scheduled_task_is_registered(self):
        missing = [
            entry["task"]
            for _, entry in self._schedule()
            if entry["task"] not in celery_app.tasks
        ]

        self.assertEqual(
            missing,
            [],
            f"beat_schedule references tasks that are not registered: {missing}. "
            "Beat would dispatch them and every one would be rejected.",
        )

    def test_every_scheduled_task_runs_without_error(self):
        failures = []
        for name, entry in self._schedule():
            task = celery_app.tasks.get(entry["task"])
            if task is None:
                failures.append(f"{name}: task {entry['task']} is not registered")
                continue
            try:
                task.apply(kwargs=entry.get("kwargs", {})).get()
            except Exception as exc:  # noqa: BLE001 - catching anything is the point
                failures.append(f"{name} ({entry['task']}): {type(exc).__name__}: {exc}")

        self.assertEqual(
            failures,
            [],
            "Scheduled tasks raised when executed:\n" + "\n".join(failures),
        )
