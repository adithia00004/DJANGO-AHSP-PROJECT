"""
PDF Export service for AHSP data.

PHASE 6: Export System

Provides PDF export functionality for:
- Professional AHSP reports
- Single job with rincian
- Multiple jobs summary
- Search results report
"""

from __future__ import annotations

import io
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from django.db.models import QuerySet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from referensi.models import AHSPReferensi, RincianReferensi

logger = logging.getLogger(__name__)


class PDFExportService:
    """
    Service for exporting AHSP data to PDF format.

    Features:
    - Professional layout
    - Single job report with rincian
    - Multiple jobs summary
    - Search results report
    - Custom styling
    """

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#2c5aa0'),
            spaceAfter=10,
            fontName='Helvetica-Bold'
        ))

        # Info style
        self.styles.add(ParagraphStyle(
            name='InfoLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold'
        ))

        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        ))

    def export_single_job(
        self,
        ahsp: AHSPReferensi,
        include_rincian: bool = True
    ) -> io.BytesIO:
        """
        Export single AHSP job to PDF.

        Args:
            ahsp: AHSP job to export
            include_rincian: Include rincian details

        Returns:
            BytesIO: PDF file in memory
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        story = []

        # Title
        title = Paragraph(
            "ANALISIS HARGA SATUAN PEKERJAAN (AHSP)",
            self.styles['CustomTitle']
        )
        story.append(title)
        story.append(Spacer(1, 0.5*cm))

        # AHSP Info
        info_data = [
            ['Sumber:', ahsp.sumber],
            ['Kode AHSP:', ahsp.kode_ahsp],
            ['Nama Pekerjaan:', ahsp.nama_ahsp],
            ['Satuan:', ahsp.satuan],
            ['Klasifikasi:', ahsp.klasifikasi or '-'],
            ['Sub Klasifikasi:', ahsp.sub_klasifikasi or '-'],
        ]

        info_table = Table(info_data, colWidths=[4*cm, 13*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ]))

        story.append(info_table)
        story.append(Spacer(1, 1*cm))

        # Rincian
        if include_rincian:
            subtitle = Paragraph("Rincian", self.styles['CustomSubtitle'])
            story.append(subtitle)
            story.append(Spacer(1, 0.3*cm))

            rincian_list = ahsp.rincian_set.all().order_by('urut')

            if rincian_list.exists():
                # Rincian table
                rincian_data = [[
                    'No', 'Kategori', 'Kode', 'Uraian', 'Satuan', 'Koefisien'
                ]]

                for rincian in rincian_list:
                    rincian_data.append([
                        str(rincian.urut),
                        rincian.kategori,
                        rincian.kode_item,
                        rincian.uraian_item[:40] + '...' if len(rincian.uraian_item) > 40 else rincian.uraian_item,
                        rincian.satuan_item,
                        f"{float(rincian.koefisien):.4f}"
                    ])

                rincian_table = Table(
                    rincian_data,
                    colWidths=[1*cm, 2*cm, 3*cm, 7*cm, 2*cm, 2*cm]
                )

                rincian_table.setStyle(TableStyle([
                    # Header
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

                    # Data
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # No column
                    ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),  # Koefisien column

                    # Grid
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

                    # Alternating row colors
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
                ]))

                story.append(rincian_table)
            else:
                story.append(Paragraph("Tidak ada rincian.", self.styles['Normal']))

        # Footer
        story.append(Spacer(1, 2*cm))
        footer_text = f"Diekspor pada: {datetime.now().strftime('%d %B %Y %H:%M:%S')}"
        footer = Paragraph(footer_text, self.styles['Footer'])
        story.append(footer)

        # Build PDF
        doc.build(story)
        buffer.seek(0)

        logger.info(f"Exported single AHSP to PDF: {ahsp.kode_ahsp}")
        return buffer

    def export_multiple_jobs(
        self,
        jobs: QuerySet[AHSPReferensi] | List[AHSPReferensi],
        title: str = "Daftar AHSP"
    ) -> io.BytesIO:
        """
        Export multiple AHSP jobs summary to PDF.

        Args:
            jobs: QuerySet or list of AHSP jobs
            title: Report title

        Returns:
            BytesIO: PDF file in memory
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        story = []

        # Title
        title_para = Paragraph(title, self.styles['CustomTitle'])
        story.append(title_para)
        story.append(Spacer(1, 0.5*cm))

        # Metadata
        meta_text = f"Total: {len(list(jobs))} pekerjaan | Diekspor: {datetime.now().strftime('%d %B %Y %H:%M:%S')}"
        meta = Paragraph(meta_text, self.styles['Normal'])
        story.append(meta)
        story.append(Spacer(1, 0.5*cm))

        # Table
        table_data = [[
            'No', 'Sumber', 'Kode AHSP', 'Nama Pekerjaan', 'Satuan', 'Klasifikasi'
        ]]

        for idx, job in enumerate(jobs, start=1):
            table_data.append([
                str(idx),
                job.sumber,
                job.kode_ahsp,
                job.nama_ahsp[:50] + '...' if len(job.nama_ahsp) > 50 else job.nama_ahsp,
                job.satuan,
                (job.klasifikasi[:30] + '...') if job.klasifikasi and len(job.klasifikasi) > 30 else (job.klasifikasi or '-')
            ])

        table = Table(
            table_data,
            colWidths=[1.5*cm, 3*cm, 3*cm, 8*cm, 2*cm, 5*cm]
        )

        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Data
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # No column

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ]))

        story.append(table)

        # Build PDF
        doc.build(story)
        buffer.seek(0)

        logger.info(f"Exported {len(list(jobs))} AHSP jobs to PDF")
        return buffer

    def export_search_results(
        self,
        results: QuerySet[AHSPReferensi] | List[AHSPReferensi],
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> io.BytesIO:
        """
        Export search results to PDF.

        Args:
            results: Search results
            query: Search query used
            filters: Filters applied

        Returns:
            BytesIO: PDF file in memory
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        story = []

        # Title
        title = Paragraph("Hasil Pencarian AHSP", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.3*cm))

        # Search info
        search_info = [
            ['Query:', query],
        ]

        if filters:
            for key, value in filters.items():
                if value:
                    search_info.append([f'{key.title()}:', str(value)])

        search_info.append(['Hasil:', f"{len(list(results))} pekerjaan"])
        search_info.append(['Tanggal:', datetime.now().strftime('%d %B %Y %H:%M:%S')])

        info_table = Table(search_info, colWidths=[3*cm, 15*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        story.append(info_table)
        story.append(Spacer(1, 0.5*cm))

        # Results table
        if results:
            table_data = [[
                'No', 'Sumber', 'Kode AHSP', 'Nama Pekerjaan', 'Satuan', 'Klasifikasi'
            ]]

            for idx, job in enumerate(results, start=1):
                table_data.append([
                    str(idx),
                    job.sumber,
                    job.kode_ahsp,
                    job.nama_ahsp[:50] + '...' if len(job.nama_ahsp) > 50 else job.nama_ahsp,
                    job.satuan,
                    (job.klasifikasi[:30] + '...') if job.klasifikasi and len(job.klasifikasi) > 30 else (job.klasifikasi or '-')
                ])

            table = Table(
                table_data,
                colWidths=[1.5*cm, 3*cm, 3*cm, 8*cm, 2*cm, 5*cm]
            )

            table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

                # Data
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),

                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
            ]))

            story.append(table)
        else:
            no_results = Paragraph("Tidak ada hasil pencarian.", self.styles['Normal'])
            story.append(no_results)

        # Build PDF
        doc.build(story)
        buffer.seek(0)

        logger.info(f"Exported search results to PDF: '{query}' ({len(list(results))} results)")
        return buffer


# Singleton instance
pdf_export_service = PDFExportService()


__all__ = [
    'PDFExportService',
    'pdf_export_service',
]
