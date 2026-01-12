"""
JSON Exporter for Jadwal Pekerjaan

Exports pekerjaan structure and progress data as JSON for import/export functionality.
"""

import json
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Any, Optional

from django.db.models import QuerySet

from detail_project.models import (
    Project, 
    Pekerjaan, 
    VolumePekerjaan,
    PekerjaanProgressWeekly,
    TahapPelaksanaan
)


class JSONExporter:
    """Export project data as JSON for import/export functionality."""

    VERSION = "1.0"

    def __init__(self, config_or_project):
        """
        Initialize JSONExporter.

        Args:
            config_or_project: Either ExportConfig object (from ExportManager)
                             or Project instance (legacy usage)
        """
        # Support both ExportConfig (new) and Project (legacy)
        from ..export_config import ExportConfig
        if isinstance(config_or_project, ExportConfig):
            # ExportConfig object - extract project_name for filename
            self.project = None
            self.project_name = config_or_project.project_name
            self.config = config_or_project
        else:
            # Direct Project instance
            self.project = config_or_project
            self.project_name = config_or_project.nama
            self.config = None
    
    def export(self, data: Dict[str, Any]):
        """
        Generic export method called by ExportManager.

        Args:
            data: Export data dict with 'pages' or direct content

        Returns:
            HttpResponse with JSON content
        """
        from django.http import HttpResponse
        import json

        # Convert data to JSON string
        json_string = json.dumps(data, indent=2, ensure_ascii=False, default=self._json_serializer)

        # Create filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.project_name}_{timestamp}.json"

        # Create response
        response = HttpResponse(json_string, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    def export_jadwal_pekerjaan(self) -> Dict[str, Any]:
        """
        Export Jadwal Pekerjaan data as JSON.

        Returns:
            Dict containing pekerjaan structure and progress data
        """
        return {
            "version": self.VERSION,
            "export_type": "jadwal_pekerjaan",
            "exported_at": datetime.now().isoformat(),
            "project_id": self.project.id,
            "pekerjaan": self._export_pekerjaan(),
            "progress": self._export_progress(),
        }
    
    def _export_pekerjaan(self) -> List[Dict[str, Any]]:
        """Export all pekerjaan with hierarchy."""
        pekerjaan_list = []
        
        # Get all pekerjaan for this project
        pekerjaan_qs = Pekerjaan.objects.filter(
            project=self.project
        ).select_related('parent').order_by('order', 'id')
        
        # Get volume data
        volume_map = {}
        for vol in VolumePekerjaan.objects.filter(pekerjaan__project=self.project):
            volume_map[vol.pekerjaan_id] = {
                'quantity': float(vol.quantity) if vol.quantity else 0,
                'unit': vol.unit or ''
            }
        
        for pek in pekerjaan_qs:
            item = {
                "id": pek.id,
                "parent_id": pek.parent_id,
                "type": self._get_pekerjaan_type(pek),
                "kode": pek.kode or "",
                "uraian": pek.uraian_pekerjaan or "",
                "level": self._get_level(pek),
                "order": pek.order or 0,
            }
            
            # Add volume/satuan/harga for pekerjaan type
            if item["type"] == "pekerjaan":
                vol_data = volume_map.get(pek.id, {})
                item["volume"] = vol_data.get('quantity', 0)
                item["satuan"] = vol_data.get('unit', '')
                item["harga_satuan"] = float(pek.harga_satuan) if pek.harga_satuan else 0
            
            pekerjaan_list.append(item)
        
        return pekerjaan_list
    
    def _export_progress(self) -> List[Dict[str, Any]]:
        """Export all progress data (planned and actual)."""
        progress_list = []
        
        # Get all progress records
        progress_qs = PekerjaanProgressWeekly.objects.filter(
            project=self.project
        ).order_by('pekerjaan_id', 'week_number')
        
        for prog in progress_qs:
            # Only include if there's actual data
            planned = float(prog.progress_proportion) if prog.progress_proportion else 0
            actual = float(prog.actual_proportion) if prog.actual_proportion else 0
            
            if planned > 0 or actual > 0:
                progress_list.append({
                    "pekerjaan_id": prog.pekerjaan_id,
                    "week": prog.week_number,
                    "planned": round(planned, 2),
                    "actual": round(actual, 2),
                })
        
        return progress_list
    
    def _get_pekerjaan_type(self, pek: Pekerjaan) -> str:
        """Determine pekerjaan type based on hierarchy."""
        # Check if has children
        has_children = Pekerjaan.objects.filter(parent=pek).exists()
        
        if has_children:
            # Check level
            if pek.parent_id is None:
                return "klasifikasi"
            else:
                return "sub_klasifikasi"
        else:
            return "pekerjaan"
    
    def _get_level(self, pek: Pekerjaan) -> int:
        """Get hierarchy level (0-based)."""
        level = 0
        current = pek
        while current.parent_id:
            level += 1
            current = current.parent
            if level > 10:  # Safety limit
                break
        return level
    
    def to_json_string(self, indent: int = 2) -> str:
        """Export as formatted JSON string."""
        data = self.export_jadwal_pekerjaan()
        return json.dumps(data, indent=indent, ensure_ascii=False, default=self._json_serializer)
    
    def _json_serializer(self, obj):
        """Handle non-serializable types."""
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def export_jadwal_pekerjaan_json(project: Project) -> Dict[str, Any]:
    """
    Convenience function to export jadwal pekerjaan as JSON dict.
    
    Args:
        project: Project instance
        
    Returns:
        Dict with export data
    """
    exporter = JSONExporter(project)
    return exporter.export_jadwal_pekerjaan()
