from fastapi import FastAPI

from dotenv import load_dotenv

load_dotenv()

from app.database import Base, engine
from app import models

from app.auth import router as auth_router
from app.products import router as products_router
from app.cart import router as cart_router
from app.orders import router as orders_router
from app.payments import router as payments_router
from app.notifications import router as notifications_router
from app.analytics import router as analytics_router
from app.reports import router as reports_router


app = FastAPI(title="StyleHub - Fashion Mini Store API")

Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(products_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(notifications_router)
app.include_router(analytics_router)
app.include_router(reports_router)



@app.get("/")
def home():
    return {"message": "StyleHub Fashion Mini Store API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
