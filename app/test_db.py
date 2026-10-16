
from app.database import engine, Base
from app.models import User, Product, Cart, Order, OrderItem

Base.metadata.create_all(bind=engine)

print("All tables are ready!")