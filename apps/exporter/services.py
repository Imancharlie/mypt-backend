import os
import re
import logging
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Image as RLImage
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from django.conf import settings
from django.template.loader import render_to_string
from django.http import HttpResponse
from pypdf import PdfReader, PdfWriter
from PIL import Image as PILImage
import requests

logger = logging.getLogger(__name__)

def _diagram_pdf_path():
    """Get the path to the Diagram_page.pdf file."""
    return os.path.join(settings.BASE_DIR, 'Diagram_page.pdf')

def _diagram_docx_path():
    """Get the path to the Diagram_page.docx file."""
    return os.path.join(settings.BASE_DIR, 'Diagram_page.docx')

def _get_diagram_data(weekly_report_id):
    """Fetch diagram data from the media server for a weekly report.
    
    Args:
        weekly_report_id: The ID of the weekly report
        
    Returns:
        dict: Diagram data with keys 'exists', 'text', 'image', etc.
              Returns empty payload if server unavailable or no data exists.
    """
    try:
        from .diagram_client import MyPTMediaClient
        
        # Use the weekly report ID as the reference
        report_reference = str(weekly_report_id)
        
        client = MyPTMediaClient()
        diagram_data = client.get_document(report_reference)
        
        logger.info(f"Retrieved diagram data for report {weekly_report_id}: exists={diagram_data.get('exists')}")
        return diagram_data
        
    except Exception as e:
        logger.error(f"Error fetching diagram data for report {weekly_report_id}: {e}")
        # Return empty payload on any error
        return {
            'exists': False,
            'report_reference': str(weekly_report_id),
            'uuid': None,
            'text': '',
            'image': None,
            'images': [],
            'created_at': None,
            'updated_at': None,
        }

def _download_image_from_url(image_url):
    """Download an image from a URL and return it as bytes.
    
    Args:
        image_url: URL of the image to download
        
    Returns:
        bytes: Image data or None if download fails
    """
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Error downloading image from {image_url}: {e}")
        return None

def _fit_image_within_bounds(image_width, image_height, max_width, max_height):
    """Calculate dimensions to fit an image within bounds while maintaining aspect ratio.
    
    Args:
        image_width: Original image width
        image_height: Original image height
        max_width: Maximum allowed width
        max_height: Maximum allowed height
        
    Returns:
        tuple: (new_width, new_height) scaled to fit within bounds
    """
    if image_width <= max_width and image_height <= max_height:
        return image_width, image_height
    
    # Calculate scaling factors
    width_ratio = max_width / image_width
    height_ratio = max_height / image_height
    scale_factor = min(width_ratio, height_ratio)
    
    new_width = int(image_width * scale_factor)
    new_height = int(image_height * scale_factor)
    
    return new_width, new_height

def _generate_weekly_report_pdf_elements(weekly_report, doc, include_title=True):
    """Generate PDF elements for a weekly report. Can be used for single exports or logbook."""
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    
    elements = []
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Create custom styles for professional format
    title_style = ParagraphStyle(
        'CoETTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=20,
        alignment=1,  # Center alignment
        fontName='Times-Bold',
        leading=19,  # 1.5 line spacing
        textColor=colors.black  # Explicit black color
    )
    
    header_style = ParagraphStyle(
        'CoETHeader',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=12,
        fontName='Times-Bold',
        leading=18,  # 1.5 line spacing
        textColor=colors.black  # Explicit black color
    )
    
    # Create normal text style
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Times-Roman',
        leading=18,  # 1.5 line spacing
        spaceAfter=6,
        textColor=colors.black  # Explicit black color
    )
    
    # Title (only if requested)
    if include_title:
        title = Paragraph("College of Engineering and Technology (CoET)", title_style)
        elements.append(title)
    
    # Weekly Report Header
    daily_reports = weekly_report.get_daily_reports()
    total_hours = sum(report.hours_spent for report in daily_reports)
    
    report_header = Paragraph(f"Weekly Report No: {weekly_report.week_number} from: {weekly_report.start_date.strftime('%d-%m-%Y')} to: {weekly_report.end_date.strftime('%d-%m-%Y')}", header_style)
    elements.append(report_header)
    
    # Table cell styles - defined here so both the daily and operations sections can use them
    header_cell_style = ParagraphStyle(
        'TableHeader', parent=styles['Normal'], fontSize=12, fontName='Times-Bold', leading=18, textColor=colors.black
    )
    cell_style = ParagraphStyle(
        'TableCell', parent=styles['Normal'], fontSize=12, fontName='Times-Roman', leading=18, textColor=colors.black
    )

    # Helper to compute minimal col width in points (content width + padding)
    def min_col_width(texts, font_name='Times-Roman', font_size=12, side_padding_pts=12):
        if not texts:
            return 0
        widest = max(stringWidth(str(t), font_name, font_size) for t in texts)
        return widest + side_padding_pts

    # Day mapping
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    # Daily Reports Table - No "Weekly Work Summary" heading
    if daily_reports.exists():
        # Fixed small Day/Hours columns so the Description column takes the rest
        available_width = doc.width  # points

        day_col = 1.0*inch  # enough for "Wednesday" (56pt) + cell padding on one line
        hours_col = 0.7*inch
        description_col = max(available_width - day_col - hours_col, 2.5*inch)

        data = [
            [
                Paragraph('Day', header_cell_style),
                Paragraph('Brief description of work performed', header_cell_style),
                Paragraph('Hours', header_cell_style),
            ]
        ]

        for i, report in enumerate(daily_reports):
            day_name = day_names[i] if i < len(day_names) else report.date.strftime('%A')
            data.append([
                Paragraph(day_name, cell_style),
                Paragraph(report.description or '', cell_style),
                Paragraph(str(report.hours_spent), cell_style),
            ])

        # Total row
        data.append([
            Paragraph('', cell_style),
            Paragraph('Total hrs', header_cell_style),
            Paragraph(str(total_hours), header_cell_style),
        ])

        daily_table = Table(data, colWidths=[day_col, description_col, hours_col], repeatRows=1)
        daily_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),  # Explicit black color
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('REPEATROWS', (0, 0), (-1, 0)),
        ]))
        elements.append(daily_table)
        elements.append(Spacer(1, 20))
    
    # Main Job and Operations - Independent section
    if hasattr(weekly_report, 'main_job') and weekly_report.main_job:
        # Add space before main job section
        elements.append(Spacer(1, 20))
        
        # Create main job title as a paragraph (not table)
        main_job_title = weekly_report.main_job.title or "Sequence of Operations"
        main_job_title_style = ParagraphStyle(
            'MainJobTitle',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=12,
            fontName='Times-Bold',
            leading=18,
            textColor=colors.black  # Explicit black color
        )
        main_job_title_para = Paragraph(main_job_title, main_job_title_style)
        elements.append(main_job_title_para)
        
        # Create operations table
        operations_data = [['No', 'Operation', 'Tools, Machinery, Equipment']]
        
        # Get actual operations from database - no mock data
        actual_operations = weekly_report.main_job.operations.all().order_by('step_number')
        
        if actual_operations.exists():
            # Use actual operations from database
            for operation in actual_operations:
                operations_data.append([
                    str(operation.step_number),
                    operation.operation_description or '',
                    operation.tools_used or ''
                ])
        else:
            # If no operations exist, show empty table with just header
            operations_data.append(['', '', ''])
        
        # Dynamically size columns so the Operation column gets the majority of width
        available_width = doc.width

        numbers = ['No'] + [str(op.step_number) for op in actual_operations]
        tools_samples = ['Tools, Machinery, Equipment'] + [
            (op.tools_used or '') for op in actual_operations
        ]

        # Keep the No column small; let the Operation column take the remaining width
        no_col = 0.6*inch
        tools_col = min(max(min_col_width(tools_samples, 'Times-Roman', 12, side_padding_pts=12), 1.0*inch), 1.8*inch)
        operation_col = max(available_width - no_col - tools_col, 3.0*inch)

        # Convert operations_data text to Paragraphs
        op_header = [
            Paragraph('No', header_cell_style),
            Paragraph('Operation', header_cell_style),
            Paragraph('Tools, Machinery, Equipment', header_cell_style),
        ]
        data_ops = [op_header]

        if actual_operations.exists():
            for op in actual_operations:
                data_ops.append([
                    Paragraph(str(op.step_number), cell_style),
                    Paragraph(op.operation_description or '', cell_style),
                    Paragraph(op.tools_used or '', cell_style),
                ])
        else:
            data_ops.append([
                Paragraph('', cell_style),
                Paragraph('', cell_style),
                Paragraph('', cell_style),
            ])

        operations_table = Table(data_ops, colWidths=[no_col, operation_col, tools_col], repeatRows=1)
        operations_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),  # Explicit black color
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('REPEATROWS', (0, 0), (-1, 0)),
        ]))
        elements.append(operations_table)
        elements.append(Spacer(1, 30))
    
    # Signature section - Create a small table for signature (right half)
    # Row 1: Headers (60%/40% split), Row 2: Empty fields for signatures
    signature_data = [
        [Paragraph('Signature Training Officer:', cell_style), Paragraph('Date:', cell_style)],
        ['', '']
    ]

    # Create signature table with right alignment
    # Signature column is 20% wider (1.8 x 1.2 = 2.16") so "Signature Training Officer:"
    # fits horizontally; Date column stays at 1.2"
    # Increase signature column by additional 20% to 2.592"
    signature_table = Table(signature_data, colWidths=[2.592*inch, 1.2*inch], hAlign='RIGHT')
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),  # Explicit black color
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.white])
    ]))

    elements.append(Spacer(1, 20))
    elements.append(KeepTogether([signature_table]))

    return elements


def _append_diagram_page_to_pdf(pdf_content, diagram_data=None):
    """Append Diagram_page.pdf to the existing PDF content with optional diagram data overlay.
    
    Args:
        pdf_content: The existing PDF content (weekly report)
        diagram_data: Optional diagram data from media server
        
    Returns:
        bytes: Combined PDF with diagram page
    """
    try:
        diagram_path = _diagram_pdf_path()
        if not os.path.exists(diagram_path):
            logger.warning(f"Diagram PDF not found at {diagram_path}, skipping diagram insertion")
            return pdf_content
        
        # Read the existing PDF content
        reader = PdfReader(BytesIO(pdf_content))
        writer = PdfWriter()
        
        # Add all pages from the original PDF
        for page in reader.pages:
            writer.add_page(page)
        
        # Always append the original Diagram_page.pdf template so the frame,
        # header and signature row are preserved. When diagram content exists,
        # build a transparent overlay (text + image) drawn inside the
        # template's drawing area and merge it onto the template page so the
        # image is displayed INSIDE the diagram_page layout.
        diagram_reader = PdfReader(diagram_path)
        overlay_pdf = None
        if diagram_data and diagram_data.get('exists'):
            overlay_pdf = _build_diagram_overlay_pdf(diagram_data)

        for page in diagram_reader.pages:
            if overlay_pdf:
                try:
                    overlay_reader = PdfReader(BytesIO(overlay_pdf))
                    if overlay_reader.pages:
                        page.merge_page(overlay_reader.pages[0])
                except Exception as e:
                    logger.error(f"Error merging diagram overlay onto template: {e}")
            writer.add_page(page)
        
        # Write the combined PDF
        output_buffer = BytesIO()
        writer.write(output_buffer)
        combined_pdf = output_buffer.getvalue()
        output_buffer.close()
        
        return combined_pdf
        
    except Exception as e:
        logger.error(f"Error appending diagram page to PDF: {e}")
        return pdf_content

# Drawing-area rectangle in Diagram_page.pdf, PDF points (y measured from bottom):
#   left, bottom, right, top
DIAGRAM_TEMPLATE_DRAWING_BOX_PT = (22.8, 56.664, 589.32, 741.6)


def _build_diagram_overlay_pdf(diagram_data):
    """Build a transparent overlay PDF with text and image drawn INSIDE the
    template's drawing box, so nothing can escape the diagram_page frame.

    Layout:
      * the text always starts at the TOP of the box (just a small margin from
        the top of the diagram page) - whether or not an image is present,
      * with an image the text may take up to 50% of the box height; without
        an image it may fill the whole box (font shrinks, and blocks are only
        dropped as an absolute last resort, so it never overflows the page),
      * the image fills the remaining space below the text; when there is no
        text the image is vertically centered.
    Styling is preserved: lines starting with "# " become headings and
    "**text**" becomes bold, exactly as the user styled them in the frontend.

    Args:
        diagram_data: Dictionary containing 'text' and 'image' data from media server

    Returns:
        bytes: Overlay PDF content, or None if there is nothing to draw or drawing fails
    """
    text = (diagram_data.get('text') or '').strip()
    image_data = diagram_data.get('image') or {}
    image_url = image_data.get('url')

    if not text and not image_url:
        return None

    try:
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.pagesizes import letter as _letter
        from reportlab.lib.utils import ImageReader
        from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT

        left, bottom, right, top = DIAGRAM_TEMPLATE_DRAWING_BOX_PT
        pad = 10
        box_left = left + pad
        box_bottom = bottom + pad
        box_right = right - pad
        box_top = top - pad
        box_w = box_right - box_left
        box_h = box_top - box_bottom

        # ---- resolve image (bytes + pixel dims) -----------------------------
        image_bytes = None
        iw = ih = 0
        if image_url:
            image_bytes = _download_image_from_url(image_url)
            if image_bytes:
                try:
                    with PILImage.open(BytesIO(image_bytes)) as img:
                        iw, ih = img.size
                except Exception as e:
                    logger.error(f"Error reading diagram image dimensions: {e}")
                    image_bytes = None

        blocks = _clean_diagram_blocks(_parse_diagram_text(text))

        # ---- build and measure styled paragraphs ------------------------------
        def _make_paragraphs(blk_list, body_size):
            paras = []
            for blk in blk_list:
                if blk['kind'] == 'blank':
                    continue
                segs = []
                for bold, s in blk['segments']:
                    esc = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    segs.append(f'<b>{esc}</b>' if bold else esc)
                markup = ''.join(segs)
                if blk['kind'] == 'heading':
                    size = body_size + 2
                    paras.append(Paragraph(markup, ParagraphStyle(
                        'DiagramHeading', fontName='Times-Bold', fontSize=size,
                        leading=size * 1.2, spaceBefore=6, spaceAfter=4,
                        alignment=TA_LEFT)))
                else:
                    paras.append(Paragraph(markup, ParagraphStyle(
                        'DiagramBody', fontName='Times-Roman', fontSize=body_size,
                        leading=body_size * 1.2, spaceAfter=2,
                        alignment=TA_JUSTIFY)))
            return paras

        def _measure(paras):
            total = 0.0
            for p in paras:
                _, h = p.wrap(box_w, box_h)
                total += h + p.getSpaceBefore() + p.getSpaceAfter()
            return total

        def _cap_block(blk):
            full = ''.join(seg for _, seg in blk['segments'])
            text = full
            while True:
                esc = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                if blk['kind'] == 'heading':
                    size = body_size + 2
                    p = Paragraph(esc, ParagraphStyle(
                        'DiagramHeading', fontName='Times-Bold', fontSize=size,
                        leading=size * 1.2, spaceBefore=6, spaceAfter=4,
                        alignment=TA_LEFT))
                else:
                    p = Paragraph(esc, ParagraphStyle(
                        'DiagramBody', fontName='Times-Roman', fontSize=body_size,
                        leading=body_size * 1.2, spaceAfter=2,
                        alignment=TA_JUSTIFY))
                _, h = p.wrap(box_w, box_h)
                total = h + p.getSpaceBefore() + p.getSpaceAfter()
                if total <= hard_max or len(text) <= 40:
                    break
                text = text[:int(len(text) * 0.85)]
            return {'kind': blk['kind'], 'segments': [(False, text.rstrip())]}

        # Text budget: up to 50% of the box when an image is present; without
        # an image the text may use the whole box (~90% of a normal page) and
        # is NEVER truncated while it still fits - the font shrinks first
        # (down to 6pt) so as much of the user's text as possible is kept.
        text_max = box_h * 0.5 if image_bytes else box_h - 8
        hard_max = box_h if not image_bytes else text_max
        min_size = 6

        body_size = 12
        draw_blocks = list(blocks)
        paras = _make_paragraphs(draw_blocks, body_size)
        text_h = _measure(paras)
        while body_size > min_size and text_h > text_max:
            body_size -= 1
            paras = _make_paragraphs(draw_blocks, body_size)
            text_h = _measure(paras)
        # Absolute last resort: only when even the minimum font cannot fit the
        # text within the page (or the image's share) are trailing blocks
        # dropped; a single giant block is capped (its beginning is kept) so
        # nothing escapes the diagram_page frame.
        while draw_blocks and text_h > hard_max:
            if len(draw_blocks) == 1:
                draw_blocks = [_cap_block(draw_blocks[0])]
                paras = _make_paragraphs(draw_blocks, body_size)
                text_h = _measure(paras)
                break
            draw_blocks.pop()
            paras = _make_paragraphs(draw_blocks, body_size)
            text_h = _measure(paras)

        gap = 16 if (paras and image_bytes) else 0

        # ---- fit the image into the space below the text ----------------------
        disp_w = disp_h = 0
        if image_bytes and iw and ih:
            if paras:
                avail_h_img = max(10.0, (box_top - text_h - gap) - box_bottom - 4)
            else:
                avail_h_img = box_h - 8
            scale = min(box_w / iw, avail_h_img / ih) if avail_h_img > 0 else 0
            if scale > 0:
                disp_w = iw * scale
                disp_h = ih * scale

        # ---- draw -------------------------------------------------------------
        buffer = BytesIO()
        c = rl_canvas.Canvas(buffer, pagesize=_letter)
        c.setFillColor(colors.black)
        c.setStrokeColor(colors.black)

        if paras:
            y = box_top
            for p in paras:
                p.drawOn(c, box_left, y - p.height)
                y -= p.height + p.getSpaceBefore() + p.getSpaceAfter()
            logger.info(
                f"Overlaid diagram text on template: {len(paras)} paragraph(s) "
                f"@ {body_size}pt body (text_h {text_h:.1f}pt)")

        if image_bytes and disp_h > 0:
            x = box_left + (box_w - disp_w) / 2.0
            if paras:
                remaining_top = box_top - text_h - gap
                y_bottom = remaining_top - disp_h
            else:
                y_bottom = box_bottom + (box_h - disp_h) / 2.0
            c.drawImage(ImageReader(BytesIO(image_bytes)), x, y_bottom,
                        width=disp_w, height=disp_h, mask='auto')
            logger.info(f"Overlaid diagram image on template: {disp_w:.0f}x{disp_h:.0f}pt")

        c.showPage()
        c.save()
        result = buffer.getvalue()
        buffer.close()
        return result

    except Exception as e:
        logger.error(f"Error building diagram overlay PDF: {e}")
        return None

# Fixed height (in inches) of the diagram frame (row 1 of the copied
# Diagram_page.docx table). The frame is kept CONSTANT like a background
# page; text and image are placed inside it and sized so they never spill
# onto a following page.
DIAGRAM_DRAWING_ROW_HEIGHT_IN = 8.6


def _estimate_wrapped_lines(text, size_pt=12, usable_width_in=7.55):
    """Approximate the number of wrapped lines a text block will take inside
    the drawing cell. Intended for reserving space for the image below it, so
    it deliberately under-estimates the characters per line (safe side)."""
    if not text:
        return 0
    # conservative: ~10.5 chars per inch for 12pt, scale with font size
    chars_per_inch = 10.5 * (12.0 / size_pt)
    cpl = max(1.0, usable_width_in * chars_per_inch)
    total = 0
    for seg in text.split('\n'):
        total += max(1, (len(seg) + cpl - 1) // int(cpl))
    return total


def _parse_diagram_text(text):
    """Split the diagram description into printable blocks.

    Lightweight markup (rendered in the exported PDF and DOCX exactly as the
    user styles it in the frontend):
      * a line starting with "# "  -> heading (bold, slightly larger)
      * "**text**" anywhere inline -> bold text

    Returns a list of blocks:
        {'kind': 'blank'|'heading'|'body', 'segments': [(is_bold, text), ...]}
    """
    blocks = []
    for raw in (text or '').split('\n'):
        line = raw.strip()
        if not line:
            blocks.append({'kind': 'blank', 'segments': []})
            continue
        if line.startswith('# '):
            kind = 'heading'
            content = line[2:].strip()
        else:
            kind = 'body'
            content = line
        segments = []
        for part in re.split(r'(\*\*[^*]+\*\*)', content):
            if not part:
                continue
            if len(part) > 4 and part.startswith('**') and part.endswith('**'):
                segments.append((True, part[2:-2]))
            else:
                segments.append((False, part))
        blocks.append({'kind': kind, 'segments': segments})
    return blocks


def _clean_diagram_blocks(blocks):
    """Trim leading/trailing blank blocks and normalise the list."""
    out = list(blocks)
    while out and out[0]['kind'] == 'blank':
        out.pop(0)
    while out and out[-1]['kind'] == 'blank':
        out.pop()
    return out


def _estimate_diagram_text_height(blocks, body_size_pt=12, usable_width_in=7.55):
    """Estimate the stacked height (inches) of parsed text blocks inside the
    drawing cell, so the image can be sized to the remaining space. Slightly
    pessimistic on purpose so the image never overflows the fixed frame."""
    total_in = 0.0
    for blk in blocks:
        if blk['kind'] == 'blank':
            total_in += 0.15
            continue
        size_pt = body_size_pt + 2 if blk['kind'] == 'heading' else body_size_pt
        text = ''.join(seg for _, seg in blk['segments'])
        lines = _estimate_wrapped_lines(text, size_pt, usable_width_in)
        line_h = size_pt * 1.2 / 72.0
        spacing = 0.13 if blk['kind'] == 'heading' else 0.07
        total_in += lines * line_h + spacing
    return total_in


def _cap_diagram_block_to_height(block, body_size_pt=12, hard_max_in=8.6,
                                 usable_width_in=7.55):
    """Cap a single oversized block so its BEGINNING fits within hard_max_in.

    Used only as an absolute last resort when one giant block (e.g. a single
    pasted paragraph) is taller than the frame even at the minimum font size.
    Rather than dropping the block entirely, the leading text is kept and
    shortened until the estimated height fits.
    """
    full = ''.join(seg for _, seg in block['segments'])
    if not full:
        return block
    text = full
    while True:
        capped = {'kind': block['kind'], 'segments': [(False, text)]}
        if (_estimate_diagram_text_height([capped], body_size_pt, usable_width_in)
                <= hard_max_in or len(text) <= 40):
            break
        text = text[:int(len(text) * 0.85)]
    return {'kind': block['kind'], 'segments': [(False, text.rstrip())]}


def _add_diagram_content_to_drawing_cell(doc, diagram_data):
    """Insert the diagram TEXT (first) and IMAGE (below it) into the drawing
    cell of the copied Diagram_page.docx table (row 1, the merged
    "Details of main job" area).

    The frame is treated as a BACKGROUND page:
      * the row height is pinned to a fixed, constant value (exact rule),
      * the template placeholder paragraphs are removed,
      * the text paragraph is added first (justified, Times New Roman 12pt),
      * the image is added below, scaled to fit the remaining height,
      * cell content is vertically centered so short content still looks fine.

    Because the row height is exact and the content is sized to fit, the
    diagram_page frame never changes size and nothing overflows to a new page.

    Args:
        doc: The Document object that already contains the copied diagram table
        diagram_data: Dictionary containing 'text' and 'image' data from media server
    """
    try:
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Pt, RGBColor, Inches

        text_content = (diagram_data.get('text') or '').strip()
        image_data = diagram_data.get('image') or {}
        image_url = image_data.get('url')

        if not text_content and not image_url:
            return

        image_bytes = None
        original_width = original_height = 0
        if image_url:
            image_bytes = _download_image_from_url(image_url)
            if image_bytes:
                try:
                    with PILImage.open(BytesIO(image_bytes)) as img:
                        original_width, original_height = img.size
                except Exception as e:
                    logger.error(f"Error reading diagram image dimensions: {e}")
                    image_bytes = None

        tables = doc.tables
        if not tables:
            logger.warning("No tables found for diagram content insertion")
            return
        table = tables[-1]
        if len(table.rows) < 2:
            logger.warning("Diagram table has no drawing row, skipping content insertion")
            return

        row = table.rows[1]
        cell = row.cells[0]

        # Remove the template's placeholder paragraphs (they would stretch the
        # frame); the row height is fixed by the exact rule below instead.
        for p in list(cell.paragraphs):
            p._p.getparent().remove(p._p)

        # Pin the frame height so it is constant regardless of content.
        tr_pr = row._tr.get_or_add_trPr()
        tr_height = tr_pr.find(qn('w:trHeight'))
        if tr_height is None:
            tr_height = OxmlElement('w:trHeight')
            tr_pr.append(tr_height)
        tr_height.set(qn('w:val'), str(int(DIAGRAM_DRAWING_ROW_HEIGHT_IN * 1440)))
        tr_height.set(qn('w:hRule'), 'exact')

        row_height_in = DIAGRAM_DRAWING_ROW_HEIGHT_IN
        cell_v_pad = 0.16
        max_width_in = 7.2

        # ---- TEXT first (top-aligned, styled). --------------------------------
        text_h = 0.0
        blocks = _clean_diagram_blocks(_parse_diagram_text(text_content))
        if blocks:
            # Text budget: up to 50% of the frame when an image is present;
            # otherwise as much of the frame as is available. Without an
            # image the text is never truncated while it still fits: the font
            # shrinks first (down to 6pt) so all of the user's text is kept.
            text_max_in = (row_height_in * 0.5) if image_bytes else (row_height_in - cell_v_pad - 0.25)
            hard_max_in = row_height_in if not image_bytes else text_max_in

            body_size_pt = 12
            while body_size_pt >= 6:
                if _estimate_diagram_text_height(blocks, body_size_pt, 7.55) <= text_max_in:
                    break
                body_size_pt -= 1
            if body_size_pt < 6:
                body_size_pt = 6

            # Absolute last resort: trailing blocks are only dropped if even the
            # minimum font size cannot fit them within the frame (or the
            # image's share); a single giant block is capped (its beginning is
            # kept) so the diagram_page frame stays on one page.
            remaining_blocks = list(blocks)
            while remaining_blocks and _estimate_diagram_text_height(
                    remaining_blocks, body_size_pt, 7.55) > hard_max_in:
                if len(remaining_blocks) == 1:
                    remaining_blocks = [_cap_diagram_block_to_height(
                        remaining_blocks[0], body_size_pt, hard_max_in, 7.55)]
                    break
                remaining_blocks.pop()
            blocks = remaining_blocks

            for blk in blocks:
                if blk['kind'] == 'blank':
                    continue
                heading = blk['kind'] == 'heading'
                size_pt = body_size_pt + 2 if heading else body_size_pt
                p = cell.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if heading else WD_ALIGN_PARAGRAPH.JUSTIFY
                if heading:
                    p.paragraph_format.space_before = Pt(6)
                    p.paragraph_format.space_after = Pt(3)
                else:
                    p.paragraph_format.line_spacing = 1.2
                    p.paragraph_format.space_after = Pt(4)
                for bold, seg in blk['segments']:
                    run = p.add_run(seg)
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(size_pt)
                    run.font.color.rgb = RGBColor(0, 0, 0)
                    run.bold = heading or bold
            text_h = _estimate_diagram_text_height(blocks, body_size_pt, 7.55)
            logger.info(
                f"Added diagram text into drawing cell ({len(blocks)} blocks, "
                f"est. {text_h:.2f}in, body {body_size_pt}pt)")

        # ---- IMAGE below the text, sized to the remaining frame height. --------
        if image_bytes and original_width and original_height:
            avail_h = max(0.35, row_height_in - text_h - cell_v_pad - 0.2)
            scale = min(
                max_width_in / (original_width / 96.0),
                avail_h / (original_height / 96.0),
            )
            width_inches = (original_width / 96.0) * scale
            height_inches = (original_height / 96.0) * scale

            p = cell.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            run = p.add_run()
            run.add_picture(BytesIO(image_bytes), width=Inches(width_inches),
                            height=Inches(height_inches))
            logger.info(
                f"Inserted diagram image into drawing cell: "
                f"{width_inches:.2f}x{height_inches:.2f}in "
                f"(avail_h {avail_h:.2f}in)")

        # Text sticks to the top of the frame with a small margin; when there
        # is no text the image is vertically centered as before.
        cell.vertical_alignment = (
            WD_CELL_VERTICAL_ALIGNMENT.TOP if text_content
            else WD_CELL_VERTICAL_ALIGNMENT.CENTER
        )

    except Exception as e:
        logger.error(f"Error inserting diagram content into drawing cell: {e}")


def _append_diagram_page_to_docx(doc, is_last_diagram=False, diagram_data=None):
    """Append Diagram_page.docx as its OWN Word section.

    Word stores page size/margins per *section*, not per page. The old version
    tried to swap margins on the single section and swap them back, which does
    nothing (only the final values are saved), so the diagram inherited the
    report's 1" margins and overflowed onto a second page.

    This version:
      1. closes the report's section with a section break (report margins kept),
      2. inserts the diagram table + its trailing paragraph untouched,
      3. gives the diagram its own section using the ORIGINAL sectPr from
         Diagram_page.docx (page size, margins, header/footer distance),
      4. pins the few things that would otherwise change when the table moves
         into another document (theme font, paragraph spacing, table indent
         under a different Word compatibility mode).

    Sections start on a new page by default, so no manual page breaks are
    needed and the report content that follows starts on a fresh page with its
    own margins.

    is_last_diagram=True  -> the diagram section becomes the document's final
                             section (no trailing blank section/page).
    is_last_diagram=False -> the diagram section is closed with a section break,
                             so more report content can follow it.
    """
    import re
    from copy import deepcopy
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    try:
        diagram_path = _diagram_docx_path()
        if not os.path.exists(diagram_path):
            logger.warning(f"Diagram DOCX not found at {diagram_path}, skipping diagram insertion")
            return

        src = Document(diagram_path)
        src_body = src.element.body
        src_sectPr = src_body.find(qn('w:sectPr'))
        if src_sectPr is None:
            logger.warning("Diagram DOCX has no section properties, skipping diagram insertion")
            return

        body = doc.element.body
        body_sectPr = body.find(qn('w:sectPr'))
        if body_sectPr is None:
            body_sectPr = OxmlElement('w:sectPr')
            body.append(body_sectPr)

        # ---------- helpers -------------------------------------------------
        W14 = 'http://schemas.microsoft.com/office/word/2010/wordml'

        def _compat_mode(document):
            for el in document.settings.element.iter(qn('w:compatSetting')):
                if el.get(qn('w:name')) == 'compatibilityMode':
                    try:
                        return int(el.get(qn('w:val')))
                    except (TypeError, ValueError):
                        pass
            return 12  # Word's behaviour when the setting is absent

        def _theme_minor_font(document):
            """Body font the diagram resolves to through its theme (e.g. Calibri)."""
            try:
                for rel in document.part.rels.values():
                    if rel.reltype.endswith('/theme'):
                        blob = rel.target_part.blob.decode('utf-8', 'ignore')
                        m = re.search(r'<a:minorFont>\s*<a:latin typeface="([^"]+)"', blob)
                        if m:
                            return m.group(1)
            except Exception:
                pass
            return 'Calibri'

        def _insert_in_pPr(pPr, new_el, before_tags):
            """Insert new_el before the first child whose tag is in before_tags (schema order)."""
            wanted = {qn(t) for t in before_tags}
            for child in pPr:
                if child.tag in wanted:
                    child.addprevious(new_el)
                    return
            pPr.append(new_el)

        def _get_pPr(p):
            pPr = p.find(qn('w:pPr'))
            if pPr is None:
                pPr = OxmlElement('w:pPr')
                p.insert(0, pPr)
            return pPr

        def _pin_rfonts(rPr, font):
            if rPr.find(qn('w:rFonts')) is not None:
                return
            rf = OxmlElement('w:rFonts')
            for attr in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
                rf.set(qn(attr), font)
            rstyle = rPr.find(qn('w:rStyle'))
            if rstyle is not None:
                rstyle.addnext(rf)
            else:
                rPr.insert(0, rf)

        after_spacing = ['w:ind', 'w:contextualSpacing', 'w:mirrorIndents',
                         'w:suppressOverlap', 'w:jc', 'w:textDirection',
                         'w:textAlignment', 'w:textboxTightWrap', 'w:outlineLvl',
                         'w:divId', 'w:cnfStyle', 'w:rPr', 'w:sectPr', 'w:pPrChange']
        before_rpr = ['w:sectPr', 'w:pPrChange']

        diagram_font = _theme_minor_font(src)
        src_mode = _compat_mode(src)
        dst_mode = _compat_mode(doc)

        # ---------- 1. close the report's section --------------------------------
        # Tiny paragraph carrying a copy of the report's section properties.
        # (Word needs a paragraph after a table anyway; it is made ~1pt high so
        # it can never push an almost-full report page onto an extra page.)
        closer = OxmlElement('w:p')
        c_pPr = OxmlElement('w:pPr')
        sp = OxmlElement('w:spacing')
        sp.set(qn('w:before'), '0')
        sp.set(qn('w:after'), '0')
        sp.set(qn('w:line'), '20')
        sp.set(qn('w:lineRule'), 'exact')
        c_pPr.append(sp)
        c_rPr = OxmlElement('w:rPr')
        c_sz = OxmlElement('w:sz')
        c_sz.set(qn('w:val'), '2')
        c_rPr.append(c_sz)
        c_pPr.append(c_rPr)
        c_pPr.append(deepcopy(body_sectPr))   # <- report section ends here
        closer.append(c_pPr)
        body_sectPr.addprevious(closer)

        # ---------- 2. Add diagram content from media server if available ----------
        # We'll store the diagram data to add it after the template is copied
        # This ensures we maintain the existing template structure
        stored_diagram_data = diagram_data
        
        # ---------- 3. copy the diagram content, untouched ----------------------
        copied = []
        for child in list(src_body):
            if child.tag == qn('w:sectPr'):
                continue
            el = deepcopy(child)

            # duplicate w14:paraId/textId across several diagrams -> drop them
            for node in el.iter():
                for attr in ('paraId', 'textId'):
                    node.attrib.pop('{%s}%s' % (W14, attr), None)

            if el.tag == qn('w:tbl'):
                # keep the table's left edge where it is in Diagram_page.docx:
                # Word >= 2013 (mode 15) measures tblInd to the cell edge,
                # older modes measure to the text edge (edge + left cell margin).
                if src_mode != dst_mode and (src_mode >= 15) != (dst_mode >= 15):
                    tblPr = el.find(qn('w:tblPr'))
                    ind = tblPr.find(qn('w:tblInd')) if tblPr is not None else None
                    if ind is not None:
                        cell_pad = 108
                        cur = int(ind.get(qn('w:w'), '0'))
                        ind.set(qn('w:w'), str(cur + cell_pad if src_mode >= 15 else cur - cell_pad))

                # inside the table the diagram gets 0pt spacing / single line from
                # the Table Grid style: pin it so it cannot change in this document
                for p in el.iter(qn('w:p')):
                    pPr = _get_pPr(p)
                    if pPr.find(qn('w:spacing')) is None:
                        s = OxmlElement('w:spacing')
                        s.set(qn('w:after'), '0')
                        s.set(qn('w:line'), '240')
                        s.set(qn('w:lineRule'), 'auto')
                        _insert_in_pPr(pPr, s, after_spacing)

            # pin the diagram's own font (theme fonts differ between documents;
            # this also fixes the height of the empty paragraphs in the table)
            for p in list(el.iter(qn('w:p'))):
                pPr = _get_pPr(p)
                mark_rPr = pPr.find(qn('w:rPr'))
                if mark_rPr is None:
                    mark_rPr = OxmlElement('w:rPr')
                    _insert_in_pPr(pPr, mark_rPr, before_rpr)
                _pin_rfonts(mark_rPr, diagram_font)
            for r in el.iter(qn('w:r')):
                rPr = r.find(qn('w:rPr'))
                if rPr is None:
                    rPr = OxmlElement('w:rPr')
                    r.insert(0, rPr)
                _pin_rfonts(rPr, diagram_font)

            body_sectPr.addprevious(el)
            copied.append(el)

        # ---------- 3. Add diagram content from media server if available ----------
        if diagram_data and diagram_data.get('exists'):
            _add_diagram_content_to_drawing_cell(doc, diagram_data)

        # ---------- 4. give the diagram its own section -------------------------
        diagram_sectPr = deepcopy(src_sectPr)   # original size + margins, byte-for-byte

        if is_last_diagram:
            # diagram section is the final one: it takes over the body-level sectPr
            body_sectPr.addprevious(diagram_sectPr)
            body.remove(body_sectPr)
        else:
            # more content will follow: end the diagram section on its last paragraph
            last = copied[-1] if copied else None
            if last is None or last.tag != qn('w:p'):
                last = OxmlElement('w:p')
                body_sectPr.addprevious(last)
            _get_pPr(last).append(diagram_sectPr)   # sectPr is last child of pPr

    except Exception as e:
        logger.error(f"Error appending diagram page to DOCX: {e}")


def export_weekly_report_pdf(weekly_report):
    """Export weekly report as PDF in CoET format with diagram page appended."""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate
    from reportlab.lib.units import inch
    from io import BytesIO
    
    buffer = BytesIO()
    # Match typical DOCX defaults: 1 inch margins
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    
    # Generate elements with title included
    elements = _generate_weekly_report_pdf_elements(weekly_report, doc, include_title=True)
    
    # Build the PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    # Fetch diagram data from media server
    diagram_data = _get_diagram_data(weekly_report.id)
    
    # Append diagram page after the weekly report
    pdf_with_diagram = _append_diagram_page_to_pdf(pdf, diagram_data)
    
    return pdf_with_diagram

def _add_weekly_report_content_to_docx(doc, weekly_report, include_title=True):
    """Add weekly report content to a DOCX document. Can be used for single exports or logbook."""
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    
    # Title (only if requested)
    if include_title:
        title = doc.add_heading('College of Engineering and Technology (CoET)', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Set font for title - black color, no line below
        for run in title.runs:
            run.font.name = 'Times New Roman'
            run.font.size = Pt(16)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0, 0, 0)  # Black color
        
        # Remove line below heading
        try:
            from docx.oxml import OxmlElement
            from docx.oxml.ns import qn
            
            # Get or create paragraph properties
            if title._element.pPr is None:
                pPr = OxmlElement('w:pPr')
                title._element.insert(0, pPr)
            else:
                pPr = title._element.pPr
            
            # Remove bottom border if it exists
            pBdr = pPr.find(qn('w:pBdr'))
            if pBdr is not None:
                pPr.remove(pBdr)
            
            # Explicitly set bottom border to none to override any style-based borders
            pBdr = OxmlElement('w:pBdr')
            bottom = OxmlElement('w:bottom')
            bottom.set(qn('w:val'), 'none')
            pBdr.append(bottom)
            pPr.append(pBdr)
        except Exception:
            pass  # If border removal fails, continue with font color changes
        
        # Set spacing after to reduce gap
        title.paragraph_format.space_after = Pt(12)
        
        # Set line spacing for title
        title.paragraph_format.line_spacing = 1.5
    
    # Weekly Report Header
    daily_reports = weekly_report.get_daily_reports()
    total_hours = sum(report.hours_spent for report in daily_reports)
    
    report_header = doc.add_heading(f'Weekly Report No: {weekly_report.week_number} from: {weekly_report.start_date.strftime("%d-%m-%Y")} to: {weekly_report.end_date.strftime("%d-%m-%Y")}', level=1)
    
    # Set font for header - black color
    for run in report_header.runs:
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 0, 0)  # Black color
    
    # Remove line below heading
    try:
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        
        # Get or create paragraph properties
        if report_header._element.pPr is None:
            pPr = OxmlElement('w:pPr')
            report_header._element.insert(0, pPr)
        else:
            pPr = report_header._element.pPr
        
        # Remove bottom border if it exists
        pBdr = pPr.find(qn('w:pBdr'))
        if pBdr is not None:
            pPr.remove(pBdr)
        
        # Explicitly set bottom border to none to override any style-based borders
        pBdr = OxmlElement('w:pBdr')
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'), 'none')
        pBdr.append(bottom)
        pPr.append(pBdr)
    except Exception:
        pass  # If border removal fails, continue with font color changes
    
    # Set line spacing for header
    report_header.paragraph_format.line_spacing = 1.5

    # Page/layout helpers - defined here so both the daily and operations sections can use them
    section = doc.sections[0]
    # EMU per inch constant used by python-docx
    EMU_PER_INCH = 914400
    content_width_inches = (section.page_width - section.left_margin - section.right_margin) / EMU_PER_INCH

    # Approximate text width in inches for Times New Roman 12pt
    def approx_inch_width(text: str, per_char=0.09, base_padding=0.3) -> float:
        return max(base_padding + len(str(text)) * per_char, 0.0)

    # Force fixed column widths on a table. Word ignores column widths unless
    # autofit is off AND every cell has an explicit width.
    def _set_fixed_column_widths(table, widths_inches: list) -> None:
        table.autofit = False
        table.allow_autofit = False
        for idx, width in enumerate(widths_inches):
            table.columns[idx].width = Inches(width)
            for row in table.rows:
                row.cells[idx].width = Inches(width)

    # python-docx has no public API for table alignment, so set w:jc directly.
    def _set_table_alignment(table, alignment: str) -> None:
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        tblPr = table._tbl.tblPr
        jc = tblPr.find(qn('w:jc'))
        if jc is None:
            jc = OxmlElement('w:jc')
            tblPr.append(jc)
        jc.set(qn('w:val'), alignment)

    # Daily Reports Section - No "Weekly Work Summary" heading
    if daily_reports.exists():
        # Create daily reports table with dynamically computed column widths
        daily_table = doc.add_table(rows=1, cols=3)
        daily_table.style = 'Table Grid'

        # Build datasets to estimate tight widths
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

        # Fixed small Day/Hours columns so the Description column gets the rest
        day_col_in = 1.0  # enough for "Wednesday" + Word cell margins on one line
        hours_col_in = 0.65
        description_col_in = max(content_width_inches - day_col_in - hours_col_in, 2.5)
        
        # Header
        header_row = daily_table.rows[0]
        header_row.cells[0].text = 'Day'
        header_row.cells[1].text = 'Brief description of work performed'
        header_row.cells[2].text = 'Hours'
        
        # Set font properties for header cells
        for cell in header_row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0, 0, 0)  # Black color
                paragraph.paragraph_format.line_spacing = 1.5
        
        # Day mapping
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        
        # Data rows
        for i, report in enumerate(daily_reports):
            row = daily_table.add_row()
            day_name = day_names[i] if i < len(day_names) else report.date.strftime('%A')
            row.cells[0].text = day_name
            row.cells[1].text = report.description
            row.cells[2].text = str(report.hours_spent)
            
            # Set font and formatting for table cells
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = 'Times New Roman'
                        run.font.size = Pt(12)
                        run.font.color.rgb = RGBColor(0, 0, 0)  # Black color
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    paragraph.paragraph_format.line_spacing = 1.5
            
            # Set word wrapping for description column to prevent overflow
            row.cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        # Add total row
        total_row = daily_table.add_row()
        total_row.cells[0].text = ''
        total_row.cells[1].text = 'Total hrs'
        total_row.cells[2].text = str(total_hours)
        
        # Set line spacing and black color for total row cells
        for cell in total_row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.color.rgb = RGBColor(0, 0, 0)  # Black color
                paragraph.paragraph_format.line_spacing = 1.5

        _set_fixed_column_widths(daily_table, [day_col_in, description_col_in, hours_col_in])
    
    # Main Job and Operations Section - Independent section
    if hasattr(weekly_report, 'main_job') and weekly_report.main_job:
        # Add space before main job section
        doc.add_paragraph()
        
        # Create main job title as a heading (not table)
        main_job_title = weekly_report.main_job.title or "Sequence of Operations"
        main_job_heading = doc.add_heading(main_job_title, level=1)
        
        # Set font for main job heading - black color
        for run in main_job_heading.runs:
            run.font.name = 'Times New Roman'
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0, 0, 0)  # Black color
        
        # Remove line below heading
        try:
            from docx.oxml import OxmlElement
            from docx.oxml.ns import qn
            
            # Get or create paragraph properties
            if main_job_heading._element.pPr is None:
                pPr = OxmlElement('w:pPr')
                main_job_heading._element.insert(0, pPr)
            else:
                pPr = main_job_heading._element.pPr
            
            # Remove bottom border if it exists
            pBdr = pPr.find(qn('w:pBdr'))
            if pBdr is not None:
                pPr.remove(pBdr)
            
            # Explicitly set bottom border to none to override any style-based borders
            pBdr = OxmlElement('w:pBdr')
            bottom = OxmlElement('w:bottom')
            bottom.set(qn('w:val'), 'none')
            pBdr.append(bottom)
            pPr.append(pBdr)
        except Exception:
            pass  # If border removal fails, continue with font color changes
        
        # Set line spacing for main job heading
        main_job_heading.paragraph_format.line_spacing = 1.5
        
        # Create operations table with proper column widths
        operations_table = doc.add_table(rows=1, cols=3)
        operations_table.style = 'Table Grid'

        # Compute available width again
        content_width_inches = (section.page_width - section.left_margin - section.right_margin) / EMU_PER_INCH

        actual_operations = weekly_report.main_job.operations.all().order_by('step_number')
        tools_samples = ['Tools, Machinery, Equipment'] + [(op.tools_used or '') for op in actual_operations]

        # Keep the No column small; let the Operation column take the remaining width
        no_col_in = 0.6
        tools_col_in = min(max(max(approx_inch_width(t) for t in tools_samples), 1.0), 2.0)
        operation_col_in = max(content_width_inches - no_col_in - tools_col_in, 3.0)
        
        # Header
        header_row = operations_table.rows[0]
        header_row.cells[0].text = 'No'
        header_row.cells[1].text = 'Operation'
        header_row.cells[2].text = 'Tools, Machinery, Equipment'
        
        # Set font properties for header cells
        for cell in header_row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0, 0, 0)  # Black color
                paragraph.paragraph_format.line_spacing = 1.5
        
        # Get actual operations from database - no mock data
        actual_operations = weekly_report.main_job.operations.all().order_by('step_number')
        
        if actual_operations.exists():
            # Use actual operations from database
            for operation in actual_operations:
                row = operations_table.add_row()
                row.cells[0].text = str(operation.step_number)
                row.cells[1].text = operation.operation_description or ''
                row.cells[2].text = operation.tools_used or ''
                
                # Set word wrapping, line spacing and black color for operation and tools columns
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.color.rgb = RGBColor(0, 0, 0)  # Black color
                row.cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
                row.cells[1].paragraphs[0].paragraph_format.line_spacing = 1.5
                row.cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
                row.cells[2].paragraphs[0].paragraph_format.line_spacing = 1.5
        else:
            # If no operations exist, show empty table with just header
            row = operations_table.add_row()
            row.cells[0].text = ''
            row.cells[1].text = ''
            row.cells[2].text = ''

        _set_fixed_column_widths(operations_table, [no_col_in, operation_col_in, tools_col_in])

    # Signature section - Create a small table for signature (right half)
    doc.add_paragraph()  # Add space before signature table
    
    # Create signature table (smaller size)
    signature_table = doc.add_table(rows=2, cols=2)
    signature_table.style = 'Table Grid'

    # Add signature content - Row 1 holds the labels, Row 2 is left blank for entries
    signature_table.rows[0].cells[0].text = 'Signature Training Officer:'
    signature_table.rows[0].cells[1].text = 'Date:'
    signature_table.rows[1].cells[0].text = ''
    signature_table.rows[1].cells[1].text = ''

    # Signature column stays 2.592" so the long label "Signature Training Officer:"
    # fits horizontally; Date column stays at 1.2".
    _set_fixed_column_widths(signature_table, [2.592, 1.2])
    _set_table_alignment(signature_table, 'right')  # right side, matching the PDF layout
    
    # Set font, black color and line spacing for signature table
    for row in signature_table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(12)
                    run.font.color.rgb = RGBColor(0, 0, 0)  # Black color
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                paragraph.paragraph_format.line_spacing = 1.5


def export_weekly_report_docx(weekly_report):
    """Export weekly report as DOCX in CoET format with diagram page appended."""
    from docx import Document
    from docx.shared import Inches
    from io import BytesIO
    
    doc = Document()
    
    # Set document margins to 1 inch to match PDF
    from docx.shared import Pt
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Add weekly report content with title included
    _add_weekly_report_content_to_docx(doc, weekly_report, include_title=True)
    
    # Fetch diagram data from media server
    diagram_data = _get_diagram_data(weekly_report.id)
    
    # Append diagram page after the signature section (is_last_diagram=True for single export)
    # This now uses the improved section-based approach
    _append_diagram_page_to_docx(doc, is_last_diagram=True, diagram_data=diagram_data)
    
    # Save to buffer
    buffer = BytesIO()
    doc.save(buffer)
    docx_content = buffer.getvalue()
    buffer.close()
    return docx_content

def export_general_report_pdf(general_report):
    """Export general report to PDF format."""
    try:
        context = {
            'general_report': general_report,
        }
        
        html_content = render_to_string('exports/general_report.html', context)
        
        # Create a simple text response for now
        response = HttpResponse(html_content, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename="general_report.html"'
        return response
        
    except Exception as e:
        logger.error(f"Error exporting general report PDF: {e}")
        raise

def export_general_report_docx(general_report):
    """Export general report to DOCX format."""
    try:
        from docx.shared import Pt, RGBColor
        doc = Document()

        # Add title
        title = doc.add_heading(general_report.title, 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Set black font for title
        for run in title.runs:
            run.font.color.rgb = RGBColor(0, 0, 0)  # Black color
        
        # Remove line below heading
        try:
            from docx.oxml import OxmlElement
            from docx.oxml.ns import qn
            
            # Get or create paragraph properties
            if title._element.pPr is None:
                pPr = OxmlElement('w:pPr')
                title._element.insert(0, pPr)
            else:
                pPr = title._element.pPr
            
            # Remove bottom border if it exists
            pBdr = pPr.find(qn('w:pBdr'))
            if pBdr is not None:
                pPr.remove(pBdr)
            
            # Explicitly set bottom border to none to override any style-based borders
            pBdr = OxmlElement('w:pBdr')
            bottom = OxmlElement('w:bottom')
            bottom.set(qn('w:val'), 'none')
            pBdr.append(bottom)
            pPr.append(pBdr)
        except Exception:
            pass  # If border removal fails, continue with font color changes

        # Add sections
        sections = [
            ('Introduction', general_report.introduction),
            ('Company Overview', general_report.company_overview),
            ('Training Objectives', general_report.training_objectives),
            ('Methodology', general_report.methodology),
            ('Achievements', general_report.achievements),
            ('Challenges Faced', general_report.challenges_faced),
            ('Skills Acquired', general_report.skills_acquired),
            ('Recommendations', general_report.recommendations),
            ('Conclusion', general_report.conclusion),
            ('Acknowledgments', general_report.acknowledgments),
        ]

        for section_title, section_content in sections:
            if section_content:
                heading = doc.add_heading(section_title, level=1)
                # Set black font for headings
                for run in heading.runs:
                    run.font.color.rgb = RGBColor(0, 0, 0)  # Black color
                
                # Remove line below heading
                try:
                    from docx.oxml import OxmlElement
                    from docx.oxml.ns import qn
                    
                    # Get or create paragraph properties
                    if heading._element.pPr is None:
                        pPr = OxmlElement('w:pPr')
                        heading._element.insert(0, pPr)
                    else:
                        pPr = heading._element.pPr
                    
                    # Remove bottom border if it exists
                    pBdr = pPr.find(qn('w:pBdr'))
                    if pBdr is not None:
                        pPr.remove(pBdr)
                    
                    # Explicitly set bottom border to none to override any style-based borders
                    pBdr = OxmlElement('w:pBdr')
                    bottom = OxmlElement('w:bottom')
                    bottom.set(qn('w:val'), 'none')
                    pBdr.append(bottom)
                    pPr.append(pBdr)
                except Exception:
                    pass  # If border removal fails, continue with font color changes
                
                paragraph = doc.add_paragraph(section_content)
                # Set black font for paragraph text
                for run in paragraph.runs:
                    run.font.color.rgb = RGBColor(0, 0, 0)  # Black color

        # Save to buffer
        buffer = BytesIO()
        doc.save(buffer)
        docx_content = buffer.getvalue()
        buffer.close()
        return docx_content

    except Exception as e:
        logger.error(f"Error exporting general report DOCX: {e}")
        raise


def export_all_weekly_reports_pdf(weekly_reports):
    """Export all weekly reports as a combined PDF (logbook) with diagram pages and filtering."""
    from reportlab.platypus import SimpleDocTemplate, PageBreak
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    # Filter out weeks without daily reports
    weekly_reports_with_data = [
        wr for wr in weekly_reports 
        if wr.get_daily_reports().exists()
    ]
    
    if not weekly_reports_with_data:
        logger.warning("No weekly reports with daily reports found for logbook export")
        # Return empty PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=inch,
            rightMargin=inch,
            topMargin=inch,
            bottomMargin=inch,
        )
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph("No weekly reports with data available.", styles['Normal']))
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        return pdf

    # Create individual PDFs for each weekly report with diagrams, then merge them
    # This approach ensures proper diagram placement after each report's signature section
    individual_pdfs = []
    
    for weekly_report in weekly_reports_with_data:
        # Generate individual weekly report PDF with diagram
        individual_pdf = export_weekly_report_pdf(weekly_report)
        individual_pdfs.append(individual_pdf)
    
    # Merge all PDFs: individual reports with diagrams (no title page)
    try:
        writer = PdfWriter()
        
        # Add each individual weekly report PDF (which already includes the diagram)
        for individual_pdf in individual_pdfs:
            individual_reader = PdfReader(BytesIO(individual_pdf))
            for page in individual_reader.pages:
                writer.add_page(page)
        
        # Write the combined PDF
        output_buffer = BytesIO()
        writer.write(output_buffer)
        combined_pdf = output_buffer.getvalue()
        output_buffer.close()
        
        return combined_pdf
    except Exception as e:
        logger.error(f"Error merging PDFs for logbook: {e}")
        # Fallback: return just the first individual PDF
        return individual_pdfs[0] if individual_pdfs else b''


def export_all_weekly_reports_docx(weekly_reports):
    """Export all weekly reports as a combined DOCX (logbook).

    Every weekly report is written straight into ONE document, and each report is
    followed by its diagram page in its own section. (The old version built one
    DOCX per report and then glued their XML together, which dropped the section
    settings, appended content after the final <w:sectPr> and piled every page
    break at the top of the file -> blank pages and a broken diagram layout.)
    """
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    # Filter out weeks without daily reports
    weekly_reports_with_data = [
        wr for wr in weekly_reports
        if wr.get_daily_reports().exists()
    ]

    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    if not weekly_reports_with_data:
        logger.warning("No weekly reports with daily reports found for logbook export")
        doc.add_paragraph("No weekly reports with data available.")
    else:
        last_index = len(weekly_reports_with_data) - 1
        for i, weekly_report in enumerate(weekly_reports_with_data):
            _add_weekly_report_content_to_docx(doc, weekly_report, include_title=True)
            # Each diagram is its own section (own margins, exactly one page).
            # Sections start on a new page, so the next report begins on a fresh
            # page automatically - no manual page breaks needed.
            _append_diagram_page_to_docx(
                doc, is_last_diagram=(i == last_index),
                diagram_data=_get_diagram_data(weekly_report.id))

    buffer = BytesIO()
    doc.save(buffer)
    docx_content = buffer.getvalue()
    buffer.close()
    return docx_content
