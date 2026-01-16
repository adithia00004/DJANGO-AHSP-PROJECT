import pytest
from django.conf import settings
from django.urls import reverse

from detail_project.models import Pekerjaan


@pytest.mark.django_db
def test_template_ahsp_requires_login(client, project):
    url = reverse("detail_project:template_ahsp", args=[project.id])

    response = client.get(url)

    assert response.status_code == 302
    assert settings.LOGIN_URL in response["Location"]


@pytest.mark.django_db
def test_template_ahsp_404_for_non_owner(client, other_user, project):
    client.force_login(other_user)
    url = reverse("detail_project:template_ahsp", args=[project.id])

    response = client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
def test_template_ahsp_context_lists_all_source_types(
    client,
    user,
    project,
    sub_klas,
    ahsp_ref,
):
    client.force_login(user)
    # Custom pekerjaan fixture ensures at least one row in context
    custom = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="C-001",
        snapshot_uraian="Custom Job",
        snapshot_satuan="ls",
        ordering_index=1,
    )
    ref_job = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_REF,
        ref=ahsp_ref,
        snapshot_kode="R-001",
        snapshot_uraian="Ref Job",
        snapshot_satuan=ahsp_ref.satuan,
        ordering_index=2,
    )
    ref_mod = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_REF_MOD,
        ref=ahsp_ref,
        snapshot_kode="RM-001",
        snapshot_uraian="Modified Ref",
        snapshot_satuan=ahsp_ref.satuan,
        ordering_index=3,
    )

    url = reverse("detail_project:template_ahsp", args=[project.id])
    response = client.get(url)

    assert response.status_code == 200
    ctx = response.context
    assert ctx["project"] == project
    assert ctx["side_active"] == "template_ahsp"
    # change_status created on demand and should belong to the same project
    assert getattr(ctx["change_status"], "project", None) == project

    jobs = list(ctx["pekerjaan"])
    assert len(jobs) == 3
    assert {job.id for job in jobs} == {custom.id, ref_job.id, ref_mod.id}
    assert ctx["count_custom"] == 1
    assert ctx["count_ref"] == 1
    assert ctx["count_mod"] == 1

    template_names = [tmpl.name for tmpl in response.templates if tmpl.name]
    assert "detail_project/template_ahsp.html" in template_names
