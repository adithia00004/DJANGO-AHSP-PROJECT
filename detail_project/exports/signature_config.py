# =============================================================================
# FILE: detail_project/exports/signature_config.py
# =============================================================================
"""
SSOT (Single Source of Truth) for Signature Configuration

This module provides centralized configuration for:
1. SignaturePresets - Define all signature roles and preset combinations
2. SignatureLayoutRules - Rules for signature placement in documents

Usage:
    from .signature_config import SignaturePresets, SignatureLayoutRules
    
    # Get preset for perencanaan documents
    roles = SignaturePresets.PERENCANAAN
    
    # Check layout rules
    min_rows = SignatureLayoutRules.MIN_ROWS_WITH_SIGNATURE
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


# =============================================================================
# SIGNATURE PRESETS
# =============================================================================

class SignaturePresets:
    """
    SSOT: Define all available signature roles and preset combinations.
    
    Different documents require different signature combinations:
    - Perencanaan documents: Owner + Konsultan Perencana
    - Pelaksanaan documents: Owner + Kontraktor + Konsultan Pengawas
    """
    
    # =========================================================================
    # ALL AVAILABLE ROLES
    # =========================================================================
    # Each role has a label (display name) and field (project model attribute)
    # IMPORTANT: Field names MUST match dashboard.models.Project fields
    
    ALL_ROLES: Dict[str, Dict[str, str]] = {
        'owner': {
            'label': 'Pemilik Proyek',
            'field': 'nama_client',  # Project.nama_client ✓
        },
        'perencana': {
            'label': 'Konsultan Perencana',
            'field': 'nama_konsultan_perencana',  # Project.nama_konsultan_perencana ✓
        },
        'kontraktor': {
            'label': 'Kontraktor Pelaksana',
            'field': 'nama_kontraktor',  # Project.nama_kontraktor ✓
        },
        'pengawas': {
            'label': 'Konsultan Pengawas',
            'field': 'nama_konsultan_pengawas',  # Project.nama_konsultan_pengawas ✓
        },
    }
    
    # =========================================================================
    # PRESET COMBINATIONS
    # =========================================================================
    
    # Tahap Perencanaan: Rekap RAB, Rekap Kebutuhan, Volume, Harga Items, Rincian AHSP
    PERENCANAAN: List[str] = ['owner', 'perencana']
    
    # Tahap Pelaksanaan: Jadwal Pekerjaan, Laporan Progress
    PELAKSANAAN: List[str] = ['owner', 'kontraktor', 'pengawas']
    
    # Full signature (all 4 roles) - for special cases
    FULL: List[str] = ['owner', 'perencana', 'kontraktor', 'pengawas']
    
    # =========================================================================
    # DOCUMENT TYPE MAPPING
    # =========================================================================
    # Maps document/export type to appropriate preset
    
    DOCUMENT_PRESETS: Dict[str, str] = {
        # Perencanaan documents
        'rekap_rab': 'PERENCANAAN',
        'rekap_kebutuhan': 'PERENCANAAN',
        'volume_pekerjaan': 'PERENCANAAN',
        'harga_items': 'PERENCANAAN',
        'rincian_ahsp': 'PERENCANAAN',
        
        # Pelaksanaan documents
        'jadwal_pekerjaan': 'PELAKSANAAN',
        'jadwal_professional': 'PELAKSANAAN',
        'laporan_progress': 'PELAKSANAAN',
    }
    
    @classmethod
    def get_roles_for_document(cls, document_type: str) -> List[str]:
        """
        Get role list for a specific document type.
        
        Args:
            document_type: Document type key (e.g., 'rekap_rab', 'jadwal_pekerjaan')
            
        Returns:
            List of role keys for the document
        """
        preset_name = cls.DOCUMENT_PRESETS.get(document_type, 'PERENCANAAN')
        return getattr(cls, preset_name, cls.PERENCANAAN)
    
    @classmethod
    def get_roles_for_preset(cls, preset: str) -> List[str]:
        """
        Get role list for a specific preset name.
        
        Args:
            preset: Preset name ('PERENCANAAN', 'PELAKSANAAN', 'FULL')
            
        Returns:
            List of role keys for the preset
        """
        return getattr(cls, preset, cls.PERENCANAAN)
    
    @classmethod
    def build_signatures(cls, project, preset: str = 'PERENCANAAN') -> List[Dict[str, str]]:
        """
        Build signature list for a preset, filling in names from project.
        
        Args:
            project: Project model instance
            preset: Preset name
            
        Returns:
            List of signature dicts with 'label', 'name', 'position' keys
        """
        roles = cls.get_roles_for_preset(preset)
        signatures = []
        
        for role_key in roles:
            role = cls.ALL_ROLES.get(role_key, {})
            label = role.get('label', role_key.title())
            field = role.get('field', '')
            
            # Get name from project if field exists
            name = ''
            if field and project:
                name = getattr(project, field, '') or ''
            
            signatures.append({
                'label': label,
                'name': name,
                'position': '',  # Can be filled by user/adapter
            })
        
        return signatures


# =============================================================================
# SIGNATURE LAYOUT RULES
# =============================================================================

class SignatureLayoutRules:
    """
    SSOT: Rules for signature placement in exported documents.
    
    Key rule: Signature section MUST NOT appear alone on a page (orphan).
    It must always have at least MIN_ROWS_WITH_SIGNATURE content rows
    on the same page.
    
    Usage:
        from .signature_config import SignatureLayoutRules as SLR
        
        if remaining_rows <= SLR.MIN_ROWS_WITH_SIGNATURE:
            # Keep these rows with signature on same page
    """
    
    # =========================================================================
    # ANTI-ORPHAN RULES
    # =========================================================================
    
    # Minimum rows that MUST appear on the same page as signature
    MIN_ROWS_WITH_SIGNATURE: int = 3
    
    # Minimum vertical space (mm) required above signature block
    MIN_SPACE_ABOVE_SIGNATURE: float = 50.0  # ~2 inches
    
    # Estimated height (mm) of signature block (for 2-4 signature boxes)
    SIGNATURE_HEIGHT_ESTIMATE: float = 80.0
    
    # =========================================================================
    # SIGNATURE BOX DIMENSIONS
    # =========================================================================
    
    # Width of each signature box (mm)
    SIGNATURE_BOX_WIDTH: float = 60.0
    
    # Height of signature box (mm)
    SIGNATURE_BOX_HEIGHT: float = 40.0
    
    # Spacing between signature boxes (mm)
    SIGNATURE_BOX_SPACING: float = 10.0
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    @classmethod
    def calculate_signature_height(cls, num_signatures: int) -> float:
        """
        Calculate total height needed for signature section.
        
        Args:
            num_signatures: Number of signature boxes
            
        Returns:
            Height in mm
        """
        if num_signatures <= 0:
            return 0.0
        
        # Assume horizontal layout (side by side)
        # Add padding above and below
        return cls.SIGNATURE_BOX_HEIGHT + cls.MIN_SPACE_ABOVE_SIGNATURE
    
    @classmethod
    def should_keep_with_signature(
        cls,
        remaining_rows: int,
        available_space_mm: float,
        row_height_mm: float = 5.0,
        num_signatures: int = 2
    ) -> bool:
        """
        Determine if remaining rows should be kept on same page as signature.
        
        This implements the anti-orphan rule: if we're near the end of content
        and the signature would be orphaned on the next page, we should
        move the last few rows + signature together to the next page.
        
        Args:
            remaining_rows: Number of content rows still to render
            available_space_mm: Available vertical space on current page (mm)
            row_height_mm: Height of each row (mm)
            num_signatures: Number of signature boxes
            
        Returns:
            True if rows should be moved with signature to next page
        """
        if remaining_rows > cls.MIN_ROWS_WITH_SIGNATURE:
            return False  # Enough rows, no need to keep together
        
        # Calculate space needed for remaining rows + signature
        content_height = remaining_rows * row_height_mm
        signature_height = cls.calculate_signature_height(num_signatures)
        total_needed = content_height + signature_height
        
        # If everything fits, no action needed
        if available_space_mm >= total_needed:
            return False
        
        # If rows fit but signature doesn't, keep together
        if available_space_mm >= content_height and available_space_mm < total_needed:
            return True
        
        return False


# =============================================================================
# SHORTHAND ALIASES
# =============================================================================

SP = SignaturePresets
SLR = SignatureLayoutRules
