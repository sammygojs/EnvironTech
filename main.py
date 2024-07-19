from flask import Flask, render_template, request, redirect, session, url_for, jsonify, make_response, send_file
from flask_sqlalchemy import SQLAlchemy
from io import BytesIO
from reportlab.pdfgen import canvas
import random
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from flask_bcrypt import Bcrypt
import paypalrestsdk
import stripe
import regex
import datetime
from math import ceil

app = Flask(__name__)
app.config["SECRET_KEY"]='65b0b774279de460f1cc5c92'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///EnvironOffset.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SESSION_PERMANENT"]=False
app.config["SESSION_TYPE"]='filesystem'

db=SQLAlchemy(app)
bcrypt=Bcrypt(app)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'Cart( "{self.user_id}", "{self.product_id}", "{self.quantity}")'


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_date = db.Column(db.DateTime, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    is_Paid = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return f'Order("{self.user_id}", "{self.order_date}", "{self.total_amount}", "{self.is_Paid}")'


class OrderDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    # price_per_unit = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'OrderDetails("{self.order_id}", "{self.product_id}", "{self.quantity}")'
    
class Metrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    contribution_done = db.Column(db.Float, nullable=False)
    total_carbon_offset = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'Metrics("{self.user_id}", "{self.order_id}", "{self.contribution_done}", "{self.total_carbon_offset}")'

# Product class
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    country = db.Column(db.String(255), nullable=False)
    population = db.Column(db.Integer, nullable=False)
    impact = db.Column(db.String(20), nullable=False)  # 'high', 'neutral', 'low'
    energy_production = db.Column(db.Float, default=None)  # in kWh/day
    time_to_recover_expense = db.Column(db.Integer, default=None)  # in days
    carbon_offset_per_year = db.Column(db.Float, default=None)  # in tons
    electricity_grid_network_km = db.Column(db.Float, default=None)  # in km

    def __repr__(self):
        return f'Product("{self.name}", "{self.price}", "{self.country}", "{self.impact}", "{self.energy_production}", "{self.time_to_recover_expense}", "{self.carbon_offset_per_year}", "{self.electricity_grid_network_km}")'


class User(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    fname=db.Column(db.String(255), nullable=False)
    lname=db.Column(db.String(255), nullable=False)
    email=db.Column(db.String(255), nullable=False)
    password=db.Column(db.String(255), nullable=False)
    country=db.Column(db.String(255), nullable=False)
    total_contribution = db.Column(db.Float, default=None)
    total_carbon_offset = db.Column(db.Float, default=None)
    carbon_footprint = db.Column(db.Float, default=None)
    offset_under_neutral = db.Column(db.Float, default=None)

    def serialize(self):
        return {
            "id": self.id,
            "password": self.password,  # Note: It's generally not recommended to expose passwords in serialization
            "email": self.email,
            "user_type": self.user_type,
            "total_contribution": self.total_contribution,
            "total_carbon_offset": self.total_carbon_offset,
            "carbon_footprint": self.carbon_footprint,
            "offset_under_neutral": self.offset_under_neutral
        }

    def __repr__(self):
         return f"User(id={self.id}, fname={self.fname}, lname={self.lname}, email={self.email}, " \
               f"country={self.country}, total_contribution={self.total_contribution}, " \
               f"total_carbon_offset={self.total_carbon_offset}, carbon_footprint={self.carbon_footprint}, " \
               f"offset_under_neutral={self.offset_under_neutral})"


# create admin Class
class Admin(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(255), nullable=False)
    lname = db.Column(db.String(255), nullable=False)
    email=db.Column(db.String(255), nullable=False)
    password=db.Column(db.String(255), nullable=False)
    is_Staff = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return f'Admin("{self.fname}","{self.lname}","{self.email}","{self.id}","{self.is_Staff}")'

#create staff class
class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(255), nullable=False)
    lname = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    is_verified = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return f'Staff("{self.fname}","{self.lname}","{self.email}","{self.id}","{self.is_verified}")'

    
# Mock data for Product class
# products = [
#     Product(
#         name=f"Product_{i}",
#         description=f"Description for Product {i}",
#         price=0.01 * i,
#         country="Country_" + str(i),
#         population=1000000 * i,
#         impact='high' if i % 2 == 0 else 'low',
#         energy_production=500.0 * i,
#         time_to_recover_expense=30 * i,
#         carbon_offset_per_year=2.5 * i,
#         electricity_grid_network_km=100.0 * i
#     )
#     for i in range(1, 11)  # Adjust the number of products you want to create
# ]


# Create and add users, admins, and staff members
user1 = User(fname="John", lname="Doe", email="john1.doe@example.com", password=bcrypt.generate_password_hash(f"123", 10).decode('utf-8'), country="USA")
user2 = User(fname="Jane", lname="Smith", email="jane.smith@example.com", password=bcrypt.generate_password_hash(f"123", 10).decode('utf-8'), country="Canada")

admin1 = Admin(fname="Admin", lname="One", email="admin@example.com", password=bcrypt.generate_password_hash(f"admin", 10).decode('utf-8'), is_Staff=True)
admin2 = Admin(fname="Admin", lname="Two", email="admin2@example.com", password=bcrypt.generate_password_hash(f"admin", 10).decode('utf-8'), is_Staff=False)

staff1 = Staff(fname="Staff", lname="One", email="staff@example.com", password=bcrypt.generate_password_hash(f"staff", 10).decode('utf-8'), is_verified=True)
staff2 = Staff(fname="Staff", lname="Two", email="staff2@example.com", password=bcrypt.generate_password_hash(f"admin", 10).decode('utf-8'), is_verified=False)

# Given JSON data
data = [
    {
        "name": "Spain",
        "grid carbon intensity (gCO2eq/kWh)": 131,
        "cost of solar (US$/kWp)": 545,
        "potential solar generation (kWh per kWp per year)": 1655,
        "population (millions)": 47.4,
        "households without access to electricity (%)": 0,
        "flag_url": "",
        "description": "With a moderate grid carbon intensity of 131 gCO2eq/kWh and a moderate cost of solar at $545/kWp, Spain boasts a high potential solar generation of 1655 kWh per kWp per year. Despite its relatively small population of 47.4 million, all households have access to electricity."
    
    },
    {
        "name": "Nigeria",
        "grid carbon intensity (gCO2eq/kWh)": 440,
        "cost of solar (US$/kWp)": 313,
        "potential solar generation (kWh per kWp per year)": 1554,
        "population (millions)": 227.5,
        "households without access to electricity (%)": 37.8,
        "flag_url": "",
        "description": "Nigeria faces challenges with a high grid carbon intensity of 440 gCO2eq/kWh and a relatively low cost of solar at $313/kWp. However, it has a moderate potential solar generation of 1554 kWh per kWp per year. With a large population of 227.5 million, approximately 37.8% of households lack access to electricity."
    },
    {
        "name": "India",
        "grid carbon intensity (gCO2eq/kWh)": 632,
        "cost of solar (US$/kWp)": 845,
        "potential solar generation (kWh per kWp per year)": 1585,
        "population (millions)": 1440,
        "households without access to electricity (%)": 3.3,
        "flag_url": "",
         "description": "India experiences significant environmental pressure with a very high grid carbon intensity of 632 gCO2eq/kWh, but it offers moderate solar installation costs at $845/kWp and moderate potential solar generation of 1585 kWh per kWp per year. With a massive population of 1.44 billion, only 3.3% of households are without access to electricity."
    
    },
    {
        "name": "Egypt",
        "grid carbon intensity (gCO2eq/kWh)": 475,
        "cost of solar (US$/kWp)": 1775,
        "potential solar generation (kWh per kWp per year)": 1986,
        "population (millions)": 114.4,
        "households without access to electricity (%)": 0,
        "extra information": "there are currently frequent blackouts happening in the country",
        "flag_url": "",
        "description": "Egypt grapples with a high grid carbon intensity of 475 gCO2eq/kWh and a substantial cost of solar at $1775/kWp. However, it boasts a high potential solar generation of 1986 kWh per kWp per year. Despite a population of 114.4 million, all households have electricity access, although frequent blackouts occur."
    
    },
    # {
    #     "name": "South Africa",
    #     "grid carbon intensity (gCO2eq/kWh)": 866,
    #     "cost of solar (US$/kWp)": 1132,
    #     "potential solar generation (kWh per kWp per year)": 1869,
    #     "population (millions)": 59.4,
    #     "households without access to electricity (%)": 10.4,
    #     "extra information": "an estimated 43% of South African households are too poor to meet their basic energy needs",
    #     "flag_url": "",
    #     "description": "South Africa faces significant environmental challenges with a very high grid carbon intensity of 866 gCO2eq/kWh. It features moderate solar installation costs at $1132/kWp and high potential solar generation of 1869 kWh per kWp per year. With a population of 59.4 million, approximately 10.4%"
    # }
]

# Convert JSON data to Product instances
products = []
for entry in data:
    name = entry['name']
    description = entry['description']  # You can add descriptions if available
    price = entry['cost of solar (US$/kWp)']  # Assuming cost of solar as price
    country = name
    population = int(entry['population (millions)'])  # Convert to integer (millions to total)
    impact = 'low' if entry['grid carbon intensity (gCO2eq/kWh)'] <= 200 else 'high'  # Example logic for impact
    energy_production = entry['potential solar generation (kWh per kWp per year)']
    time_to_recover_expense = int(price / energy_production * 365)  # Assuming full energy consumption
    carbon_offset_per_year = entry['grid carbon intensity (gCO2eq/kWh)'] * energy_production / 1_000_000
    electricity_grid_network_km = None  # Not provided in JSON data
    product = Product(
        name=name,
        description=description,
        price=price,
        country=country,
        population=population,
        impact=impact,
        energy_production=energy_production,
        time_to_recover_expense=time_to_recover_expense,
        carbon_offset_per_year=carbon_offset_per_year,
        electricity_grid_network_km=electricity_grid_network_km
    )
    products.append(product)



with app.app_context():

    # db.session.add_all(products + users + orders + admins + staff_members)
    # db.drop_all() 
    # db.create_all()
    # db.session.commit()
    # db.session.add_all(products)
    # db.session.add_all([user1, user2, admin1, admin2, staff1, staff2])
    # db.session.commit()
    # write db code here
    users=User().query.all()
    print(users)
    # orders=Order().query.all()
    # print(orders)
    # products=Product().query.all()
    # print(products[1].description)
    # metrics=Metrics().query.all()
    # print(metrics)
    # orderDetails=OrderDetails().query.all()
    # print(orderDetails)
    # print("DB IS CONNECTED AND WORKING")
    # db.create_all()
    # admins=Admin().query.all()
    # print(admins)
    # staffs = Staff().query.all()
    # print(staffs)
    # create_product()
    print("DB IS CONNECTED AND WORKING")

@app.route("/")
def homepage():
    return render_template('Homepage.html')

@app.route("/user/calculate")
def calculate_footprint():
    return render_template('user/Footprint_cal.html')

@app.route("/products")
def products_homepage():
    sort_by = request.args.get('sort_by', 'asc')  # Default sorting: ascending
    if sort_by == 'asc':
        products = Product.query.order_by(Product.price).all()
    elif sort_by == 'desc':
        products = Product.query.order_by(Product.price.desc()).all()
    else:
        products = Product.query.all()
    return render_template('products.html',products=products,sort_by=sort_by)

@app.route("/faq")
def faq():
    return render_template('faq.html')

@app.route("/problems-solutions")
def problems_solutions():
    return render_template('problems-solutions.html')

@app.route("/how-it-works")
def how_it_works():
    return render_template('how-it-works.html')

@app.route("/user/stats")
def user_stats1():
    return render_template('user/statistics1.html')

@app.route('/staff/userDetails/<int:user_id>')
def user_details(user_id):
    # Fetch user data from the database (replace this with your data retrieval logic)
    # user = {
    #     'id': 1,
    #     'firstName': 'John',
    #     'lastName': 'Doe',
    #     'email': 'john@example.com',
    #     'country': 'USA',
    #     'total_contribution': 1000,
    #     'total_carbon_offset': 50,
    #     'carbon_footprint': 20,
    #     'offset_under_neutral': None  # Add actual value if available
    # }
    user = User().query.filter_by(id=user_id).first()
    
    return render_template('staff/userDetails.html', user=user)

# -------------printing methods------------
from reportlab.lib.pagesizes import letter

user_data = []
@app.route('/staff/generate-pdf/<int:user_id>', methods=['GET'])
def generate_pdf(user_id):
    # userId = session['user_id']
    users = User().query.filter_by(id=user_id).first()
    user_data.clear()
    
    user_data.append({
        'id': users.id,
        'firstName': users.fname,
        'lastName': users.lname,
        'email': users.email,
        'country': users.country,
        'total_contribution': users.total_contribution,
        'total_carbon_offset': users.total_carbon_offset,
        'carbon_footprint': users.carbon_footprint,
        'offset_under_neutral': users.offset_under_neutral
    })
 
    pdf_file = generate_pdf_file()
    return send_file(pdf_file, as_attachment=True, download_name='user_details.pdf')
 
def generate_pdf_file():
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.setFont("Helvetica", 12)
    p.setTitle("User Detailed Report")

    # Initialize y position near the top of the page
    y = 750
    
    # Draw Title and Line once
    p.drawString(50, y, "User Detailed Report")
    p.line(50, y-5, 550, y-5)
    y -= 50  # Adjust y position after title
    
    # Iterate through user data to display user details and order history on the first page
    for user in user_data:
        draw_user_data(p, user, y)
        y -= 250  # Adjust y position for next section

        # Break out of the loop if you only need the first user's data on the first page
        break

    # Draw user order history
    draw_user_order_history(p, user_data[0]['id'], y)

    # Create a new page for charts
    p.showPage()

    # Reset y position for the new page
    y = 730
    
    # Generate and draw charts on the second page
    generate_carbon_footprint_comparison_graph(user['carbon_footprint'], user['country'])
    p.drawImage("carbon_footprint_comparison1.png", 50, y - 260, width=500, height=350)
    os.remove("carbon_footprint_comparison1.png")
    y -= 350  # Adjust y position after drawing the first chart

    generate_system_comparison_bar_chart(user)
    p.drawImage("system_comparison_chart.png", 50, y - 350, width=500, height=350)
    os.remove("system_comparison_chart.png")
    
    # Finalize the PDF
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

def draw_user_order_history(p, user_id, start_y):
    # Fetch orders
    orders = Order.query.filter_by(user_id=user_id).all()
    
    # Table data setup
    data = [['Order ID', 'Date', 'Total Amount']]
    for order in orders:
        # Each order is a row in the table
        data.append([order.id, order.order_date.strftime('%Y-%m-%d'), f"${order.total_amount:.2f}"])
    
    # Create the table
    table = Table(data, colWidths=[100, 150, 100], rowHeights=20)
    
    # Add style to the table
    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.gray),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ])
    
    table.setStyle(style)
    
    # Draw the table at the specified y-coordinate
    table.wrapOn(p, 50, start_y)
    table.drawOn(p, 50, start_y - 20)



def draw_user_data(p, user, y):
    """
    Draws the user data onto the PDF canvas.
    :param p: The PDF canvas instance from reportlab.
    :param user: Dictionary containing user data.
    :param y: Vertical position on the PDF.
    """
    # Draw user details
    # p.drawString(50, y, f"User ID: {user['id']}")
    p.drawString(50, y - 20, f"First Name: {user['firstName']}")
    p.drawString(50, y - 40, f"Last Name: {user['lastName']}")
    p.drawString(50, y - 60, f"Email: {user['email']}")
    p.drawString(50, y - 80, f"Country: {user['country']}")
    p.drawString(50, y - 100, f"Total Contribution: ${user['total_contribution']}")
    p.drawString(50, y - 120, f"Total Carbon Offset: {user['total_carbon_offset']} tons")
    p.drawString(50, y - 140, f"Carbon Footprint: {user['carbon_footprint']} tons")

    # Conditionally render the offset under neutral
    offset_text = f"Offset Under Neutral: {user['offset_under_neutral']} tons" if user['offset_under_neutral'] is not None else "Offset Under Neutral: N/A"
    p.drawString(50, y - 160, offset_text)

import matplotlib.pyplot as plt
import numpy as np

def generate_system_comparison_bar_chart(user):
    # Fetch user-specific metrics
    user_metrics = Metrics.query.filter_by(user_id=user['id']).first()
    
    # Calculate average metrics for all users
    all_metrics = Metrics.query.all()
    total_contribution_all = sum([m.contribution_done for m in all_metrics]) / len(all_metrics)
    total_carbon_offset_all = sum([m.total_carbon_offset for m in all_metrics]) / len(all_metrics)

    # User-specific metrics for comparison
    user_contribution = user_metrics.contribution_done if user_metrics else 0
    user_carbon_offset = user_metrics.total_carbon_offset if user_metrics else 0

    # Bar chart data
    categories = ['Total Contribution', 'Total Carbon Offset']
    user_values = [user_contribution, user_carbon_offset]
    all_values = [total_contribution_all, total_carbon_offset_all]

    # Number of categories
    n = len(categories)
    index = np.arange(n)
    bar_width = 0.35

    # Plotting
    fig, ax = plt.subplots()
    bar1 = ax.bar(index, user_values, bar_width, label='User')
    bar2 = ax.bar(index + bar_width, all_values, bar_width, label='Average All Users')

    # Labeling and aesthetics
    ax.set_xlabel('Metrics')
    ax.set_ylabel('Values')
    ax.set_title('Comparison of User Metrics vs. Average')
    ax.set_xticks(index + bar_width / 2)
    ax.set_xticklabels(categories)
    ax.legend()

    # Save the generated bar chart
    plt.savefig('system_comparison_chart.png')
    plt.close()

import matplotlib
matplotlib.use('Agg')  # Set the backend before importing pyplot
import matplotlib.pyplot as plt

def generate_carbon_footprint_comparison_graph(user_footprint, user_country):
    # Example data: Average footprints for different countries
    average_footprints = {
        'USA': 16.07,
        'China': 7.42,
        'India': 1.9,
        'World Average': 4.8
    }

    # Plotting the graph
    plt.figure(figsize=(8, 8))
    plt.bar(average_footprints.keys(), average_footprints.values(), color='skyblue')
    plt.bar(user_country, user_footprint, color='orange')

    # Adding labels and title
    plt.xlabel('Country')
    plt.ylabel('Carbon Footprint (tons)')
    plt.title('User Carbon Footprint Comparison')

    # Adding user's footprint as a line on top
    plt.axhline(y=user_footprint, color='red', linestyle='--')
    plt.text(len(average_footprints) - 0.7, user_footprint + 0.1, f'User ({user_country}): {user_footprint}', ha='center')

    # Adding legend
    plt.legend(['User', 'Average Footprint'])

    # Save the graph
    plt.savefig('carbon_footprint_comparison1.png')

# paypal
client_id = "ATr-vuT8BrvJBLV1Yt4hpyzqnt2cmZ9PPqwtp7cc_WwWgmxohaWN2d8jhKF2tLHuFti3x0TVqGB08nh6"
client_secret = "EBF-bgTQyoa1hWEiB3dO5J4uSE6QOvb41DRi5pR42pIrp68olpvc_QNk94AiiAEl7hBKjHIEDY4QO2t0"
# stripe
stripe.api_key = "sk_test_51OsBhYDlNYWKCKsQrDMhg7FexYzUYmnF1Eh2VoPpxd6PIpAQtQHZ9loWh6b2kg7ybl6n1rnVnov7cYN5Z2BwNrq000BiF9YeJu"
stripe_publishable_key = "pk_test_51OsBhYDlNYWKCKsQWCJHfumzg3haURPDmcB5bilOc8R4Pl0pCMusNIE0wreIFYDZh27wI9YKDgVRf0pDfJYUk0Vf00lrunT65X"

paypalrestsdk.configure({
    "mode": "sandbox",
    "client_id": client_id,
    "client_secret": client_secret
})

@app.route("/order/payment_return")
def user_paymentReturn():
    if not session.get("user_id"):
        return redirect("/")
    return redirect("/")

@app.route("/order/payment_cancel")
def user_paymentCancel():
    if not session.get("user_id"):
        return redirect("/")
    return redirect("/")

# Stripe
@app.route("/stripe/payment", methods=['POST'])
def stripe_payment():
    if not session.get("user_id"):
        return redirect("/")
    
    order_id = request.json['orderID']
    order = Order().query.filter_by(id=order_id, user_id=session['user_id']).first_or_404()
    if order.is_Paid:
        return redirect("/")

    order_details = OrderDetails().query.filter_by(order_id=order_id).all()
    #product = Product().query.filter_by(id=order_details.product_id).first()
    products = Product().query.filter(Product.id.in_([od.product_id for od in order_details])).all()

    #if order_details is None or product is None:
    #    raise Exception("Order details or product does not exist")

    #intend = stripe.PaymentIntent.create(amount=order.total_amount, currency='gbp')
    #return jsonify({ "client_secret": intend.client_secret })
    total_cents = 0
    for order_detail, product in zip(order_details, products):
        total_cents += int(product.price * 100) * order_detail.quantity

    # According to Stripe's API documentation, total price must be >= 0.3 GBP.
    # See https://docs.stripe.com/currencies#minimum-and-maximum-charge-amounts for more details
    if total_cents < 30:
        return jsonify({ "status": "error", "description": "Total price must be >= 0.3 pound."})

    items = [{
            'price_data': {
                'currency': 'gbp',
                'product_data': { 'name': product.name },
                'unit_amount': int(100 * product.price)
            },
            'quantity': order_detail.quantity,
        }
        for order_detail, product in zip(order_details, products)
    ]
    #print(items)

    ss = stripe.checkout.Session.create(
    #  line_items = [{
    #    'price_data': {
    #      'currency': 'gbp',
    #      'product_data': { 'name': product.name },
    #      'unit_amount': cents
    #      #'unit_amount': 30
    #    },
    #    'quantity': order_details.quantity,
    #  }],
        line_items=items,
        mode = 'payment',
        success_url = url_for("order_Success", _external=True),
        cancel_url = url_for("user_paymentCancel", _external=True)
    )

    return jsonify({ "status": "ok", "url": ss.url })

@app.route('/user/compare', methods=['POST'])
def print_selected_products():
    userId = session.get('user_id')
    user = User.query.get(userId)
    selected_products = request.form.getlist('productCheckbox')
    products = [Product.query.get(product_id) for product_id in selected_products]
    # Process the selected products here (e.g., save to a database, perform further operations)
    return render_template('/user/compareProducts.html', selected_products=products, user=user)

@app.route('/compare', methods=['POST'])
def print_selected_products_logged_out():
    selected_products = request.form.getlist('productCheckbox')
    products = [Product.query.get(product_id) for product_id in selected_products]
    # Process the selected products here (e.g., save to a database, perform further operations)
    return render_template('/compareProducts.html', selected_products=products)

@app.route('/user/orders')
def user_orders():
    userId = session.get('user_id')
    user = User.query.get(userId)
    orders=Order().query.filter_by(user_id=userId)
    return render_template('user/orders.html', user_orders=orders, user=user)

# Paypal
# create payment
@app.route("/user/payment/<int:order_id>")
def user_payment(order_id):
    if not session.get("user_id"):
        return redirect("/")
    order = Order().query.filter_by(id=order_id).first()
    user = User().query.filter_by(id=session.get("user_id")).first()
    if order is None:
        return redirect("/")
    return render_template("user/payment.html", client_id=client_id, order_id=order_id, user=user)

@app.route('/order/payment', methods=["POST"])
def payment_create():
    if not session.get('user_id'):
        return redirect('/')
    
    order_id = request.json['orderID']
    order = Order().query.filter_by(id=order_id, user_id=session['user_id']).first_or_404()

    # Use the total amount directly regardless of different goods
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": { "payment_method": "paypal" },
        "redirect_urls": {
            # Not sure how it works
            "return_url": url_for("user_paymentReturn", _external=True),
            "cancel_url": url_for("user_paymentCancel", _external=True)
        },
        "transactions": [{
            "amount": {
                "total": f"{order.total_amount}",
                "currency": "GBP"
            }
        }]
    })
    if not payment.create():
        print(payment.error)
        return redirect('/')
    
    ec = regex.search(r"(?<=token=).*", payment.links[1].href).group(0)

    return jsonify({"paymentID": payment.id, "EC": ec})

# Execute payment
@app.route("/order/execute", methods=["POST"])
def order_execute():
    status = "ERROR"
    payment = paypalrestsdk.Payment.find(request.json["paymentID"])
    if payment.execute({"payer_id": request.json["payerID"]}):
        status = "OK"
    else:
        print(payment.error)
    return jsonify({"status" : status, "description": payment.error})

@app.route('/api/data')
def get_api_data():
    # 与/user/statistics端点中相同的逻辑
    users = User.query.all()
    
    # 将查询结果转换为JSON格式响应
    return jsonify({
        'contributions': [user.total_contribution for user in users],
        'carbon_offsets': [user.total_carbon_offset for user in users],
        'carbon_footprints': [user.carbon_footprint for user in users]
    })


@app.route('/user/statsticofcountry', methods=['GET'])
def get_user_country():
    userId = session.get('user_id')  # 获取当前登录的用户ID
    if not userId:
        return jsonify({'error': 'User not logged in'}), 401  # 如果用户未登录，返回错误信息

    user = User.query.filter_by(id=userId).first()  # 查询当前用户
    if user:
        return jsonify({'country': user.country})  # 返回用户的国家信息
    else:
        return jsonify({'error': 'User not found'}), 404  # 如果用户不存在，返回错误信息


def datetimeformat(value, format='%d %B %Y'):
    ordinal_day = value.strftime('%d') + get_ordinal(int(value.strftime('%d')))
    return value.strftime(f'{ordinal_day} %B %Y')

def get_ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return suffix

app.jinja_env.filters['datetimeformat'] = datetimeformat
#User Statistics
@app.route('/user/statistics', methods=['GET'])
def user_status():
    userId = session.get('user_id')
    user = User().query.filter_by(id=userId).first()
    users = User.query.all()
    user_data = {
        'contributions': [user.total_contribution for user in users],
        'carbon_offsets': [user.total_carbon_offset for user in users],
        'carbon_footprints': [user.carbon_footprint for user in users]
    }
    orders = db.session.query(Order, OrderDetails, Product)\
        .select_from(Order)\
        .join(OrderDetails)\
        .join(Product)\
        .filter(Order.user_id == userId)\
        .all()
    
    orders2 = db.session.query(Order, Metrics).\
        select_from(Order).\
        join(Metrics).all()

    total_cost = sum(order.total_amount for order, _, _ in orders if order.is_Paid == 1)
    total_offset = sum(metric.total_carbon_offset for _, metric in orders2 if _.is_Paid == 1)

      # Fetch all paid orders to calculate average system spending
    paid_orders = Order.query.filter_by(is_Paid=1).all()
    total_system_spending = sum(order.total_amount for order in paid_orders)
    print("total_system_spending: ", total_system_spending)

    num_users = User.query.count()  # Total number of users for average calculation
    average_system_spending = total_system_spending / num_users if num_users else 0

    # Manually fetch paid orders for the user
    user_paid_orders = Order.query.filter_by(user_id=userId, is_Paid=1).all()
    total_user_spending = sum(order.total_amount for order in user_paid_orders)

     # Fetch total carbon offsets for the logged-in user
    user_carbon_offset = user.total_carbon_offset if user.total_carbon_offset else 0

    total_carbon_offset = sum(user.total_carbon_offset for user in users if user.total_carbon_offset is not None)
    num_users = len(users)
    average_carbon_offset = total_carbon_offset / num_users if num_users else 0

    return render_template('user/statistics.html', orders=orders, user=user, user_data=user_data,total_cost=total_cost,total_offset=total_offset,
                            total_user_spending=total_user_spending, average_system_spending=average_system_spending, user_carbon_offset=user_carbon_offset,
                           average_carbon_offset=average_carbon_offset)

#User Statistics
@app.route('/user/statistics1')
def user_statistics():
    # 获取所有用户的统计数据
    users = User.query.all()
    
    # 准备传递给模板的数据
    user_data = {
        'contributions': [user.total_contribution for user in users],
        'carbon_offsets': [user.total_carbon_offset for user in users],
        'carbon_footprints': [user.carbon_footprint for user in users]
    }
    '''    # Assuming we define the statistical interval as one month
    one_month_ago = datetime.now() - timedelta(days=30)

    # Calculate the total carbon footprints from the previous month
    # Calculate the carbon footprints from the previous month
    previous_carbon_footprints = []
    for user in users:
        # Query the user's previous record
        previous_record = User.query.filter(
            User.id == user.id,
            User.timestamp <= one_month_ago
        ).order_by(User.timestamp.desc()).first()

    previous_carbon_footprint = previous_record.carbon_footprint if previous_record else user.carbon_footprint
    previous_carbon_footprints.append(previous_carbon_footprint)
    # Calculate the differences
    carbon_footprint_differences = [
        current - previous for current, previous in zip(user_data['carbon_footprints'], previous_carbon_footprints)
    ]
    '''

    # Add the differences to the user_data dictionary
    #user_data['carbon_footprint_differences'] = carbon_footprint_differences

    # 渲染模板并传递数据
    return render_template('user/statistics1.html', user_data=user_data)

#Footprint
@app.route('/user/upload_foot', methods=['POST','GET'])
def upload_foot():
    user_id = session.get('user_id')  
    user = User.query.get(user_id)
    if request.method == 'POST':
        user.fname = request.form['fname']
        user.lname = request.form['lname']
        user.Uname = request.form['Uname']
        user.email = request.form['email']
        user.country = request.form['country']
        db.session.commit()

        return redirect(url_for('foot'))
        # return render_template("user/Footprintupdate.html",success_message=)
    else:

        return render_template("user/Footprintupdate.html",user=user)


@app.route("/login",methods=["POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        if email=="" and password=="":
            error_message = 'Empty username or password'
            return render_template('Homepage.html',error_message=error_message)
        else:
            authUser=User().query.filter_by(email=email).first()
            authAdmin=Admin().query.filter_by(email=email).first()
            authStaff=Staff().query.filter_by(email=email).first()

            if(authUser == None and authAdmin == None and authStaff == None):
                error_message = 'Email not found'
                return render_template('Homepage.html',error_message=error_message)
            elif(authUser):
                    if authUser and bcrypt.check_password_hash(authUser.password, password):
                        session['user_id']=authUser.id
                        session['user_email']=authUser.email
                        return redirect('/user/home')
                    else:
                        error_message = 'Incorrect Password User'
                        return render_template('Homepage.html',error_message=error_message)
            elif(authAdmin):
                if authAdmin and bcrypt.check_password_hash(authAdmin.password, password):
                    session['admin_id']=authAdmin.id
                    session['admin_email']=authAdmin.email
                    if(authAdmin.is_Staff == True):
                        session['staff_id']=authAdmin.id
                        session['staff_email']=authAdmin.email
                        return render_template('admin/LoginRole.html')
                    else:
                        return redirect('/admin/dashboard')
                else:
                    error_message = 'Incorrect Password Admin'
                    return render_template('Homepage.html',error_message=error_message)
            else:
                if authStaff.is_verified == False:
                    error_message = 'Staff is not approved'
                    return render_template('Homepage.html',error_message=error_message)
                else: 
                    if authStaff and bcrypt.check_password_hash(authStaff.password, password):
                        session['staff_id']=authStaff.id
                        session['staff_email']=authStaff.email
                        return redirect('/staff/dashboard')
                    else:
                        error_message = 'Incorrect Password Staff'
                        return render_template('Homepage.html',error_message=error_message)

#Paymentsumit
@app.route("/user/cart",methods=['GET','POST'])
def userCart():
    userId = session.get('user_id')
    user = User().query.filter_by(id=userId).first()
    if request.method == 'POST':
        cartItems = Cart().query.filter_by(user_id=userId).all()
        total_val = 0
        total_offset = 0
        total_contribution = 0
        for item in cartItems:
            product = Product().query.filter_by(id=item.product_id).first()
            total_val += (item.quantity * (Product().query.filter_by(id=item.product_id).first().price))
            total_contribution += product.price * item.quantity
            total_offset += product.carbon_offset_per_year * item.quantity
        
        new_order = Order(user_id=userId, order_date=datetime.datetime.now(), total_amount=total_val, is_Paid=False)

        # Add metrics for the user and order
        db.session.add(new_order)
        db.session.commit()
        metrics = Metrics(user_id=userId, order_id=new_order.id, contribution_done=total_contribution, total_carbon_offset=total_offset)
        db.session.add(metrics)
        db.session.commit()

        for items in cartItems:
            new_OrderDetail = OrderDetails(order_id=new_order.id , product_id=items.product_id, quantity=items.quantity)
            db.session.add(new_OrderDetail)
            db.session.commit()
            print('new_OrderDetail',new_OrderDetail.id)
            
        print('orderId',new_order.id)
        session['new_order_id'] = new_order.id
        return redirect(f"/user/payment/{new_order.id}")
    else:
        userId=session.get('user_id')
        cartItems = Cart().query.filter_by(user_id=userId).all()
        print(cartItems)
        productList = []
        for cart in cartItems:
            product = Product().query.filter_by(id=cart.product_id).first()
            productList.append(product)
        cartSize = len(cartItems)
        return render_template("user/cart.html", data = zip(cartItems,productList), cartSize=cartSize, client_id=client_id,user=user)

# Route to handle updating order status
@app.route('/user/order_Success.html', methods=['GET'])
def order_Success():
    if not session.get('user_id'):
        return redirect('/')
    userId = session.get('user_id')

    IDOfNewOrder = session.get('new_order_id')

    user = User().query.filter_by(id=userId).first()
    total_contribution = 0
    total_carbon_offset = 0
    # Calculate aggregated metrics for each order
    
    metric = Metrics.query.filter_by(order_id=IDOfNewOrder).first()
    if metric:
        total_contribution += metric.contribution_done
        total_carbon_offset += metric.total_carbon_offset

        # Update user's metrics
    if(user.total_contribution == None):
        user.total_contribution = total_contribution
    else:  
        user.total_contribution += total_contribution
    
    if(user.total_carbon_offset == None):
        user.total_carbon_offset = total_carbon_offset
    else:  
        user.total_carbon_offset += total_carbon_offset

    # user.total_carbon_offset += total_carbon_offset

    #order = Order.query.get_or_404(IDOfNewOrder)
    #order.is_paid = 1  # Update is_paid to 1 (paid)
    Order().query.filter_by(id=IDOfNewOrder).update(dict(is_Paid=True))
    # db.session.commit()  # Commit the change to the database
    session.pop('new_order_id', None)
    db.session.commit()

    Cart.query.filter_by(user_id=userId).delete()
    db.session.commit()

    print(Order().query.filter_by(id=IDOfNewOrder).first())

    return render_template("/user/order_Success.html")

@app.route("/user/product/<int:id>",methods=['POST','GET'])
def productPage(id):
    product = Product().query.filter_by(id=id).first()
    userId=session.get('user_id')
    user = User().query.filter_by(id=userId).first()
    if request.method == 'POST':
        cart_to_update = Cart().query.filter_by(user_id=userId,product_id=id).first()
        if cart_to_update:
            cart_to_update.quantity+=1
            db.session.add(cart_to_update)
            db.session.commit()

            # return render_template('user/product.html',product=product)
            return redirect(url_for('userCart'))
        else:
            cartToBeAdded = Cart(user_id=userId, product_id=id, quantity=1)
            db.session.add(cartToBeAdded)
            db.session.commit()
            return redirect(url_for('userCart'))
    else:
        product = Product().query.filter_by(id=id).first()
        return render_template('user/product.html',product=product,user=user)
    
@app.route("/product/<int:id>",methods=['POST','GET'])
def productPageWithoutLogin(id):
    product = Product().query.filter_by(id=id).first()
        
    product = Product().query.filter_by(id=id).first()
    return render_template('product.html',product=product)

@app.route('/IncrCart/<int:productId>',methods=['GET','POST'])
def IncrementCartValue(productId):
    if request.method=='POST':
        userId=session.get('user_id')
        cart_to_update = Cart().query.filter_by(user_id=userId,product_id=productId).first()
        cart_to_update.quantity+=1
        db.session.add(cart_to_update)
        db.session.commit()
        return redirect(url_for('userCart')) 

@app.route('/DecrCart/<int:productId>',methods=['GET','POST'])
def DecrementCartValue(productId):
    if request.method=='POST':
        userId=session.get('user_id')
        cart_to_update = Cart().query.filter_by(user_id=userId,product_id=productId).first()
        if(cart_to_update.quantity==1):
            db.session.delete(cart_to_update)
            db.session.commit()
            return redirect(url_for('userCart'))
        cart_to_update.quantity-=1
        db.session.add(cart_to_update)
        db.session.commit()
        return redirect(url_for('userCart')) 

@app.route("/loginRole")
def loginRole():
    return render_template('admin/loginRole.html')

@app.route("/loginAsAdmin")
def loginAsAdmin():
    session.pop('staff_id', None)
    session.pop('staff_email', None)
    return redirect('/admin/dashboard')

@app.route("/loginAsStaff")
def loginAsStaff():
    session.pop('admin_id', None)
    session.pop('admin_email', None)
    return redirect('/staff/dashboard')

@app.route("/filter_capacity")
def filter_capacity():
    if not session.get('user_id'):
        return redirect('/')
    userId = session.get('user_id')
    user=User().query.filter_by(id=userId).first()
    min_price = int(request.args.get('min_cap', 0))
    max_price = int(request.args.get('max_cap', 99999999))  
    sort_by = request.args.get('sort_by', 'asc') 

    products = Product.query.filter(Product.energy_production.between(min_price, max_price)).all()

    return render_template('user/home.html', products=products,user=user, sort_by=sort_by)

@app.route("/filter_capacity_2")
def filter_capacity_logged_out():
    min_price = int(request.args.get('min_cap', 0))
    max_price = int(request.args.get('max_cap', 99999999))  
    sort_by = request.args.get('sort_by', 'asc') 

    products = Product.query.filter(Product.energy_production.between(min_price, max_price)).all()

    return render_template('products.html', products=products,sort_by=sort_by)

@app.route("/filter_products")
def filter_products():
    if not session.get('user_id'):
        return redirect('/')
    userId = session.get('user_id')
    user=User().query.filter_by(id=userId).first()
    min_price = int(request.args.get('min_price', 0))
    max_price = int(request.args.get('max_price', 99999999))  
    sort_by = request.args.get('sort_by', 'asc') 

    products = Product.query.filter(Product.price.between(min_price, max_price)).all()

    return render_template('user/home.html', products=products,user=user, sort_by=sort_by)

@app.route("/filter_products_2")
def filter_products_logged_out():
    min_price = int(request.args.get('min_price', 0))
    max_price = int(request.args.get('max_price', 99999999))  
    sort_by = request.args.get('sort_by', 'asc') 

    products = Product.query.filter(Product.price.between(min_price, max_price)).all()

    return render_template('products.html', products=products,sort_by=sort_by)

@app.route("/user/home")
def user_home():
    if not session.get('user_id'):
        return redirect('/')
    userId = session.get('user_id')
    user=User().query.filter_by(id=userId).first()
    # products = Product().query.all()
    sort_by = request.args.get('sort_by', 'asc')  # Default sorting: ascending
    if sort_by == 'asc':
        products = Product.query.order_by(Product.price).all()
    elif sort_by == 'desc':
        products = Product.query.order_by(Product.price.desc()).all()
    else:
        products = Product.query.all()
    

    
    # print(products)
    return render_template('user/home.html',products=products,user=user, sort_by=sort_by)

@app.route("/forgotPassword")
def user_forgotpassword_homepage():
    return render_template('ForgotPassword.html')

@app.route('/user/carbon_footprint', methods=['POST'])
def handle_emission_value():
    if request.method == 'POST':
        userId = session.get('user_id')
        user = User().query.filter_by(id=userId).first()
        data = request.json
        emission_value = data.get('emissionValue')
        if emission_value is not None:
            user.carbon_footprint = emission_value
            db.session.commit()
            if user.carbon_footprint != None:
                user.offset_under_neutral = 0 if (user.carbon_footprint == None) else user.carbon_footprint - 0 if (user.total_carbon_offset == None) else user.total_carbon_offset
            db.session.commit()
            return jsonify({'message': 'Emission value received successfully'}), 200
        else:
            # If emission value is not found in the request data
            return jsonify({'error': 'Emission value not found in request data'}), 400

@app.route("/user/forgotPassword",methods=['GET','POST'])
def user_forgotpassword():
    userId = session.get('user_id')
    user = User().query.filter_by(id=userId).first()
    if request.method == 'POST':
        oldpwd = request.form.get('oldpwd')
        newpwd = request.form.get('newpwd')
        confirmnewpwd = request.form.get('confirmnewpwd')

        
        print(user)

        if(bcrypt.check_password_hash(user.password,oldpwd)):
            if(newpwd == confirmnewpwd):
                user.password = bcrypt.generate_password_hash(newpwd, 10).decode('utf-8')
                db.session.commit()
                return render_template('user/forgotPassword.html',success_message="Password updated successfully.")
            else:
                return render_template('user/forgotPassword.html',error_message="new password and confirm new password does not match")
        else:
            return render_template('user/forgotPassword.html',error_message="Old password does not match")
    else:
        # userId = session.get('user_id')
        # user = User().query.filter_by(id=userId).first()
        # print(user)
        # sample = '123'
        # print(bcrypt.check_password_hash(user.password,sample))
        return render_template('user/forgotPassword.html',user=user)

@app.route("/user/user_login")
def user_login():
    return render_template('user/login.html')


@app.route('/user/compareCountry', methods=['POST'])
def print_selected_countries():
    import json
    from flask import request, render_template

    # Assuming this route is located in a Flask application

    # Path to the JSON file containing country data
    file_path = './countries.json'

    # Read the country data from the JSON file
    with open(file_path, 'r') as f:
        countries_data = json.load(f)

    # Get the selected countries from the form
    selected_countries = request.form.getlist('countryCheckbox')

    compareCountries = []

    # Capitalize the names of the selected countries
    for country in countries_data:
        if country['name'] in selected_countries:
            compareCountries.append(country)

    # Uncomment the line below if you want to pass the modified country data to a template
    # return render_template('user/countryComparisonPage.html', countries=countries_data)
    print(compareCountries)
    return "Selected countries processed successfully"



@app.route("/user/countryComparisonPage")
def user_country_comparison_page():
    file_path = './countries.json'
    with open(file_path, 'r') as f:
        countries = json.load(f)
        
    for country in countries:
        capitalized_name = country['name'].capitalize()
        country['name'] = capitalized_name
    # countries = [
    #     {"name": "Spain", "population": "47.42 M", "flag_url": "https://upload.wikimedia.org/wikipedia/en/9/9a/Flag_of_Spain.svg", "description": "Spain National flag"},
    #     {"name": "Portugal", "population": "10.33 M", "flag_url": "https://upload.wikimedia.org/wikipedia/commons/5/5c/Flag_of_Portugal.svg", "description": "Portugal National flag"},
    #     {"name": "Italy", "population": "59.11 M", "flag_url": "https://upload.wikimedia.org/wikipedia/en/0/03/Flag_of_Italy.svg", "description": "Italy National flag"}
    #     # Add more country data as needed
    # ]
    return render_template('user/countryComparisonPage.html', countries=countries)

@app.route('/order_data')
def order_data():
    # Get total amount contributed per month for the last 6 months
    six_months_ago = datetime.datetime.now() - datetime.timedelta(days=30*6)
    
    # Aggregate total amount contributed per month for the last 6 months
    total_contributions = db.session.query(func.strftime("%Y-%m", Order.order_date), func.sum(Order.total_amount)).\
                          join(OrderDetails).\
                          filter(Order.order_date >= six_months_ago).\
                          group_by(func.strftime("%Y-%m", Order.order_date)).all()
    
    # Convert the result to a list of dictionaries for easy JSON serialization
    # data = [{'month': entry[0], 'total_amount': entry[1]} for entry in total_contributions]
    data = [
  {"month": "2023-01", "total_amount": 100},
  {"month": "2023-02", "total_amount": 150},
  {"month": "2023-03", "total_amount": 200},
  {"month": "2023-04", "total_amount": 180},
  {"month": "2023-05", "total_amount": 220},
  {"month": "2023-06", "total_amount": 250}
]
    
    # Return the data as JSON
    return jsonify(data)

@app.route("/user/register",methods=['POST','GET'])
def user_register():
    if request.method == 'GET':
        return render_template('user/register.html')
    else:
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        country = request.form.get('country')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if(fname == '' or lname == '' or email == '' or password == '' or confirm_password == ''):
            return render_template('/user/register.html',error_message="Please fill all the fields")
        elif(password != confirm_password):
            return render_template('/user/register.html',error_message="Passwords do not match")
        elif not (User().query.filter_by(email=email)):
            return render_template('/user/register.html',error_message="Email already exists")
        else:
            authUser = User(fname=fname,lname=lname,email=email,country=country,password=bcrypt.generate_password_hash(password, 10).decode('utf-8'))
            db.session.add(authUser)
            db.session.commit()
            return render_template('/user/register.html',success_message="Registration Successful, please login")

@app.route("/staff/register",methods=['POST','GET'])
def staff_register():
    if request.method == 'GET':
        return render_template('staff/register.html')
    else:
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if(fname == '' or lname == '' or email == '' or password == '' or confirm_password == ''):
            return render_template('/staff/register.html',error_message="Please fill all the fields")
        elif(password != confirm_password):
            return render_template('/staff/register.html',error_message="Passwords do not match")
        elif (Staff().query.filter_by(email=email).first() != None):
            return render_template('/staff/register.html',error_message="Email already exists")
        else:
            authStaff = Staff(fname=fname,lname=lname,email=email,password=bcrypt.generate_password_hash(password, 10).decode('utf-8'),is_verified=False)
            db.session.add(authStaff)
            db.session.commit()
            return render_template('/staff/register.html',success_message="Registration Successful, Approval pending by admin")

@app.route('/user/update_profile', methods=['POST','GET'])
def update_profile():
    if request.method == 'POST':
        userId = session.get('user_id') 
        user = User().query.filter_by(id=userId).first()
    
        # email = request.form.get('email')
        # firstname = request.form.get('firstname')
        # lastname = request.form.get('lastname')
        # country = request.form.get('country')
        user.fname = request.form.get('fname')
        user.lname = request.form.get('lname')
        if(request.form.get('country') != None):
            user.country = request.form.get('country')

        db.session.commit()

        user = User().query.filter_by(id=userId).first()
        # return redirect(url_for('user_profile'))
        return render_template("user/updateProfile.html",user=user,success_message='Profile updated')
    else:
        userId = session.get('user_id')
        user = User().query.filter_by(id=userId).first()
        return render_template("user/updateProfile.html",user=user)
            
@app.route('/user/addToCheckoutList/<int:product_id>', methods=['GET'])
def user_addToCheckoutList(product_id):
    if not session.get('user_id'):
        return redirect('/')
    print(product_id)
    return redirect(url_for('user_home'))

@app.route("/staff/dashboard")
def staff_dashboard():
    if not session.get('staff_id'):
        return redirect('/')
    orders = Order().query.all()
    metrics = Metrics().query.all()
    total_contribution = sum(order.total_amount for order in orders)
    # total_offset = sum(order.total_amount for order in orders)
    total_offset = sum(metrics.total_carbon_offset for metrics in metrics)
    users = User().query.all()
    staffId = session.get('staff_id')
    staff = Staff().query.filter_by(id=staffId).first()

    # Querying counts of users with different carbon footprints
    num_negative_carbon_users = User.query.filter(User.offset_under_neutral  > 0).count()
    num_positive_carbon_users = User.query.filter(User.offset_under_neutral  < 0).count()
    num_neutral_carbon_users = User.query.filter(User.offset_under_neutral == None).count()
    num_neutral_carbon_users2 = User.query.filter(User.offset_under_neutral == 0).count()
    return render_template('staff/dashboard.html',staff=staff,orders=orders,users=users,total_contribution=total_contribution,total_offset=total_offset,num_negative_carbon_users=num_negative_carbon_users,num_positive_carbon_users=num_positive_carbon_users,num_neutral_carbon_users=num_neutral_carbon_users+num_neutral_carbon_users2)

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get('admin_id'):
        return redirect('/')
    admin = Admin().query.filter_by(id=session.get('admin_id')).first()
    users = User().query.all()
    staffs = Staff().query.all()
    admins = Admin().query.all()
    return render_template('admin/dashboard.html',users=users,staffs=staffs,admins=admins, admin=admin)

@app.route("/admin/allUsers")
def admin_allUsers():
    if not session.get('admin_id'):
        return redirect('/')
    admin = Admin().query.filter_by(id=session.get('admin_id')).first()
    users = User().query.all()
    return render_template('admin/allUsers.html',users=users,admin=admin)

@app.route("/staff/allUsers")
def staff_allUsers():
    if not session.get('staff_id'):
        return redirect('/')
    staffId = session.get('staff_id')
    staff = Staff().query.filter_by(id=staffId).first()
    users = User().query.all()
    return render_template('staff/allUsers.html',users=users,staff=staff)

#admin approve staff
@app.route('/admin/approve-user/<int:id>')
def adminApprove(id):
    if not session.get('admin_id'):
        return redirect('/')
    Staff().query.filter_by(id=id).update(dict(is_verified=True))
    db.session.commit()
    staffs = Staff().query.all()
    # print(staffs)
    return render_template('admin/allStaff.html',staffs=staffs,alert_message_approved="Staff with ID: "+str(id)+" has been approved")

#admin disapprove staff
@app.route('/admin/disapprove-user/<int:id>')
def adminDisapprove(id):
    if not session.get('admin_id'):
        return redirect('/')
    Staff().query.filter_by(id=id).update(dict(is_verified=False))
    db.session.commit()
    staffs = Staff().query.all()
    print(staffs)
    return render_template('admin/allStaff.html',staffs=staffs,alert_message_disapproved="Staff with ID: "+str(id)+" has been disaproved.")

@app.route("/admin/allStaff")
def admin_allStaff():
    if not session.get('admin_id'):
        return redirect('/')
    admin = Admin().query.filter_by(id=session.get('admin_id')).first()
    staffs = Staff().query.all()
    # print(staffs)
    return render_template('admin/allStaff.html',staffs=staffs,admin=admin)

@app.route("/admin/allAdmin")
def admin_allAdmin():
    if not session.get('admin_id'):
        return redirect('/')
    admins = Admin().query.all()
    admin = Admin().query.filter_by(id=session.get('admin_id')).first()
    print("this is admins:",len(admins))
    return render_template('admin/allAdmin.html',admins=admins,admin=admin)

@app.route('/admin/addStaff', methods=['GET', 'POST'])
def admin_addStaff():
    if not session.get('admin_id'):
            return redirect('/')
    admin = Admin().query.filter_by(id=session.get('admin_id')).first()
    if request.method == 'POST':
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        password = generate_random_password()

        new_staff = Staff(fname=fname, lname=lname, email=email, password=bcrypt.generate_password_hash(password, 10).decode('utf-8'))

        db.session.add(new_staff)
        db.session.commit()
        return render_template("admin/addStaff.html", success_message="Staff has been created.", email=email, password=password,admin=admin)
    else:
        return render_template("admin/addStaff.html", admin=admin)


@app.route("/admin/addProduct", methods=['GET', 'POST'])
def admin_addProduct():
    if not session.get('admin_id'):
            return redirect('/')
    admin = Admin().query.filter_by(id=session.get('admin_id')).first()
    if request.method == 'POST':
        # Extract form data
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        country = request.form['country']
        population = int(request.form['population'])
        impact = request.form['impact']
        energy_production = float(request.form['energy_production'])
        time_to_recover_expense = int(request.form['time_to_recover_expense'])
        carbon_offset_per_year = float(request.form['carbon_offset_per_year'])
        electricity_grid_network_km = float(request.form['electricity_grid_network_km'])

        new_product = Product(
            name=name,
            description=description,
            price=price,
            country=country,
            population=population,
            impact=impact,
            energy_production=energy_production,
            time_to_recover_expense=time_to_recover_expense,
            carbon_offset_per_year=carbon_offset_per_year,
            electricity_grid_network_km=electricity_grid_network_km
        )

        db.session.add(new_product)
        db.session.commit()
        return render_template("admin/addProduct.html", success_message="Product has been added",admin=admin)

    else:
        return render_template("admin/addProduct.html",admin=admin)

@app.route('/admin/addUser', methods=['GET', 'POST'])
def admin_addUser():
    if not session.get('admin_id'):
        return redirect('/')
    admin = Admin().query.filter_by(id=session.get('admin_id')).first()
    if request.method == 'POST':
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        country = request.form['country']
        password = generate_random_password()

        new_user = User(
            fname=fname,
            lname=lname,
            email=email,
            country=country,
            password=bcrypt.generate_password_hash(password, 10).decode('utf-8')
        )

        db.session.add(new_user)
        db.session.commit()

        return render_template('admin/addUser.html', success_message="User has been created.", email=email, password=password,admin=admin)
    else:
        return render_template('admin/addUser.html', admin=admin)

@app.route('/admin/addAdmin', methods=['GET', 'POST'])
def admin_form():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_random_password()

        new_admin = Admin(email=email, password=bcrypt.generate_password_hash(password, 10).decode('utf-8'))

        db.session.add(new_admin)
        db.session.commit()

        return render_template('admin/addAdmin.html', success_message="Admin has been created.",email=email, password=password)
    else:
        return render_template('admin/addAdmin.html')
    
@app.route('/admin/changeUserPwd/<int:id>', methods=['GET', 'POST'])
def admin_changeUserPwd(id):
    user = User().query.filter_by(id=id).first()
    admin = Admin().query.filter_by(id=session.get('admin_id')).first()
    if request.method == 'GET':
        return render_template('admin/changeUserPwd.html',user=user,admin=admin)
    else:
        email = request.form['email']
        print("email: ",email)
        password = generate_random_password()

        User.query.filter_by(id=id).update({User.password: bcrypt.generate_password_hash(password, 10).decode('utf-8')})
        db.session.commit()

        return render_template('admin/changeUserPwd.html',success_message="User password has been reset.",email=email, password=password,user=user,admin=admin)
    
@app.route('/admin/changeUserProfile/<int:id>', methods=['GET', 'POST'])
def admin_changeUserProfile(id):
    user = User().query.filter_by(id=id).first()
    admin = Admin().query.filter_by(id=session.get('admin_id')).first()
    if request.method == 'POST':
        user.fname = request.form.get('firstname')
        user.lname = request.form.get('lastname')
        if(request.form.get('country') != None):
            user.country = request.form.get('country')

        db.session.commit()

        return render_template('admin/changeUserProfile.html', success_message="User profile Updated successfully.", user=user, admin=admin)
    else:
        return render_template('admin/changeUserProfile.html',user=user, admin=admin)
    
@app.route('/admin/changeStaffProfile/<int:id>', methods=['GET', 'POST'])
def admin_changeStaffProfile(id):
    staff = Staff().query.filter_by(id=id).first()
    admin = Admin().query.filter_by(id=session.get('admin_id')).first()
    if request.method == 'POST':
        email = request.form.get('email')
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')

        # Update staff details
        staff.email = email
        staff.fname = firstname
        staff.lname = lastname

        db.session.commit()

        return render_template('admin/changeStaffProfile.html', success_message="Staff has been updated.",email=email,staff=staff,admin=admin)
    else:
        return render_template('admin/changeStaffProfile.html',staff=staff,admin=admin)
    
@app.route('/admin/changeStaffPwd/<int:id>', methods=['GET', 'POST'])
def admin_changeStaffPwd(id):
    staff = Staff().query.filter_by(id=id).first()
    admin = Admin().query.filter_by(id=session.get('admin_id')).first()
    if request.method == 'POST':
        email = request.form['email']
        password = generate_random_password()

        Staff.query.filter_by(id=id).update({Staff.password: bcrypt.generate_password_hash(password, 10).decode('utf-8')})

        db.session.commit()

        return render_template('admin/addAdmin.html', success_message="Staff has been updated.",email=email, password=password, admin=admin)
    else:
        return render_template('admin/changeStaffPwd.html',staff=staff,admin=admin)

@app.route('/admin/EnableStaffAccess/<int:id>', methods=['GET'])
def admin_EnableStaffAccess(id):
    if not session.get('admin_id'):
        return redirect('/')
    admin = Admin().query.filter_by(id=id).first()
    admin.is_Staff = True
    db.session.commit()
    return render_template('admin/allAdmin.html',admins = Admin().query.all(),success_message_enabled="Yes",email=admin.email)

@app.route('/admin/DisableStaffAccess/<int:id>', methods=['GET'])
def admin_DisableStaffAccess(id):
    if not session.get('admin_id'):
        return redirect('/')
    admin = Admin().query.filter_by(id=id).first()
    admin.is_Staff = False
    db.session.commit()
    return render_template('admin/allAdmin.html',admins = Admin().query.all(),success_message_disabled="Yes",email=admin.email)
    

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('homepage'))

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

import secrets
import string

def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(characters) for i in range(length))
    return password

if __name__=="__main__":
    app.run(debug=True)