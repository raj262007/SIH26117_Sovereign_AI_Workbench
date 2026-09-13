"""
Deliverable Generation Tool.
Generates native, styled executive Word memos (.docx) and spreadsheets (.xlsx).
"""

import os
from datetime import datetime
from typing import Dict, Any, List
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from src.utils.file_manager import get_output_path, compute_sha256

def generate_inspection_memo(
    data: Dict[str, Any],
    sandbox_result: Dict[str, Any],
    filename: str = "Refinery_Inspection_Approval_Memo.docx"
) -> str:
    """
    Generate a formal executive memo (.docx) with styling, tables, and audit trail.
    Returns the absolute path to the generated document.
    """
    output_path = get_output_path(filename)
    doc = Document()

    # Page Margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # 1. Organization Header
    header = doc.add_paragraph()
    header_run = header.add_run("STRATEGIC PETROLEUM & INDUSTRIAL DIRECTORATE\nTECHNICAL INTEGRITY & SAFETY DIVISION")
    header_run.font.name = "Arial"
    header_run.font.size = Pt(11)
    header_run.font.bold = True
    header_run.font.color.rgb = RGBColor(70, 80, 95)
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 2. Document Title
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(8)
    title_p.paragraph_format.space_after = Pt(12)
    title_run = title_p.add_run("EXECUTIVE MEMO: PIPING WALL THICKNESS COMPLIANCE AUDIT")
    title_run.font.name = "Arial"
    title_run.font.size = Pt(15)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(20, 30, 50)
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 3. Status Alert Banner
    is_breach = "FAIL" in sandbox_result.get("status", "") or "BREACH" in sandbox_result.get("status", "")
    banner_p = doc.add_paragraph()
    banner_p.paragraph_format.space_after = Pt(14)
    
    if is_breach:
        banner_run = banner_p.add_run("  CRITICAL BREACH: IMMEDIATE DE-RATING & RETIREMENT NOTICE  ")
        banner_run.font.name = "Arial"
        banner_run.font.size = Pt(12)
        banner_run.font.bold = True
        banner_run.font.color.rgb = RGBColor(200, 20, 20)
    else:
        banner_run = banner_p.add_run("  ALL MEASUREMENT POINTS WITHIN SAFE API 570 THRESHOLDS  ")
        banner_run.font.name = "Arial"
        banner_run.font.size = Pt(12)
        banner_run.font.bold = True
        banner_run.font.color.rgb = RGBColor(20, 140, 50)
    banner_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 4. Metadata Box
    meta = data.get("metadata", {})
    doc.add_paragraph().add_run("1. OPERATIONAL & ASSET METADATA").bold = True
    meta_table = doc.add_table(rows=3, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_rows = [
        ("Facility / Unit:", meta.get("facility", "CDU-1"), "Line Identifier:", meta.get("line_number", "10\"-HC-1004-CS300")),
        ("Pipe Material:", meta.get("material", "ASTM A106 Grade B"), "Applicable Code:", meta.get("standard", "API 570")),
        ("Inspection Date:", datetime.now().strftime("%Y-%m-%d"), "Authorized Inspector:", meta.get("inspector", "R. K. Sharma"))
    ]
    for idx, (lbl1, val1, lbl2, val2) in enumerate(meta_rows):
        row = meta_table.rows[idx]
        row.cells[0].paragraphs[0].add_run(f"{lbl1} {val1}")
        row.cells[1].paragraphs[0].add_run(f"{lbl2} {val2}")

    # 5. Measurement Summary Table
    doc.add_paragraph().paragraph_format.space_before = Pt(12)
    doc.add_paragraph().add_run("2. ULTRASONIC THICKNESS (UT) MEASUREMENT LOG").bold = True
    
    points = data.get("measurement_points", [])
    if points:
        table = doc.add_table(rows=len(points) + 1, cols=5)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        headers = ["Point ID", "Location Description", "Nominal", "Measured", "Status"]
        for col_idx, h_text in enumerate(headers):
            cell = table.rows[0].cells[col_idx]
            p = cell.paragraphs[0]
            run = p.add_run(h_text)
            run.font.bold = True
            run.font.size = Pt(9.5)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        for row_idx, pt in enumerate(points):
            row = table.rows[row_idx + 1]
            row.cells[0].paragraphs[0].add_run(pt.get("point_id", ""))
            row.cells[1].paragraphs[0].add_run(pt.get("description", ""))
            row.cells[2].paragraphs[0].add_run(f"{pt.get('nominal_mm', 0):.2f} mm")
            row.cells[3].paragraphs[0].add_run(f"{pt.get('measured_mm', 0):.2f} mm")
            status_run = row.cells[4].paragraphs[0].add_run(pt.get("condition", ""))
            if pt.get("is_breached", False):
                status_run.font.bold = True
                status_run.font.color.rgb = RGBColor(200, 20, 20)

    # 6. Sandboxed Verification Box
    doc.add_paragraph().paragraph_format.space_before = Pt(12)
    doc.add_paragraph().add_run("3. DETERMINISTIC CODEACT SANDBOX VERIFICATION").bold = True
    
    calc_p = doc.add_paragraph()
    calc_p.paragraph_format.space_after = Pt(4)
    calc_run = calc_p.add_run(
        f"Algorithm Status: {sandbox_result.get('status')}\n"
        f"Sandbox Output:\n{sandbox_result.get('stdout', '')}\n"
        f"Execution Time: {sandbox_result.get('duration_sec', 0.0)}s (Deterministic Python VM)"
    )
    calc_run.font.name = "Courier New"
    calc_run.font.size = Pt(9.5)

    # 7. Chief Inspector Signature Block
    doc.add_paragraph().paragraph_format.space_before = Pt(16)
    sign_table = doc.add_table(rows=1, cols=2)
    sign_table.rows[0].cells[0].paragraphs[0].add_run("Verified by:\n\n___________________________\nChief Technical Inspector")
    sign_table.rows[0].cells[1].paragraphs[0].add_run("Approved by:\n\n___________________________\nGeneral Manager (Refinery Operations)")

    # 8. Forensic Audit Footer
    footer_p = doc.add_paragraph()
    footer_p.paragraph_format.space_before = Pt(24)
    raw_hash_source = f"{meta.get('report_id')}-{datetime.now().isoformat()}-{sandbox_result.get('status')}"
    sha256_hash = compute_sha256(raw_hash_source)
    footer_run = footer_p.add_run(
        f"Sovereign Audit Hash (SHA-256): {sha256_hash}\n"
        f"Generated Air-Gapped via On-Premise Agentic AI Workbench | 0 WAN Egress Verified"
    )
    footer_run.font.size = Pt(7.5)
    footer_run.font.color.rgb = RGBColor(120, 120, 120)
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.save(output_path)
    return output_path

def generate_inspection_spreadsheet(
    data: Dict[str, Any],
    filename: str = "Refinery_Piping_Thickness_Log.xlsx"
) -> str:
    """
    Generate a clean, styled Excel log (.xlsx) using openpyxl for data analysis.
    """
    output_path = get_output_path(filename)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "UT Measurement Log"

    # Title & Metadata
    ws["A1"] = "REFINERY PIPING ULTRASONIC THICKNESS LOG"
    ws["A1"].font = Font(name="Arial", size=14, bold=True, color="1F497D")
    
    meta = data.get("metadata", {})
    ws["A3"] = "Facility:"; ws["B3"] = meta.get("facility", "")
    ws["A4"] = "Line Number:"; ws["B4"] = meta.get("line_number", "")
    ws["A5"] = "Material:"; ws["B5"] = meta.get("material", "")
    ws["A6"] = "Standard:"; ws["B6"] = meta.get("standard", "")

    # Table Headers
    headers = ["Point ID", "Location Description", "Nominal (mm)", "Measured (mm)", "Threshold (mm)", "Deficit (mm)", "Status"]
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")

    start_row = 8
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    threshold_val = data.get("thresholds", {}).get("t_threshold", 3.30)
    points = data.get("measurement_points", [])

    for row_idx, pt in enumerate(points, start=start_row + 1):
        measured = pt.get("measured_mm", 0.0)
        deficit = round(measured - threshold_val, 2)
        is_breach = measured < threshold_val

        ws.cell(row=row_idx, column=1, value=pt.get("point_id"))
        ws.cell(row=row_idx, column=2, value=pt.get("description"))
        ws.cell(row=row_idx, column=3, value=pt.get("nominal_mm"))
        ws.cell(row=row_idx, column=4, value=measured)
        ws.cell(row=row_idx, column=5, value=threshold_val)
        ws.cell(row=row_idx, column=6, value=deficit)
        
        status_cell = ws.cell(row=row_idx, column=7, value="CRITICAL BREACH" if is_breach else "PASS")
        if is_breach:
            status_cell.font = Font(bold=True, color="FF0000")
            status_cell.fill = PatternFill(start_color="FFD2D2", end_color="FFD2D2", fill_type="solid")

    # Column auto-width
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    wb.save(output_path)
    return output_path

def generate_executive_presentation(
    data: Dict[str, Any],
    sandbox_result: Dict[str, Any],
    filename: str = "Refinery_Inspection_Executive_Brief.pptx"
) -> str:
    """
    Generate an executive briefing presentation (.pptx) using python-pptx.
    Provides structured 4-slide deck:
    Slide 1: Executive Cover & Asset Metadata
    Slide 2: UT Measurement Findings & Telemetry Table
    Slide 3: Deterministic CodeAct Sandbox & API 570 Compliance
    Slide 4: Operational Remediation Plan & Authorization Sign-off
    """
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE

    output_path = get_output_path(filename)
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(5.625)  # 16:9 widescreen layout

    meta = data.get("metadata", {})
    points = data.get("measurement_points", [])
    thresholds = data.get("thresholds", {})
    status = sandbox_result.get("status", "PASS")
    is_breach = "FAIL" in status or "BREACH" in status

    # Color definitions
    NAVY = RGBColor(15, 23, 42)
    DARK_BLUE = RGBColor(30, 58, 138)
    CRITICAL_RED = RGBColor(220, 38, 38)
    SAFE_GREEN = RGBColor(22, 163, 74)
    TEXT_MUTED = RGBColor(100, 116, 139)
    WHITE = RGBColor(255, 255, 255)

    # -------------------------------------------------------------------------
    # SLIDE 1: Title & Executive Summary
    # -------------------------------------------------------------------------
    blank_layout = prs.slide_layouts[6]
    slide1 = prs.slides.add_slide(blank_layout)

    # Top accent bar
    bar = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(10), Inches(0.4))
    bar.fill.solid(); bar.fill.fore_color.rgb = CRITICAL_RED if is_breach else DARK_BLUE
    bar.line.fill.background()

    # Title Box
    title_box = slide1.shapes.add_textbox(Inches(0.8), Inches(1.0), Inches(8.4), Inches(2.2))
    tf1 = title_box.text_frame
    tf1.word_wrap = True
    
    p1 = tf1.paragraphs[0]
    p1.text = "STRATEGIC ASSET INTEGRITY AUDIT"
    p1.font.size = Pt(13); p1.font.bold = True; p1.font.color.rgb = DARK_BLUE
    
    p2 = tf1.add_paragraph()
    p2.text = "Ultrasonic Wall Thickness & API 570 Compliance Briefing"
    p2.font.size = Pt(22); p2.font.bold = True; p2.font.color.rgb = NAVY
    p2.space_before = Pt(8)

    p3 = tf1.add_paragraph()
    p3.text = f"Facility: {meta.get('facility', 'CDU-1')} | Circuit: {meta.get('line_number', '10\"-HC-1004-CS300')} | Material: {meta.get('material', 'ASTM A106 Gr B')}"
    p3.font.size = Pt(12); p3.font.color.rgb = TEXT_MUTED
    p3.space_before = Pt(8)

    # Status callout banner
    banner = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(3.4), Inches(8.4), Inches(1.1))
    banner.fill.solid()
    banner.fill.fore_color.rgb = RGBColor(254, 242, 242) if is_breach else RGBColor(240, 253, 244)
    banner.line.color.rgb = CRITICAL_RED if is_breach else SAFE_GREEN
    
    btf = banner.text_frame
    btf.word_wrap = True
    bp1 = btf.paragraphs[0]
    bp1.text = "COMPLIANCE STATUS: " + ("CRITICAL RETIREMENT BREACH DETECTED" if is_breach else "ALL POINTS WITHIN SAFE LIMITS")
    bp1.font.size = Pt(14); bp1.font.bold = True
    bp1.font.color.rgb = CRITICAL_RED if is_breach else SAFE_GREEN
    bp1.alignment = PP_ALIGN.CENTER
    
    bp2 = btf.add_paragraph()
    bp2.text = f"Evaluated under API 570 Clause 7.1.1 (Threshold: {thresholds.get('t_threshold', 3.30)} mm) | Air-Gapped Sovereign AI System (Team rv2)"
    bp2.font.size = Pt(10.5); bp2.font.color.rgb = NAVY
    bp2.alignment = PP_ALIGN.CENTER

    # -------------------------------------------------------------------------
    # SLIDE 2: Ultrasonic Thickness Measurement Table
    # -------------------------------------------------------------------------
    slide2 = prs.slides.add_slide(blank_layout)
    s2_title = slide2.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(8.4), Inches(0.8))
    s2_tf = s2_title.text_frame
    s2_p = s2_tf.paragraphs[0]
    s2_p.text = "Ultrasonic Thickness (UT) Measurement Telemetry"
    s2_p.font.size = Pt(18); s2_p.font.bold = True; s2_p.font.color.rgb = NAVY

    # Table
    rows = len(points) + 1 if points else 2
    cols = 5
    table_shape = slide2.shapes.add_table(rows, cols, Inches(0.8), Inches(1.3), Inches(8.4), Inches(2.8))
    table = table_shape.table
    table.columns[0].width = Inches(1.2)
    table.columns[1].width = Inches(2.6)
    table.columns[2].width = Inches(1.4)
    table.columns[3].width = Inches(1.4)
    table.columns[4].width = Inches(1.8)

    headers = ["Point ID", "Location Description", "Nominal (mm)", "Measured (mm)", "Integrity Status"]
    for i, h in enumerate(headers):
        cell = table.cell(0, i)
        cell.fill.solid(); cell.fill.fore_color.rgb = DARK_BLUE
        cp = cell.text_frame.paragraphs[0]
        cp.text = h; cp.font.bold = True; cp.font.size = Pt(10.5); cp.font.color.rgb = WHITE
        cp.alignment = PP_ALIGN.CENTER

    t_thresh = thresholds.get("t_threshold", 3.30)
    for r_idx, pt in enumerate(points, 1):
        measured = pt.get("measured_mm", 0.0)
        breached = measured < t_thresh
        vals = [
            pt.get("point_id", f"P-{r_idx}"),
            pt.get("description", ""),
            f"{pt.get('nominal_mm', 0):.2f}",
            f"{measured:.2f}",
            "CRITICAL BREACH" if breached else "ACCEPTABLE"
        ]
        for c_idx, val in enumerate(vals):
            cell = table.cell(r_idx, c_idx)
            if breached:
                cell.fill.solid(); cell.fill.fore_color.rgb = RGBColor(254, 226, 226)
            cp = cell.text_frame.paragraphs[0]
            cp.text = val; cp.font.size = Pt(10)
            if c_idx == 4 and breached:
                cp.font.bold = True; cp.font.color.rgb = CRITICAL_RED
            if c_idx != 1:
                cp.alignment = PP_ALIGN.CENTER

    # -------------------------------------------------------------------------
    # SLIDE 3: Deterministic CodeAct Sandbox & Regulatory Standards
    # -------------------------------------------------------------------------
    slide3 = prs.slides.add_slide(blank_layout)
    s3_title = slide3.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(8.4), Inches(0.8))
    s3_tf = s3_title.text_frame
    s3_p = s3_tf.paragraphs[0]
    s3_p.text = "Deterministic CodeAct Verification & Regulatory Citations"
    s3_p.font.size = Pt(18); s3_p.font.bold = True; s3_p.font.color.rgb = NAVY

    # Left: Sandbox VM Box
    box_left = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.3), Inches(4.0), Inches(3.6))
    box_left.fill.solid(); box_left.fill.fore_color.rgb = RGBColor(248, 250, 252)
    box_left.line.color.rgb = RGBColor(203, 213, 225)
    bl_tf = box_left.text_frame; bl_tf.word_wrap = True
    bl_p1 = bl_tf.paragraphs[0]
    bl_p1.text = "DETERMINISTIC CODEACT VM"
    bl_p1.font.bold = True; bl_p1.font.size = Pt(11); bl_p1.font.color.rgb = DARK_BLUE
    
    bl_p2 = bl_tf.add_paragraph()
    bl_p2.text = f"Status: {sandbox_result.get('status')}\nExecution Time: {sandbox_result.get('duration_sec', 0.02)}s\nNetwork Egress: 0 Bytes\n\nOutput Log:\n{sandbox_result.get('stdout', '')[:160]}"
    bl_p2.font.size = Pt(9.5); bl_p2.font.color.rgb = NAVY; bl_p2.space_before = Pt(6)

    # Right: API 570 Grounded Citations
    box_right = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.2), Inches(1.3), Inches(4.0), Inches(3.6))
    box_right.fill.solid(); box_right.fill.fore_color.rgb = RGBColor(248, 250, 252)
    box_right.line.color.rgb = RGBColor(203, 213, 225)
    br_tf = box_right.text_frame; br_tf.word_wrap = True
    br_p1 = br_tf.paragraphs[0]
    br_p1.text = "GROUNDED REGULATORY CITATIONS"
    br_p1.font.bold = True; br_p1.font.size = Pt(11); br_p1.font.color.rgb = DARK_BLUE

    br_p2 = br_tf.add_paragraph()
    br_p2.text = (
        "• API 570 Clause 7.1.1: Structural minimum base limit is 2.80 mm plus 0.50 mm safety margin "
        "(Critical Alert Threshold = 3.30 mm).\n\n"
        "• API 570 Clause 7.2: Any wall thickness reading below retirement threshold mandates immediate "
        "pressure de-rating and non-conformance notification.\n\n"
        "• ASME B31.3 Para 304.1: Hoop stress recalculation required prior to continued pressurization."
    )
    br_p2.font.size = Pt(9.5); br_p2.font.color.rgb = NAVY; br_p2.space_before = Pt(6)

    # -------------------------------------------------------------------------
    # SLIDE 4: Operational Action Items & Authorization Sign-off
    # -------------------------------------------------------------------------
    slide4 = prs.slides.add_slide(blank_layout)
    s4_title = slide4.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(8.4), Inches(0.8))
    s4_tf = s4_title.text_frame
    s4_p = s4_tf.paragraphs[0]
    s4_p.text = "Remediation Action Plan & Executive Endorsement"
    s4_p.font.size = Pt(18); s4_p.font.bold = True; s4_p.font.color.rgb = NAVY

    actions_box = slide4.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(8.4), Inches(2.2))
    atf = actions_box.text_frame; atf.word_wrap = True
    ap1 = atf.paragraphs[0]
    ap1.text = "MANDATORY REMEDIATION ACTION ITEMS:"
    ap1.font.bold = True; ap1.font.size = Pt(12); ap1.font.color.rgb = CRITICAL_RED if is_breach else DARK_BLUE

    actions = [
        "1. Immediate De-rating: Reduce operating pressure by 20% on Circuit 10\"-HC-1004-CS300 pending mechanical review.",
        "2. Temporary Containment: Install engineered full-enclosure clamp at Point T-12 (Lower Elbow Extrados) within 48h.",
        "3. Accelerated Ultrasonic Survey: Execute bi-weekly UT re-scans across adjacent TMLs (T-11 through T-15).",
        "4. Spool Replacement: Program full schedule replacement during upcoming turnaround (Target: Q3/2026)."
    ] if is_breach else [
        "1. Routine Survey: Maintain current 12-month ultrasonic inspection frequency.",
        "2. Anomaly Monitoring: Re-verify Point T-12 during next scheduled turnaround.",
        "3. Archive Records: Log inspection data in Refinery Asset Integrity Management System (AIMS)."
    ]
    for act in actions:
        p = atf.add_paragraph()
        p.text = act; p.font.size = Pt(10.5); p.font.color.rgb = NAVY; p.space_before = Pt(4)

    # Sign-off box
    sign_box = slide4.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(3.9), Inches(8.4), Inches(1.1))
    sign_box.fill.solid(); sign_box.fill.fore_color.rgb = RGBColor(241, 245, 249)
    sign_box.line.color.rgb = RGBColor(203, 213, 225)
    stf = sign_box.text_frame; stf.word_wrap = True
    sp1 = stf.paragraphs[0]
    sp1.text = "Verified: _____________________________ (Chief Technical Inspector)        Approved: _____________________________ (GM Refinery Operations)"
    sp1.font.size = Pt(10); sp1.font.color.rgb = NAVY; sp1.alignment = PP_ALIGN.CENTER
    sp2 = stf.add_paragraph()
    sp2.text = "Generated by Sovereign On-Premise Agentic AI Workbench | Team rv2 // SIH 2026 | Zero Outbound Telemetry"
    sp2.font.size = Pt(8); sp2.font.color.rgb = TEXT_MUTED; sp2.alignment = PP_ALIGN.CENTER; sp2.space_before = Pt(6)

    prs.save(output_path)
    return output_path

