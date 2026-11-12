from typing import TypeVar

from django.db.models import Model

from django_test_migrations.contrib.unittest_case import MigratorTestCase

M = TypeVar("M", bound=Model)


class ScrubLoggedTokensMigrationTest(MigratorTestCase):
    migrate_from = ("logging", "0001_initial")
    migrate_to = ("logging", "0002_remove_tokens_from_logs")

    def _token_in_log(self, model: type[M]) -> bool:
        return any(
            "token" in object_data.keys()
            for object_data in model.objects.values_list(
                "extra_data__object_data", flat=True
            )
        )

    def prepare(self):
        ContentType = self.old_state.apps.get_model("contenttypes", "ContentType")
        TimelineLogProxy = self.old_state.apps.get_model("logging", "TimelineLogProxy")

        application, _ = ContentType.objects.get_or_create(
            app_label="api", model="application"
        )
        TimelineLogProxy.objects.create(
            content_type=application,
            object_id="1",
            extra_data={"event": "create", "object_data": {"id": 1, "token": "secret"}},
        )
        TimelineLogProxy.objects.create(
            content_type=application,
            object_id="1",
            extra_data={"event": "update", "object_data": {"token": "updated"}},
        )

        publication, _ = ContentType.objects.get_or_create(
            app_label="publications", model="publication"
        )
        TimelineLogProxy.objects.create(
            content_type=application,
            object_id="1",
            extra_data={"event": "create", "object_data": {"token": "kept"}},
        )
        TimelineLogProxy.objects.create(
            content_type=application,
            object_id="1",
            extra_data={"event": "update", "object_data": {"token": "updated"}},
        )

        self.assertTrue(self._token_in_log(TimelineLogProxy))

    def test_only_application_tokens_are_removed(self):
        TimelineLogProxy = self.new_state.apps.get_model("logging", "TimelineLogProxy")

        self.assertFalse(self._token_in_log(TimelineLogProxy))
