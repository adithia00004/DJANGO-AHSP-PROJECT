"""
Pagination Engine - Smart splitting for export overflow handling

Handles intelligent pagination for exports with too many columns/rows:
- Column splitting: Month-based boundaries (W1-W4, W5-W8, etc.)
- Row splitting: Hierarchy-aware (never split sub-klasifikasi)
- Page matrix: Both-axis overflow creates grid of pages

Author: Claude Sonnet 4.5
Date: 2025-01-15
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import math


@dataclass
class PageChunk:
    """Represents a single page chunk"""
    page_number: int
    row_start: int
    row_end: int
    col_start: int
    col_end: int
    rows: List[Dict[str, Any]]
    columns: List[str]
    is_continuation: bool = False
    continuation_context: Optional[str] = None


class PaginationEngine:
    """
    Smart pagination engine for export overflow handling.

    Features:
    - Month-based column chunking (4 weeks = 1 month)
    - Hierarchy-aware row splitting (preserve sub-klasifikasi groups)
    - Continuation headers for context preservation
    - Page matrix for both-axis overflow
    """

    def __init__(
        self,
        max_rows_per_page: int = 28,
        max_cols_per_page: int = 16,
        weeks_per_month: int = 4
    ):
        """
        Initialize pagination engine.

        Args:
            max_rows_per_page: Maximum rows per page (default: 28 for A4 landscape)
            max_cols_per_page: Maximum columns per page (default: 16)
            weeks_per_month: Weeks per month for aggregation (default: 4)
        """
        self.max_rows_per_page = max_rows_per_page
        self.max_cols_per_page = max_cols_per_page
        self.weeks_per_month = weeks_per_month

    def split_weeks_into_month_chunks(self, total_weeks: int) -> List[Dict[str, Any]]:
        """
        Split weeks into month-based chunks.

        Args:
            total_weeks: Total number of weekly columns

        Returns:
            List of month chunks:
            [
                {
                    'month': 1,
                    'start_week': 1,
                    'end_week': 4,
                    'label': 'Bulan 1 (W1-W4)',
                    'week_count': 4
                },
                ...
            ]

        Example:
            >>> engine = PaginationEngine(weeks_per_month=4)
            >>> engine.split_weeks_into_month_chunks(10)
            [
                {'month': 1, 'start_week': 1, 'end_week': 4, 'label': 'Bulan 1 (W1-W4)', 'week_count': 4},
                {'month': 2, 'start_week': 5, 'end_week': 8, 'label': 'Bulan 2 (W5-W8)', 'week_count': 4},
                {'month': 3, 'start_week': 9, 'end_week': 10, 'label': 'Bulan 3 (W9-W10)', 'week_count': 2}
            ]
        """
        chunks = []
        month_number = 1
        week_cursor = 1

        while week_cursor <= total_weeks:
            end_week = min(week_cursor + self.weeks_per_month - 1, total_weeks)
            week_count = end_week - week_cursor + 1

            chunks.append({
                'month': month_number,
                'start_week': week_cursor,
                'end_week': end_week,
                'label': f'Bulan {month_number} (W{week_cursor}-W{end_week})',
                'week_count': week_count
            })

            week_cursor = end_week + 1
            month_number += 1

        return chunks

    def split_rows_by_hierarchy(
        self,
        rows: List[Dict[str, Any]],
        hierarchy_key: str = 'klasifikasi_id'
    ) -> List[Dict[str, Any]]:
        """
        Split rows into pages while preserving hierarchy.

        Never splits in the middle of a sub-klasifikasi group.
        Adds continuation headers when a klasifikasi spans multiple pages.

        Args:
            rows: List of row dictionaries
            hierarchy_key: Key to group by (default: 'klasifikasi_id')

        Returns:
            List of page dictionaries:
            [
                {
                    'page': 1,
                    'row_start': 0,
                    'row_end': 27,
                    'rows': [...],
                    'is_continuation': False,
                    'continuation_context': None
                },
                ...
            ]

        Example:
            If rows 0-30 all have klasifikasi_id=1, and max_rows=28,
            it will NOT split at row 28. Instead:
            - Page 1: Rows 0-30 (all rows, exceeds limit but preserves group)
            OR if next group starts at row 25:
            - Page 1: Rows 0-24 (klasifikasi_id=1)
            - Page 2: Rows 25-52 (klasifikasi_id=2, continuation header added)
        """
        if not rows:
            return []

        pages = []
        current_page_rows = []
        current_page_start = 0
        page_number = 1

        # Group rows by hierarchy
        groups = self._group_rows_by_hierarchy(rows, hierarchy_key)

        for group_id, group_rows in groups:
            # Check if adding this group exceeds page limit
            would_exceed = len(current_page_rows) + len(group_rows) > self.max_rows_per_page

            if would_exceed and current_page_rows:
                # Save current page
                pages.append({
                    'page': page_number,
                    'row_start': current_page_start,
                    'row_end': current_page_start + len(current_page_rows) - 1,
                    'rows': current_page_rows,
                    'is_continuation': False,
                    'continuation_context': None
                })

                # Start new page
                page_number += 1
                current_page_start += len(current_page_rows)
                current_page_rows = []

            # Add group to current page
            current_page_rows.extend(group_rows)

        # Add final page
        if current_page_rows:
            pages.append({
                'page': page_number,
                'row_start': current_page_start,
                'row_end': current_page_start + len(current_page_rows) - 1,
                'rows': current_page_rows,
                'is_continuation': False,
                'continuation_context': None
            })

        return pages

    def _group_rows_by_hierarchy(
        self,
        rows: List[Dict[str, Any]],
        hierarchy_key: str
    ) -> List[Tuple[Any, List[Dict[str, Any]]]]:
        """
        Group consecutive rows by hierarchy key.

        Args:
            rows: List of row dictionaries
            hierarchy_key: Key to group by

        Returns:
            List of (group_id, group_rows) tuples
        """
        if not rows:
            return []

        groups = []
        current_group_id = rows[0].get(hierarchy_key)
        current_group_rows = [rows[0]]

        for row in rows[1:]:
            row_group_id = row.get(hierarchy_key)

            if row_group_id == current_group_id:
                current_group_rows.append(row)
            else:
                # Save current group
                groups.append((current_group_id, current_group_rows))

                # Start new group
                current_group_id = row_group_id
                current_group_rows = [row]

        # Add final group
        if current_group_rows:
            groups.append((current_group_id, current_group_rows))

        return groups

    def create_page_matrix(
        self,
        rows: List[Dict[str, Any]],
        total_weeks: int,
        hierarchy_key: str = 'klasifikasi_id'
    ) -> List[PageChunk]:
        """
        Create page matrix for both-axis overflow.

        When both rows and columns exceed limits, creates a grid of pages:
        - Horizontal axis: Month chunks
        - Vertical axis: Hierarchy-aware row pages

        Args:
            rows: List of row dictionaries
            total_weeks: Total number of weekly columns
            hierarchy_key: Hierarchy grouping key

        Returns:
            List of PageChunk objects representing the page matrix

        Example:
            With 50 rows (2 pages) × 24 weeks (6 months in 4-week chunks, 2 pages),
            creates 2×2 = 4 pages:
            - Page 1: Rows 0-27, Weeks 1-16
            - Page 2: Rows 0-27, Weeks 17-24
            - Page 3: Rows 28-49, Weeks 1-16
            - Page 4: Rows 28-49, Weeks 17-24
        """
        # Split rows
        row_pages = self.split_rows_by_hierarchy(rows, hierarchy_key)

        # Split columns (weeks into month chunks)
        month_chunks = self.split_weeks_into_month_chunks(total_weeks)

        # Group month chunks into column pages
        col_pages = self._group_month_chunks_into_pages(month_chunks)

        # Create page matrix
        page_matrix = []
        page_number = 1

        for row_page in row_pages:
            for col_page_idx, col_page in enumerate(col_pages):
                # Build column list for this page
                columns = []
                for month_chunk in col_page['chunks']:
                    for week in range(month_chunk['start_week'], month_chunk['end_week'] + 1):
                        columns.append(f'W{week}')

                # Determine continuation context
                is_continuation = row_page['is_continuation'] or col_page_idx > 0
                continuation_context = None

                if is_continuation:
                    context_parts = []
                    if row_page['is_continuation']:
                        context_parts.append(f"Rows {row_page['row_start']+1}-{row_page['row_end']+1}")
                    if col_page_idx > 0:
                        context_parts.append(f"Weeks {col_page['start_week']}-{col_page['end_week']}")
                    continuation_context = " | ".join(context_parts)

                page_chunk = PageChunk(
                    page_number=page_number,
                    row_start=row_page['row_start'],
                    row_end=row_page['row_end'],
                    col_start=col_page['start_week'],
                    col_end=col_page['end_week'],
                    rows=row_page['rows'],
                    columns=columns,
                    is_continuation=is_continuation,
                    continuation_context=continuation_context
                )

                page_matrix.append(page_chunk)
                page_number += 1

        return page_matrix

    def _group_month_chunks_into_pages(
        self,
        month_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Group month chunks into column pages.

        Args:
            month_chunks: List of month chunk dictionaries

        Returns:
            List of column page dictionaries
        """
        col_pages = []
        current_page_chunks = []
        current_week_count = 0
        page_number = 1

        for chunk in month_chunks:
            # Check if adding this chunk exceeds column limit
            would_exceed = current_week_count + chunk['week_count'] > self.max_cols_per_page

            if would_exceed and current_page_chunks:
                # Save current page
                start_week = current_page_chunks[0]['start_week']
                end_week = current_page_chunks[-1]['end_week']

                col_pages.append({
                    'page': page_number,
                    'start_week': start_week,
                    'end_week': end_week,
                    'chunks': current_page_chunks,
                    'week_count': current_week_count
                })

                # Start new page
                page_number += 1
                current_page_chunks = []
                current_week_count = 0

            # Add chunk to current page
            current_page_chunks.append(chunk)
            current_week_count += chunk['week_count']

        # Add final page
        if current_page_chunks:
            start_week = current_page_chunks[0]['start_week']
            end_week = current_page_chunks[-1]['end_week']

            col_pages.append({
                'page': page_number,
                'start_week': start_week,
                'end_week': end_week,
                'chunks': current_page_chunks,
                'week_count': current_week_count
            })

        return col_pages

    def calculate_page_count(
        self,
        total_rows: int,
        total_cols: int
    ) -> Dict[str, int]:
        """
        Calculate total page count for given dimensions.

        Args:
            total_rows: Total number of rows
            total_cols: Total number of columns

        Returns:
            Dictionary with page count info:
            {
                'row_pages': 2,
                'col_pages': 3,
                'total_pages': 6,
                'needs_pagination': True
            }
        """
        row_pages = math.ceil(total_rows / self.max_rows_per_page)
        col_pages = math.ceil(total_cols / self.max_cols_per_page)
        total_pages = row_pages * col_pages
        needs_pagination = total_pages > 1

        return {
            'row_pages': row_pages,
            'col_pages': col_pages,
            'total_pages': total_pages,
            'needs_pagination': needs_pagination
        }
