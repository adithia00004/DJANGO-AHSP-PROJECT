"""WP-B5 inc-B5b — Single canonical project-identity provider for ALL exports.

Before this, identity was read ad-hoc in several places with WRONG field names
(e.g. ``lokasi`` / ``tahun_anggaran``) that silently fell back to ``'-'`` — so
exports showed location & year as ``'-'``. This is the one place that maps to the
REAL Dashboard ``Project`` fields; every exporter/adapter must source identity
here (B-5: project identity from Dashboard).
"""
from __future__ import annotations


def get_project_identity(project) -> dict:
    """Return canonical identity built from the real Dashboard Project fields."""
    def _s(attr, default="-"):
        val = getattr(project, attr, None)
        return val if (val is not None and val != "") else default

    tahun = getattr(project, "tahun_project", None)
    return {
        "name": _s("nama"),
        "code": _s("index_project", ""),
        "location": _s("lokasi_project"),
        "year": str(tahun) if tahun else "-",
        "owner": _s("nama_client"),   # client / pemilik
        "client": _s("nama_client"),
        "sumber_dana": _s("sumber_dana"),
        "anggaran_owner": getattr(project, "anggaran_owner", None),
        "ket_project1": _s("ket_project1", ""),
        "ket_project2": _s("ket_project2", ""),
        "jabatan_client": _s("jabatan_client", ""),
        "instansi_client": _s("instansi_client", ""),
        "kontraktor": _s("nama_kontraktor", ""),
        "instansi_kontraktor": _s("instansi_kontraktor", ""),
        "konsultan_perencana": _s("nama_konsultan_perencana", ""),
        "instansi_konsultan_perencana": _s(
            "instansi_konsultan_perencana", ""
        ),
        "konsultan_pengawas": _s("nama_konsultan_pengawas", ""),
        "instansi_konsultan_pengawas": _s(
            "instansi_konsultan_pengawas", ""
        ),
        "tanggal_mulai": getattr(project, "tanggal_mulai", None),
        "tanggal_selesai": getattr(project, "tanggal_selesai", None),
    }
