
import os

import stripe
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi import Request

from app.database import get_db
from app.models import Order
from app.auth import get_current_user


load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

router = APIRouter(
    prefix="/api/payments",
    tags=["Payments"]
)


class PaymentRequest(BaseModel):
    order_id: int = Field(gt=0)


@router.post("/create-checkout-session")
def create_checkout_session(
    payment_data: PaymentRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not stripe.api_key:
        raise HTTPException(
            status_code=500,
            detail="Stripe secret key is not configured"
        )

    order = db.query(Order).filter(
        Order.id == payment_data.order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    if order.payment_status == "SUCCESS":
        raise HTTPException(
            status_code=400,
            detail="Order is already paid"
        )

    if order.total_amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid order amount"
        )

    try:
        session = stripe.checkout.Session.create(
    mode="payment",
    line_items=[
        {
            "price_data": {
                "currency": "inr",
                "product_data": {
                    "name": f"StyleHub Order #{order.id}"
                },
                "unit_amount": int(round(order.total_amount * 100)),
            },
            "quantity": 1,
        }
    ],
    success_url=(
        "http://127.0.0.1:8000/payment-success"
        "?session_id={CHECKOUT_SESSION_ID}"
    ),
    cancel_url="http://127.0.0.1:8000/payment-cancelled",
    metadata={
        "order_id": str(order.id),
        "user_id": str(current_user.id)
    }
)
        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "order_id": order.id,
            "payment_status": order.payment_status
        }

    
    except stripe.StripeError as e:
        print("Stripe error:", str(e))
        raise HTTPException(
            status_code=502,
            detail="Stripe checkout failed. Check the terminal output."
    )

        @router.post("/webhook")
        async def stripe_webhook(
            request: Request,
            db: Session = Depends(get_db)
    ):
            if not STRIPE_WEBHOOK_SECRET:
                raise HTTPException(
                    status_code=500 ,
                    detail="Stripe webhook secret is not configured"
                )

            payload = await request.body()
            signature = request.headers.get("stripe-signature")

    if not signature:
        raise HTTPException(
            status_code=400,
            detail="Missing Stripe signature"
        )

    try:
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook payload or signature"
        )

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        if session.get("payment_status") == "paid":
            order_id = session.get("metadata", {}).get("order_id")

            if order_id:
                order = db.query(Order).filter(
                    Order.id == int(order_id)
                ).first()

                if order:
                    order.payment_status = "SUCCESS"
                    order.status = "PROCESSING"
                    db.commit()

    elif event["type"] == "checkout.session.async_payment_failed":
        session = event["data"]["object"]
        order_id = session.get("metadata", {}).get("order_id")

        if order_id:
            order = db.query(Order).filter(
                Order.id == int(order_id)
            ).first()

            if order and order.payment_status != "SUCCESS":
                order.payment_status = "FAILED"
                db.commit()

    return {"received": True}