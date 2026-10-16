
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Cart, Product, Order, OrderItem, Notification
from app.schemas import OrderResponse
from pydantic import BaseModel
from app.auth import get_current_user



router = APIRouter(prefix="/api/orders", tags=["Orders"])
class OrderStatusUpdate(BaseModel):
    status: str


# 1. PLACE ORDER
@router.post("/", response_model=OrderResponse, status_code=201)
def place_order(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cart_items = db.query(Cart).filter(
        Cart.user_id == current_user.id
    ).all()

    if not cart_items:
        raise HTTPException(
            status_code=400,
            detail="Your cart is empty"
        )

    total_amount = 0
    order_items_data = []

    # Check products and stock
    for cart_item in cart_items:
        product = db.query(Product).filter(
            Product.id == cart_item.product_id
        ).first()

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {cart_item.product_id} not found"
            )

        if product.stock < cart_item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.name}"
            )

        item_total = product.price * cart_item.quantity
        total_amount += item_total

        order_items_data.append({
            "product": product,
            "quantity": cart_item.quantity,
            "price": product.price
        })

    try:
        # Create order
        new_order = Order(
            user_id=current_user.id,
            total_amount=total_amount,
            status="PENDING",
            payment_status="PENDING"
        )

        db.add(new_order)
        db.flush()

       
        # Save order items and reduce stock
        for item in order_items_data:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item["product"].id,
                quantity=item["quantity"],
                price=item["price"]
            )
            db.add(order_item)

            # Reduce product stock
            item["product"].stock -= item["quantity"]
            
        # Clear the user's cart after creating the order
        for cart_item in cart_items:
            db.delete(cart_item)

                    # Create order notification
        notification = Notification(
            user_id=current_user.id,
            message=f"Your order #{new_order.id} has been placed successfully!",
            notification_type="ORDER_UPDATE"
        )
        db.add(notification)

        db.commit()
        db.refresh(new_order)

        return {
            "id": new_order.id,
            "user_id": new_order.user_id,
            "total_amount": new_order.total_amount,
            "status": new_order.status,
            "payment_status": new_order.payment_status,
            "created_at": new_order.created_at,
            "items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "price": item.price
                }
                for item in db.query(OrderItem).filter(
                    OrderItem.order_id == new_order.id
                ).all()
            ]
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not create order"
        )


# 2. VIEW ORDER HISTORY
@router.get("/", response_model=list[OrderResponse])
def get_order_history(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    orders = db.query(Order).filter(
        Order.user_id == current_user.id
    ).order_by(Order.id.desc()).all()

    result = []

    for order in orders:
        items = db.query(OrderItem).filter(
            OrderItem.order_id == order.id
        ).all()

        result.append({
            "id": order.id,
            "user_id": order.user_id,
            "total_amount": order.total_amount,
            "status": order.status,
            "payment_status": order.payment_status,
            "created_at": order.created_at,
            "items": items
        })

    return result


# 3. VIEW SINGLE ORDER
@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    items = db.query(OrderItem).filter(
        OrderItem.order_id == order.id
    ).all()

    return {
        "id": order.id,
        "user_id": order.user_id,
        "total_amount": order.total_amount,
        "status": order.status,
        "payment_status": order.payment_status,
        "created_at": order.created_at,
        "items": items
    }
# 4. UPDATE ORDER STATUS
@router.patch("/{order_id}/status")
def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    allowed_statuses = [
        "PENDING",
        "PROCESSING",
        "SHIPPED",
        "DELIVERED",
        "CANCELLED"
    ]

    if data.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid order status"
        )

    order = db.query(Order).filter(
        Order.id == order_id
    ).first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    order.status = data.status

    notification = Notification(
        user_id=order.user_id,
        message=f"Your order #{order.id} status is now {data.status}.",
        notification_type="ORDER_UPDATE"
    )

    db.add(notification)
    db.commit()
    db.refresh(order)

    return {
        "message": "Order status updated successfully",
        "order_id": order.id,
        "status": order.status
    }