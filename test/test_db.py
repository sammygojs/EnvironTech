import datetime
import pytest
import sys
sys.path.append("C:\TSP\project")
from main import db, app, Cart, Order, OrderDetails, Metrics, Product, User, Admin, Staff

@pytest.fixture(scope='module')
def test_client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

@pytest.fixture(scope='module')
def new_user():
    with app.app_context():
        user = User(fname="Test", lname="User", email="test@example.com", password="test123", country="Test Country")
        return user

def test_add_to_cart(test_client, new_user):
    with app.app_context():
        # Add a new user to the database
        db.session.add(new_user)
        db.session.commit()

        # Create a new product
        product = Product(name="Test Product", price=10.0, country="Test Country", population=10000, impact="low")
        db.session.add(product)
        db.session.commit()

        # Add the product to the user's cart
        cart_item = Cart(user_id=new_user.id, product_id=product.id, quantity=1)
        db.session.add(cart_item)
        db.session.commit()

        # Retrieve the user's cart and check if the product is added
        user_cart = Cart.query.filter_by(user_id=new_user.id).all()
        assert len(user_cart) == 1
        assert user_cart[0].product_id == product.id

def test_place_order(test_client, new_user):
    with app.app_context():
        # Add a new user to the database
        db.session.add(new_user)
        db.session.commit()

        # Create a new product
        product = Product(name="Test Product", price=10.0, country="Test Country", population=10000, impact="low")
        db.session.add(product)
        db.session.commit()

        # Add the product to the user's cart
        cart_item = Cart(user_id=new_user.id, product_id=product.id, quantity=1)
        db.session.add(cart_item)
        db.session.commit()

        # Place an order
        order = Order(user_id=new_user.id, order_date=datetime.datetime.now(), total_amount=10.0, is_Paid=1)
        db.session.add(order)
        db.session.commit()

        # Retrieve the user's orders and check if the order is placed
        user_orders = Order.query.filter_by(user_id=new_user.id).all()
        assert len(user_orders) == 1
        assert user_orders[0].total_amount == 10.0

def test_order_details(test_client, new_user):
    with app.app_context():
        # Add a new order to the database
        order = Order(user_id=new_user.id, order_date=datetime.datetime.now(), total_amount=10.0, is_Paid=1)
        db.session.add(order)
        db.session.commit()

        # Create multiple products and add them to the order details
        product1 = Product(name="Product 1", price=20.0, country="Test Country", population=10000, impact="low")
        db.session.add(product1)
        db.session.commit()

        product2 = Product(name="Product 2", price=30.0, country="Test Country", population=10000, impact="high")
        db.session.add(product2)
        db.session.commit()

        # Add products to the order details
        order_detail1 = OrderDetails(order_id=order.id, product_id=product1.id, quantity=1)
        db.session.add(order_detail1)

        order_detail2 = OrderDetails(order_id=order.id, product_id=product2.id, quantity=2)
        db.session.add(order_detail2)

        db.session.commit()

        # Retrieve order details and check if the products are correctly added
        order_details = OrderDetails.query.filter_by(order_id=order.id).all()
        assert len(order_details) == 2
        assert order_details[0].product_id == product1.id
        assert order_details[1].product_id == product2.id

def test_metrics(test_client, new_user):
    with app.app_context():
        # Add a new user and order to the database
        order = Order(user_id=new_user.id, order_date=datetime.datetime.now(), total_amount=10.0, is_Paid=1)
        db.session.add(order)
        db.session.commit()

        # Create a new metrics entry for the user and order
        metrics = Metrics(user_id=new_user.id, order_id=order.id, contribution_done=5.0, total_carbon_offset=2.5)
        db.session.add(metrics)
        db.session.commit()

        # Retrieve the metrics entry and check if it is correctly added
        user_metrics = Metrics.query.filter_by(user_id=new_user.id).first()
        assert user_metrics is not None
        assert user_metrics.order_id == order.id

def test_admin(test_client):
    with app.app_context():
        # Add a new admin to the database
        admin = Admin(fname="Admin", lname="User", email="admin@example.com", password="admin123", is_Staff=1)
        db.session.add(admin)
        db.session.commit()

        # Retrieve the admin and check if it is correctly added
        admin_from_db = Admin.query.filter_by(email="admin@example.com").first()
        assert admin_from_db is not None

def test_staff(test_client):
    with app.app_context():
        # Check if there is any staff member with the same email
        existing_staff = Staff.query.filter_by(email="teststaff@example.com").first()

        # If there is an existing staff member with the same email, delete it
        if existing_staff:
            db.session.delete(existing_staff)
            db.session.commit()

        # Add a new staff member to the database
        staff = Staff(fname="Staff", lname="User", email="teststaff@example.com", password="staff123", is_verified=1)
        db.session.add(staff)
        db.session.commit()

        # Retrieve the staff member and check if it is correctly added
        staff_from_db = Staff.query.filter_by(email="teststaff@example.com").first()
        assert staff_from_db is not None


def test_product():
    with app.app_context():
        # Add multiple products with different attributes
        product1 = Product(name="Product 1", price=20.0, country="Test Country", population=10000, impact="low")
        db.session.add(product1)

        product2 = Product(name="Product 2", price=30.0, country="Test Country", population=20000, impact="high")
        db.session.add(product2)

        db.session.commit()

        # Retrieve products and check if they are correctly added with the specified attributes
        products = Product.query.all()
        # print(products)
        assert len(products) >= 2




