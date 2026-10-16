
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Cart, Product
from app.schemas import CartAdd, CartUpdate, CartItemResponse
from app.auth import get_current_user


router = APIRouter(prefix="/api/cart", tags=["Cart"])


# 1. VIEW CART
@router.get("/", response_model=list[CartItemResponse])
def view_cart(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return db.query(Cart).filter(
        Cart.user_id == current_user.id
    ).all()


# 2. ADD PRODUCT TO CART
@router.post("/", response_model=CartItemResponse, status_code=201)
def add_to_cart(
    item_data: CartAdd,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    product = db.query(Product).filter(
        Product.id == item_data.product_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.stock < item_data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    cart_item = db.query(Cart).filter(
        Cart.user_id == current_user.id,
        Cart.product_id == item_data.product_id
    ).first()

    if cart_item:
        new_quantity = cart_item.quantity + item_data.quantity

        if new_quantity > product.stock:
            raise HTTPException(status_code=400, detail="Insufficient stock")

        cart_item.quantity = new_quantity
    else:
        cart_item = Cart(
            user_id=current_user.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity
        )
        db.add(cart_item)

    db.commit()
    db.refresh(cart_item)

    return cart_item


# 3. UPDATE CART QUANTITY
@router.put("/{cart_item_id}", response_model=CartItemResponse)
def update_cart(
    cart_item_id: int,
    item_data: CartUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cart_item = db.query(Cart).filter(
        Cart.id == cart_item_id,
        Cart.user_id == current_user.id
    ).first()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    product = db.query(Product).filter(
        Product.id == cart_item.product_id
    ).first()

    if not product or item_data.quantity > product.stock:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    cart_item.quantity = item_data.quantity
    db.commit()
    db.refresh(cart_item)

    return cart_item


# 4. REMOVE ITEM FROM CART
@router.delete("/{cart_item_id}")
def remove_from_cart(
    cart_item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cart_item = db.query(Cart).filter(
        Cart.id == cart_item_id,
        Cart.user_id == current_user.id
    ).first()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    db.delete(cart_item)
    db.commit()

    return {"message": "Product removed from cart"}


# 5. CART TOTAL PRICE
@router.get("/total")
def get_cart_total(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    cart_items = db.query(Cart).filter(
        Cart.user_id == current_user.id
    ).all()

    total_amount = 0
    items = []

    for item in cart_items:
        product = db.query(Product).filter(
            Product.id == item.product_id
        ).first()

        if product:
            item_total = product.price * item.quantity
            total_amount += item_total

            items.append({
                "product_id": product.id,
                "product_name": product.name,
                "price": product.price,
                "quantity": item.quantity,
                "item_total": round(item_total, 2)
            })

    return {
        "items": items,
        "total_amount": round(total_amount, 2)
    }
