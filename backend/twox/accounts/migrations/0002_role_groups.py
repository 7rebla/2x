"""Create the groups of the two roles "manage" and "read" (E-40).

The names are fixed here on purpose and not imported from ``roles.py``: a
migration must keep doing what it did when it was written.
"""

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

ROLE_GROUP_NAMES = ("manage", "read")


def create_role_groups(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    group = apps.get_model("auth", "Group")
    for name in ROLE_GROUP_NAMES:
        group.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    # Going back leaves the groups in place: removing them would silently
    # take the role from every account.
    operations = [
        migrations.RunPython(create_role_groups, migrations.RunPython.noop),
    ]
