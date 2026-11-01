import io
import csv
import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_qr_image_bytes(code_string):
    """Generates a PIL QR code image in memory and returns a ReportLab Image or BytesIO buffer."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=2,
    )
    qr.add_data(code_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

def generate_batch_qr_pdf(batch, unit_codes):
    """Generates a PDF grid sheet of printable QR code labels for a batch using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#0f172a'),
        alignment=1,
        spaceAfter=10
    )
    cell_title_style = ParagraphStyle(
        'CellTitle',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1e293b'),
        fontName='Helvetica-Bold',
        alignment=1
    )
    cell_meta_style = ParagraphStyle(
        'CellMeta',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#475569'),
        alignment=1
    )

    elements = []
    
    # Header
    header_text = f"<b>MediVerify Official Batch QR Labels</b><br/>" \
                  f"Product: {batch.product.brand_name} ({batch.product.strength}) | Batch: {batch.batch_number} | Exp: {batch.expiry_date}"
    elements.append(Paragraph(header_text, title_style))
    elements.append(Spacer(1, 10))

    # Grid cells (3 columns x N rows)
    table_data = []
    row = []

    for uc in unit_codes:
        qr_buf = generate_qr_image_bytes(uc.secure_code)
        img = Image(qr_buf, width=60, height=60)
        
        cell_content = [
            Paragraph(f"<b>{batch.product.brand_name}</b>", cell_title_style),
            img,
            Paragraph(f"Code: <b>{uc.secure_code}</b>", cell_meta_style),
            Paragraph(f"Batch: {batch.batch_number} | Exp: {batch.expiry_date}", cell_meta_style),
        ]
        
        row.append(cell_content)
        if len(row) == 3:
            table_data.append(row)
            row = []
            
    if row:
        while len(row) < 3:
            row.append("")
        table_data.append(row)

    grid_table = Table(table_data, colWidths=[180, 180, 180])
    grid_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    
    elements.append(grid_table)
    doc.build(elements)
    
    buffer.seek(0)
    return buffer.getvalue()

def generate_batch_csv(batch, unit_codes):
    """Generates a CSV export of unit codes for a batch."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Product Brand', 'Generic Name', 'Batch Number', 'Serial Number', 'Secure Verification Code', 'Manufacture Date', 'Expiry Date'])
    
    for uc in unit_codes:
        writer.writerow([
            batch.product.brand_name,
            batch.product.generic_name,
            batch.batch_number,
            uc.serial_number,
            uc.secure_code,
            batch.manufacture_date,
            batch.expiry_date
        ])
        
    return buffer.getvalue()
