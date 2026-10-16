
import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order
from app.auth import require_roles
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)
from reportlab.lib.styles import getSampleStyleSheet

router = APIRouter(
    prefix="/api/reports",
    tags=["Reports"],
)


@router.get("/orders/csv")
def export_orders_csv(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin"))
):
    orders = db.query(Order).order_by(
        Order.created_at.desc()
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Order ID",
        "User ID",
        "Total Amount",
        "Order Status",
        "Payment Status",
        "Created At",
    ])

    for order in orders:
        writer.writerow([
            order.id,
            order.user_id,
            order.total_amount,
            order.status,
            order.payment_status,
            order.created_at,
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=orders_report.csv"
        },
    )

@router.get("/orders/pdf")
def export_orders_pdf(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin"))
):
    orders = db.query(Order).order_by(
        Order.created_at.desc()
    ).all()

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
    )

    styles = getSampleStyleSheet()
    elements = []

    elements.append(
        Paragraph("StyleHub - Order Report", styles["Title"])
    )
    elements.append(Spacer(1, 16))

    data = [[
        "Order ID",
        "User ID",
        "Total Amount",
        "Order Status",
        "Payment Status",
        "Created At",
    ]]

    for order in orders:
        data.append([
            str(order.id),
            str(order.user_id),
            str(order.total_amount),
            str(order.status),
            str(order.payment_status),
            str(order.created_at or ""),
        ])

    table = Table(
        data,
        repeatRows=1,
        colWidths=[55, 55, 90, 95, 100, 150],
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))

    elements.append(table)
    document.build(elements)

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                "attachment; filename=orders_report.pdf"
        },
    )
