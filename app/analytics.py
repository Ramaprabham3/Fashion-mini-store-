
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Order
from app.auth import require_roles
from app.models import OrderItem, Product


router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"],
)


@router.get("/summary")
def get_sales_summary(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin"))
):
    total_orders = db.query(func.count(Order.id)).scalar() or 0

    pending_orders = db.query(func.count(Order.id)).filter(
        Order.status == "PENDING"
    ).scalar() or 0

    completed_orders = db.query(func.count(Order.id)).filter(
        Order.status == "DELIVERED"
    ).scalar() or 0

    total_revenue = db.query(
        func.coalesce(func.sum(Order.total_amount), 0)
    ).filter(
        Order.payment_status == "SUCCESS"
    ).scalar()

    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "total_revenue": round(float(total_revenue), 2),
    }
