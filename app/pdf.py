from __future__ import annotations

from io import BytesIO
from pathlib import Path
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT

FONT_PATH = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
FONT_BOLD_PATH = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
if FONT_PATH.exists():
    pdfmetrics.registerFont(TTFont('DejaVuSans', str(FONT_PATH)))
if FONT_BOLD_PATH.exists():
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', str(FONT_BOLD_PATH)))


def _styles():
    styles = getSampleStyleSheet()
    base = 'DejaVuSans' if FONT_PATH.exists() else 'Helvetica'
    bold = 'DejaVuSans-Bold' if FONT_BOLD_PATH.exists() else 'Helvetica-Bold'
    styles.add(ParagraphStyle(
        name='APTitle',
        fontName=bold,
        fontSize=20,
        leading=24,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name='APSubtitle',
        fontName=base,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#667085'),
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name='APH2',
        fontName=bold,
        fontSize=13,
        leading=17,
        spaceBefore=12,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='APBody',
        fontName=base,
        fontSize=9,
        leading=13,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name='APSmall',
        fontName=base,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#475467'),
    ))
    return styles


def rub(value):
    if value is None:
        return '—'
    try:
        amount = float(value)
    except Exception:
        return str(value)
    return f'{amount:,.0f}'.replace(',', ' ') + ' руб.'


def _p(text: object, style):
    escaped = str(text if text is not None else '—')
    escaped = escaped.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return Paragraph(escaped, style)


def _qr_flowable(url: str):
    qr = qrcode.QRCode(border=1, box_size=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    stream = BytesIO()
    img.save(stream, format='PNG')
    stream.seek(0)
    return Image(stream, width=32*mm, height=32*mm)


def build_passport_pdf(payload: dict, *, public_url: str | None = None, private: bool = False) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14*mm,
        rightMargin=14*mm,
        topMargin=14*mm,
        bottomMargin=14*mm,
        title='AutoPassport',
    )
    styles = _styles()
    story = []
    vehicle = payload['vehicle']
    title = f"AutoPassport: {vehicle.get('make')} {vehicle.get('model')} {vehicle.get('year')}"
    story.append(_p(title, styles['APTitle']))
    mode = 'приватный отчёт владельца' if private else 'публичный паспорт по временной ссылке'
    story.append(_p(f'Формат: {mode}. VIN: {vehicle.get("vin")}. Пробег: {vehicle.get("current_mileage")} км.', styles['APSubtitle']))
    if public_url:
        qr_table = Table([
            [_qr_flowable(public_url), _p(f'Временная публичная ссылка:\n{public_url}', styles['APSmall'])]
        ], colWidths=[38*mm, 130*mm])
        qr_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        story.append(qr_table)
        story.append(Spacer(1, 4*mm))

    story.append(_p('Сводка по автомобилю', styles['APH2']))
    summary_rows = [
        ['Марка', vehicle.get('make')],
        ['Модель', vehicle.get('model')],
        ['Версия', vehicle.get('trim') or '—'],
        ['Год', vehicle.get('year')],
        ['VIN', vehicle.get('vin')],
        ['Текущий пробег', f"{vehicle.get('current_mileage')} км"],
    ]
    table = Table([[_p(a, styles['APBody']), _p(b, styles['APBody'])] for a,b in summary_rows], colWidths=[42*mm, 126*mm])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor('#D0D5DD')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F2F4F7')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(table)

    visits = payload.get('visits', [])
    story.append(_p('Ремонтные визиты и обслуживание', styles['APH2']))
    if not visits:
        story.append(_p('Записей нет.', styles['APBody']))
    for visit in visits:
        cost = rub(visit.get('total_cost_rubles')) if 'total_cost_rubles' in visit else 'скрыто владельцем'
        head = f"{visit.get('visit_date')} · {visit.get('title')} · {visit.get('trust_level')} · {cost}"
        story.append(_p(head, styles['APBody']))
        meta = f"Пробег: {visit.get('mileage') or '—'} км. Место: {visit.get('location') or '—'}. {visit.get('description') or ''}"
        story.append(_p(meta, styles['APSmall']))
        rows = [['Тип', 'Позиция', 'Бренд / №', 'Кол-во', 'Стоимость']]
        for item in visit.get('items', []):
            if item.get('cost_rubles') is not None:
                item_cost = rub(item.get('cost_rubles'))
            else:
                item_cost = item.get('cost_status') or '—'
            brand = ' / '.join(x for x in [item.get('brand'), item.get('part_number')] if x)
            qty = ' '.join(x for x in [str(item.get('quantity') or ''), item.get('unit') or ''] if x).strip()
            rows.append([item.get('item_type'), item.get('title'), brand or '—', qty or '—', item_cost])
        if len(rows) > 1:
            t = Table([[_p(cell, styles['APSmall']) for cell in row] for row in rows], colWidths=[22*mm, 62*mm, 33*mm, 18*mm, 33*mm])
            t.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor('#D0D5DD')),
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EAECF0')),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 3),
                ('RIGHTPADDING', (0,0), (-1,-1), 3),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            story.append(t)
        story.append(Spacer(1, 4*mm))

    story.append(_p('Примечание о доверии', styles['APH2']))
    story.append(_p('verified — подтверждено заказ-нарядом, актом или чеком. confirmed — подтверждено диагностикой, фото результата или подтверждением мастера. declared — заявлено владельцем без достаточного документа.', styles['APSmall']))
    doc.build(story)
    return buffer.getvalue()
