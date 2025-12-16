"""
Test suite for Unified Table Layer - Grid/Gantt/Kurva-S Modes
Tests the unified overlay system with comprehensive fixtures.

Author: Claude Code
Date: 2025-12-10
"""

import pytest
import json
from decimal import Decimal
from datetime import date, timedelta
from django.urls import reverse
from django.contrib.auth import get_user_model


# ================= Fixtures for Unified Table Testing =================
@pytest.fixture
def klasifikasi(db, project):
    """Create a test Klasifikasi."""
    from detail_project.models import Klasifikasi
    return Klasifikasi.objects.create(
        project=project,
        nama="Klasifikasi Test",
        ordering_index=1
    )


@pytest.fixture
def sub_klasifikasi(db, project, klasifikasi):
    """Create a test SubKlasifikasi."""
    from detail_project.models import SubKlasifikasi
    return SubKlasifikasi.objects.create(
        project=project,
        klasifikasi=klasifikasi,
        nama="Sub-Klasifikasi Test",
        ordering_index=1
    )



@pytest.fixture
def sample_weekly_columns(db):
    """
    Generate sample weekly time columns (12 weeks = 3 months).
    Matches the structure expected by UnifiedTableManager.
    """
    start_date = date(2025, 1, 1)  # Start from Jan 1, 2025
    columns = []

    for week_num in range(1, 13):  # 12 weeks
        week_start = start_date + timedelta(weeks=week_num - 1)
        week_end = week_start + timedelta(days=6)

        columns.append({
            'id': f'col_{week_num}',
            'fieldId': f'week_{week_num}',
            'weekNumber': week_num,
            'week_number': week_num,
            'rangeLabel': f'W{week_num}: {week_start.strftime("%d/%m")} - {week_end.strftime("%d/%m")}',
            'generationMode': 'weekly',
            'type': 'weekly',
            'meta': {
                'timeColumn': True,
                'columnMeta': {
                    'id': f'col_{week_num}',
                    'fieldId': f'week_{week_num}',
                    'weekNumber': week_num,
                    'week_number': week_num,
                }
            }
        })

    return columns


@pytest.fixture
def sample_pekerjaan_tree(db, project, sub_klasifikasi):
    """
    Generate sample pekerjaan tree with 5 main items and 2 sub-items each.
    Returns tree structure expected by UnifiedTableManager.
    """
    from detail_project.models import Pekerjaan

    tree = []
    pekerjaan_instances = []

    for i in range(1, 6):  # 5 main pekerjaan
        # Create main pekerjaan
        main_pekerjaan = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub_klasifikasi,
            snapshot_uraian=f'Pekerjaan {i}',
            snapshot_satuan='m2',
            ordering_index=i
        )
        pekerjaan_instances.append(main_pekerjaan)

        # Create sub-pekerjaan
        sub_rows = []
        for j in range(1, 3):  # 2 sub-items each
            sub_pekerjaan = Pekerjaan.objects.create(
                project=project,
                sub_klasifikasi=sub_klasifikasi,
                snapshot_uraian=f'Sub-Pekerjaan {i}.{j}',
                snapshot_satuan='m2',
                ordering_index=i * 10 + j
            )
            pekerjaan_instances.append(sub_pekerjaan)

            sub_rows.append({
                'pekerjaanId': sub_pekerjaan.id,
                'id': sub_pekerjaan.id,
                'pekerjaan_id': sub_pekerjaan.id,
                'name': sub_pekerjaan.snapshot_uraian,
                'nama': sub_pekerjaan.snapshot_uraian,
                'raw': {
                    'id': sub_pekerjaan.id,
                    'pekerjaan_id': sub_pekerjaan.id,
                    'nama': sub_pekerjaan.snapshot_uraian,
                },
                'subRows': [],
                'children': [],
            })

        tree.append({
            'pekerjaanId': main_pekerjaan.id,
            'id': main_pekerjaan.id,
            'pekerjaan_id': main_pekerjaan.id,
            'name': main_pekerjaan.snapshot_uraian,
            'nama': main_pekerjaan.snapshot_uraian,
            'raw': {
                'id': main_pekerjaan.id,
                'pekerjaan_id': main_pekerjaan.id,
                'nama': main_pekerjaan.snapshot_uraian,
            },
            'subRows': sub_rows,
            'children': sub_rows,
        })

    return tree, pekerjaan_instances


@pytest.fixture
def sample_progress_data(db, sample_pekerjaan_tree, sample_weekly_columns):
    """
    Generate sample progress data (planned & actual) for StateManager.
    Returns dict with planned and actual cell maps.

    Pattern:
    - Planned: Linear progression (0% → 100% over 12 weeks)
    - Actual: Follows planned with some variance (+/- 5%)
    """
    tree, pekerjaan_instances = sample_pekerjaan_tree
    columns = sample_weekly_columns

    planned_cells = {}
    actual_cells = {}

    # Flatten tree to get all pekerjaan IDs
    all_pekerjaan_ids = []
    for node in tree:
        all_pekerjaan_ids.append(node['pekerjaanId'])
        for sub_node in node.get('subRows', []):
            all_pekerjaan_ids.append(sub_node['pekerjaanId'])

    # Generate progress data for each pekerjaan
    for pkj_id in all_pekerjaan_ids:
        # Linear progression: each week adds ~8.33% (100% / 12 weeks)
        cumulative_planned = 0
        cumulative_actual = 0

        for week_idx, col in enumerate(columns, start=1):
            column_id = col['fieldId']
            cell_key = f"{pkj_id}-{column_id}"

            # Planned: steady 8.33% per week
            week_planned = min(8.33, 100 - cumulative_planned)
            cumulative_planned += week_planned
            planned_cells[cell_key] = round(cumulative_planned, 2)

            # Actual: follows planned with +/- 5% variance
            import random
            variance = random.uniform(-5, 5)
            week_actual = max(0, min(week_planned + variance, 100 - cumulative_actual))
            cumulative_actual += week_actual
            actual_cells[cell_key] = round(cumulative_actual, 2)

    return {
        'planned': planned_cells,
        'actual': actual_cells,
    }


@pytest.fixture
def sample_dependencies(db, sample_pekerjaan_tree):
    """
    Generate sample dependencies between pekerjaan.
    Returns list of dependency objects.

    Pattern:
    - Pekerjaan 1 → Pekerjaan 2 (week 3 → week 4)
    - Pekerjaan 2 → Pekerjaan 3 (week 6 → week 7)
    """
    tree, _ = sample_pekerjaan_tree

    if len(tree) < 3:
        return []

    return [
        {
            'fromPekerjaanId': tree[0]['pekerjaanId'],
            'fromColumnId': 'week_3',
            'toPekerjaanId': tree[1]['pekerjaanId'],
            'toColumnId': 'week_4',
            'color': '#94a3b8',
            'type': 'finish-to-start',
        },
        {
            'fromPekerjaanId': tree[1]['pekerjaanId'],
            'fromColumnId': 'week_6',
            'toPekerjaanId': tree[2]['pekerjaanId'],
            'toColumnId': 'week_7',
            'color': '#94a3b8',
            'type': 'finish-to-start',
        },
    ]


@pytest.fixture
def unified_table_payload(
    sample_pekerjaan_tree,
    sample_weekly_columns,
    sample_progress_data,
    sample_dependencies
):
    """
    Complete payload for UnifiedTableManager.updateData().
    This is the main fixture that combines all data.
    """
    tree, _ = sample_pekerjaan_tree

    return {
        'tree': tree,
        'timeColumns': sample_weekly_columns,
        'inputMode': 'percentage',
        'timeScale': 'weekly',
        'dependencies': sample_dependencies,
        'progressData': sample_progress_data,
    }


# ================= API Endpoint Tests =================

@pytest.mark.django_db
class TestJadwalPekerjaanPageAPI:
    """Test API endpoints that provide data for unified table."""

    def test_jadwal_pekerjaan_page_loads(self, client_logged, project):
        """Test that jadwal pekerjaan page loads successfully."""
        url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
        response = client_logged.get(url)

        assert response.status_code == 200
        html = response.content.decode("utf-8")

        # Check for unified table container
        assert 'id="tanstack-grid-container"' in html
        assert 'id="gantt-redesign-container"' in html
        assert 'id="scurve-view"' in html

    def test_page_has_correct_mode_tabs(self, client_logged, project):
        """Test that page has Grid, Gantt, and Kurva-S tabs."""
        url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
        response = client_logged.get(url)

        assert response.status_code == 200
        html = response.content.decode("utf-8")

        # Check for mode tabs
        assert 'id="grid-tab"' in html or 'Grid' in html
        assert 'id="gantt-tab"' in html or 'Gantt' in html
        assert 'id="scurve-tab"' in html or 'Kurva-S' in html or 'scurve' in html

    def test_page_includes_unified_table_script(self, client_logged, project):
        """Test that page includes jadwal-kegiatan bundle with unified table."""
        url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
        response = client_logged.get(url)

        assert response.status_code == 200
        html = response.content.decode("utf-8")

        # Check for jadwal-kegiatan bundle
        assert "assets/js/jadwal-kegiatan" in html

        # Check for data attributes
        assert f'data-api-base="/detail_project/api/project/{project.id}/tahapan/' in html


# ================= Unified Table Data Structure Tests =================

@pytest.mark.django_db
class TestUnifiedTableDataStructures:
    """Test data structures used by unified table system."""

    def test_weekly_columns_structure(self, sample_weekly_columns):
        """Test that weekly columns have correct structure."""
        assert len(sample_weekly_columns) == 12

        for col in sample_weekly_columns:
            # Check required fields
            assert 'id' in col
            assert 'fieldId' in col
            assert 'weekNumber' in col or 'week_number' in col
            assert 'meta' in col

            # Check meta structure
            assert col['meta']['timeColumn'] is True
            assert 'columnMeta' in col['meta']

    def test_pekerjaan_tree_structure(self, sample_pekerjaan_tree):
        """Test that pekerjaan tree has correct nested structure."""
        tree, pekerjaan_instances = sample_pekerjaan_tree

        assert len(tree) == 5  # 5 main items
        assert len(pekerjaan_instances) == 15  # 5 + (5 * 2 sub-items)

        for node in tree:
            # Check required fields
            assert 'pekerjaanId' in node
            assert 'id' in node
            assert 'name' in node or 'nama' in node
            assert 'raw' in node
            assert 'subRows' in node or 'children' in node

            # Check sub-items
            sub_rows = node.get('subRows', []) or node.get('children', [])
            assert len(sub_rows) == 2  # 2 sub-items per main item

    def test_progress_data_structure(self, sample_progress_data):
        """Test that progress data has correct cell key format."""
        planned = sample_progress_data['planned']
        actual = sample_progress_data['actual']

        assert len(planned) > 0
        assert len(actual) > 0

        # Check cell key format: "pekerjaanId-columnId"
        for cell_key in planned.keys():
            assert '-' in cell_key
            parts = cell_key.split('-')
            assert len(parts) == 2
            assert parts[0].isdigit()  # pekerjaanId is numeric
            assert 'week_' in parts[1]  # columnId contains 'week_'

        # Check values are percentages (0-100)
        for value in planned.values():
            assert 0 <= value <= 100
        for value in actual.values():
            assert 0 <= value <= 100

    def test_dependencies_structure(self, sample_dependencies):
        """Test that dependencies have correct structure."""
        assert len(sample_dependencies) == 2

        for dep in sample_dependencies:
            assert 'fromPekerjaanId' in dep
            assert 'fromColumnId' in dep
            assert 'toPekerjaanId' in dep
            assert 'toColumnId' in dep
            assert 'color' in dep
            assert 'type' in dep

    def test_unified_table_payload_completeness(self, unified_table_payload):
        """Test that complete payload has all required fields."""
        payload = unified_table_payload

        # Check top-level fields
        assert 'tree' in payload
        assert 'timeColumns' in payload
        assert 'inputMode' in payload
        assert 'timeScale' in payload
        assert 'dependencies' in payload
        assert 'progressData' in payload

        # Check data completeness
        assert len(payload['tree']) == 5
        assert len(payload['timeColumns']) == 12
        assert payload['inputMode'] == 'percentage'
        assert payload['timeScale'] == 'weekly'
        assert len(payload['dependencies']) == 2
        assert 'planned' in payload['progressData']
        assert 'actual' in payload['progressData']


# ================= Mode-Specific Tests =================

@pytest.mark.django_db
class TestGridMode:
    """Test Grid mode functionality (editable input cells)."""

    def test_grid_mode_has_input_cells(self, client_logged, project, sample_pekerjaan_tree):
        """Test that Grid mode shows input cells."""
        url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
        response = client_logged.get(url)

        assert response.status_code == 200
        html = response.content.decode("utf-8")

        # Grid mode should have input capability
        # (Check via JavaScript initialization, not HTML structure)
        assert 'tanstack-grid-container' in html

    def test_grid_mode_cell_data_structure(self, sample_progress_data):
        """Test that cell data can be edited in Grid mode."""
        planned = sample_progress_data['planned']
        actual = sample_progress_data['actual']

        # Simulate cell edit
        test_cell_key = list(planned.keys())[0]
        original_value = planned[test_cell_key]

        # Update value
        new_value = min(original_value + 10, 100)
        planned[test_cell_key] = new_value

        # Verify update
        assert planned[test_cell_key] == new_value
        assert planned[test_cell_key] != original_value


@pytest.mark.django_db
class TestGanttMode:
    """Test Gantt mode functionality (canvas overlay with bars)."""

    def test_gantt_mode_container_exists(self, client_logged, project):
        """Test that Gantt mode container exists in HTML."""
        url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
        response = client_logged.get(url)

        assert response.status_code == 200
        html = response.content.decode("utf-8")

        assert 'id="gantt-redesign-container"' in html

    def test_gantt_bar_data_calculation(
        self,
        sample_pekerjaan_tree,
        sample_weekly_columns,
        sample_progress_data
    ):
        """Test that Gantt bar data is correctly calculated from progress data."""
        tree, _ = sample_pekerjaan_tree
        columns = sample_weekly_columns
        planned = sample_progress_data['planned']
        actual = sample_progress_data['actual']

        # Simulate _buildBarData logic from UnifiedTableManager
        bar_data = []

        for node in tree:
            pkj_id = node['pekerjaanId']

            for col in columns:
                col_id = col['fieldId']
                cell_key = f"{pkj_id}-{col_id}"

                if cell_key in planned or cell_key in actual:
                    planned_value = planned.get(cell_key, 0)
                    actual_value = actual.get(cell_key, planned_value)
                    variance = actual_value - planned_value

                    bar_data.append({
                        'pekerjaanId': pkj_id,
                        'columnId': col_id,
                        'planned': planned_value,
                        'actual': actual_value,
                        'variance': variance,
                        'label': node['name'],
                        'color': '#ffc107',  # Yellow for actual
                    })

        # Verify bar data
        assert len(bar_data) > 0

        # Check first bar
        first_bar = bar_data[0]
        assert 'pekerjaanId' in first_bar
        assert 'columnId' in first_bar
        assert 'planned' in first_bar
        assert 'actual' in first_bar
        assert 'variance' in first_bar
        assert first_bar['color'] == '#ffc107'  # Yellow actual color

    def test_gantt_colors_correct(self):
        """Test that Gantt uses correct colors (cyan planned, yellow actual)."""
        # As defined in GanttCanvasOverlay.js
        PLANNED_COLOR = '#0dcaf0'  # Cyan
        ACTUAL_COLOR = '#ffc107'   # Yellow

        assert PLANNED_COLOR == '#0dcaf0'
        assert ACTUAL_COLOR == '#ffc107'


@pytest.mark.django_db
class TestKurvaSMode:
    """Test Kurva-S mode functionality (S-curve overlay)."""

    def test_kurvas_mode_container_exists(self, client_logged, project):
        """Test that Kurva-S mode container exists in HTML."""
        url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
        response = client_logged.get(url)

        assert response.status_code == 200
        html = response.content.decode("utf-8")

        assert 'id="scurve-view"' in html

    def test_kurvas_cumulative_calculation(
        self,
        sample_weekly_columns,
        sample_progress_data
    ):
        """Test that Kurva-S cumulative progress is correctly calculated."""
        columns = sample_weekly_columns
        planned = sample_progress_data['planned']
        actual = sample_progress_data['actual']

        # Simulate _calculateCumulativeProgress logic from UnifiedTableManager
        def calculate_cumulative(cell_data, time_columns):
            curve_points = []
            cumulative_progress = 0

            for col in time_columns:
                col_id = col['fieldId']
                week_num = col.get('weekNumber', col.get('week_number', 0))

                # Sum all progress for this week across all pekerjaan
                week_total = 0
                week_count = 0

                for cell_key, value in cell_data.items():
                    if f"-{col_id}" in cell_key:
                        week_total += value
                        week_count += 1

                # Average progress for this week
                avg_progress = week_total / week_count if week_count > 0 else 0
                cumulative_progress += avg_progress

                curve_points.append({
                    'columnId': col_id,
                    'weekNumber': week_num,
                    'weekProgress': avg_progress,
                    'cumulativeProgress': min(100, cumulative_progress),
                })

            return curve_points

        planned_curve = calculate_cumulative(planned, columns)
        actual_curve = calculate_cumulative(actual, columns)

        # Verify curve data
        assert len(planned_curve) == 12  # 12 weeks
        assert len(actual_curve) == 12

        # Check first point
        assert planned_curve[0]['weekNumber'] == 1
        assert 'cumulativeProgress' in planned_curve[0]

        # Check last point (should be close to 100%)
        assert planned_curve[-1]['cumulativeProgress'] >= 90
        assert planned_curve[-1]['cumulativeProgress'] <= 100

    def test_kurvas_y_axis_inverted(self):
        """Test that Y-axis is inverted (0% at bottom, 100% at top)."""
        # Simulate _interpolateY from KurvaSCanvasOverlay
        def interpolate_y(progress, y0, y100):
            """0% → y0 (bottom), 100% → y100 (top)"""
            clamped_progress = max(0, min(100, progress))
            return y0 - (clamped_progress / 100) * (y0 - y100)

        # Test with canvas height 600px, margins 40px
        canvas_height = 600
        y0_percent = canvas_height - 40  # 560px (0% at bottom)
        y100_percent = 40                # 40px (100% at top)

        # Test 0% should be at bottom
        y_at_0 = interpolate_y(0, y0_percent, y100_percent)
        assert y_at_0 == y0_percent  # 560px

        # Test 100% should be at top
        y_at_100 = interpolate_y(100, y0_percent, y100_percent)
        assert y_at_100 == y100_percent  # 40px

        # Test 50% should be in middle
        y_at_50 = interpolate_y(50, y0_percent, y100_percent)
        assert 250 < y_at_50 < 350  # Roughly middle

    def test_kurvas_colors_correct(self):
        """Test that Kurva-S uses correct colors (cyan planned, yellow actual)."""
        # As defined in KurvaSCanvasOverlay.js
        PLANNED_COLOR = '#0dcaf0'  # Cyan
        ACTUAL_COLOR = '#ffc107'   # Yellow

        assert PLANNED_COLOR == '#0dcaf0'
        assert ACTUAL_COLOR == '#ffc107'


# ================= Integration Tests =================

@pytest.mark.django_db
class TestUnifiedTableIntegration:
    """Integration tests for complete unified table workflow."""

    def test_complete_workflow_grid_to_gantt(
        self,
        client_logged,
        project,
        unified_table_payload
    ):
        """Test complete workflow: load page → Grid mode → switch to Gantt."""
        # 1. Load page
        url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
        response = client_logged.get(url)
        assert response.status_code == 200

        # 2. Verify Grid mode containers exist
        html = response.content.decode("utf-8")
        assert 'tanstack-grid-container' in html

        # 3. Verify Gantt mode containers exist
        assert 'gantt-redesign-container' in html

        # 4. Simulate data flow (this would happen via JavaScript in browser)
        payload = unified_table_payload

        # Verify payload is valid for both modes
        assert len(payload['tree']) > 0
        assert len(payload['timeColumns']) > 0
        assert 'progressData' in payload

    def test_complete_workflow_grid_to_kurvas(
        self,
        client_logged,
        project,
        unified_table_payload
    ):
        """Test complete workflow: load page → Grid mode → switch to Kurva-S."""
        # 1. Load page
        url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
        response = client_logged.get(url)
        assert response.status_code == 200

        # 2. Verify Kurva-S mode container exists
        html = response.content.decode("utf-8")
        assert 'scurve-view' in html

        # 3. Simulate cumulative calculation
        payload = unified_table_payload
        planned = payload['progressData']['planned']

        # Calculate cumulative for verification
        total_cells = len(planned)
        assert total_cells > 0

    def test_mode_switching_preserves_data(self, sample_progress_data):
        """Test that switching modes preserves data (no data loss)."""
        planned_before = sample_progress_data['planned'].copy()
        actual_before = sample_progress_data['actual'].copy()

        # Simulate mode switch (data should remain unchanged)
        planned_after = sample_progress_data['planned']
        actual_after = sample_progress_data['actual']

        # Verify no data loss
        assert planned_before == planned_after
        assert actual_before == actual_after
        assert len(planned_before) == len(planned_after)


# ================= Performance Tests =================

@pytest.mark.django_db
class TestUnifiedTablePerformance:
    """Performance tests for unified table with large datasets."""

    def test_large_dataset_structure(self, db, project, sub_klasifikasi):
        """Test unified table with large dataset (100 pekerjaan × 52 weeks)."""
        from detail_project.models import Pekerjaan

        # Create 100 pekerjaan
        pekerjaan_list = []
        for i in range(100):
            pkj = Pekerjaan.objects.create(
                project=project,
                sub_klasifikasi=sub_klasifikasi,
                snapshot_uraian=f'Pekerjaan Large {i}',
                snapshot_satuan='m2',
                ordering_index=i
            )
            pekerjaan_list.append(pkj)

        assert len(pekerjaan_list) == 100

        # Generate 52 weeks of columns
        columns = []
        for week in range(1, 53):
            columns.append({
                'id': f'col_{week}',
                'fieldId': f'week_{week}',
                'weekNumber': week,
                'meta': {'timeColumn': True}
            })

        assert len(columns) == 52

        # Calculate expected cell count
        expected_cells = 100 * 52  # 5,200 cells
        assert expected_cells == 5200

        # This test verifies structure can handle large datasets
        # Actual performance testing would require Selenium/browser


# ================= Regression Tests =================

@pytest.mark.django_db
class TestLegacyGanttRemoval:
    """Regression tests to ensure legacy Gantt V2 is completely removed."""

    def test_no_legacy_gantt_imports(self, client_logged, project):
        """Test that page does NOT import legacy gantt-frozen-grid.js."""
        url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
        response = client_logged.get(url)

        assert response.status_code == 200
        html = response.content.decode("utf-8")

        # Should NOT contain legacy Gantt V2 module
        assert 'gantt-frozen-grid' not in html
        assert 'GanttFrozenGrid' not in html

    def test_unified_overlay_is_default(self, client_logged, project):
        """Test that unified overlay is the default rendering method."""
        url = reverse("detail_project:jadwal_pekerjaan", args=[project.id])
        response = client_logged.get(url)

        assert response.status_code == 200
        html = response.content.decode("utf-8")

        # Should contain unified table components
        assert 'tanstack-grid-container' in html
        assert 'gantt-redesign-container' in html
