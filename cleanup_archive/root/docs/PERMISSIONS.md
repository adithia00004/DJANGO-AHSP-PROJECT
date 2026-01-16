# Referensi App Permissions

## Overview

Phase 4 introduces granular permissions and predefined groups so access to the Referensi module can be delegated safely.

The following custom permissions are defined on `AHSPReferensi`:

- `referensi.view_ahsp_stats` – view the pre-computed statistics dashboard.
- `referensi.import_ahsp_data` – upload and commit AHSP data through the preview workflow.
- `referensi.export_ahsp_data` – download/export AHSP datasets.

All default Django model permissions (`view`, `add`, `change`, `delete`) remain available for the three core models: `AHSPReferensi`, `RincianReferensi`, and `KodeItemReferensi`.

### Built-in Groups

| Group | Intended Roles | Included Permissions |
|-------|----------------|----------------------|
| Referensi Viewer | Stakeholders who only consume data | - `view_*` on AHSP/Rincian/Kode Item<br>- `view_ahsp_stats` |
| Referensi Editor | Data stewards who curate AHSP entries | All Viewer permissions plus:<br>- `change_*` on AHSP/Rincian/Kode Item<br>- `import_ahsp_data` |
| Referensi Admin | Power users who administer the dataset | All Editor permissions plus:<br>- `add_*`/`delete_*` on all models<br>- `export_ahsp_data` |

Groups are provisioned automatically in migration `0015_create_permission_groups`. Re-running `python manage.py migrate referensi` will ensure the groups exist in all environments.

### Assigning Users to Groups

```
python manage.py shell

from django.contrib.auth.models import Group, User
user = User.objects.get(username="staff")
group = Group.objects.get(name="Referensi Editor")
user.groups.add(group)
```

Users can also be assigned via the Django admin UI under *Users → Groups*.

### View Access Matrix

| View | Required Permissions |
|------|----------------------|
| Referensi Admin Portal (`referensi:admin_portal`) | `view_ahspreferensi`, `change_ahspreferensi` |
| Referensi Database (`referensi:ahsp_database`) | `view_ahspreferensi`, `change_ahspreferensi` |
| Preview Import (`referensi:preview_import`) | `view_ahspreferensi`, `import_ahsp_data` |
| Commit Import (`referensi:commit_import`) | `import_ahsp_data` |

> ℹ️ Superusers continue to bypass permission checks, but staff users now require explicit group assignment.

### Auditing

All modifications to AHSP and Rincian records are tracked via **django-simple-history**. Administrators can review change logs directly from the Django admin using the “History” button on each object.

