from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify
import boto3
import uuid
import os
import hashlib
from datetime import datetime
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pickle-secret-key-2025')

# AWS Configuration
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', 'arn:aws:sns:us-east-1:123456789012:OrderConfirmations')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@pickles.com')

# AWS clients using IAM role (EC2 attached)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
sns = boto3.client('sns', region_name=AWS_REGION)
ec2 = boto3.client('ec2', region_name=AWS_REGION)
iam = boto3.client('iam', region_name=AWS_REGION)
ses = boto3.client('ses', region_name=AWS_REGION)

# DynamoDB tables - Production ready
order_table = dynamodb.Table('PickleOrders')
user_table = dynamodb.Table('PickleUsers')
contact_table = dynamodb.Table('PickleContacts')

def hash_password(password):
    """Hash password for secure storage"""
    return hashlib.sha256(password.encode()).hexdigest()

def send_email_notification(to_email, subject, message):
    """Send email via SNS and SES"""
    try:
        # Send via SNS
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject=subject
        )
        
        # Send via SES for direct email
        ses.send_email(
            Source=ADMIN_EMAIL,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': message}}
            }
        )
        return True
    except ClientError:
        return False

def get_instance_info():
    """Get EC2 instance metadata"""
    try:
        import urllib.request
        response = urllib.request.urlopen('http://169.254.169.254/latest/meta-data/instance-id', timeout=2)
        return response.read().decode('utf-8')
    except:
        return 'local'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/order', methods=['GET', 'POST'])
def order():
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            phone = request.form['phone']
            address = request.form['address']
            city = request.form['city']
            pincode = request.form['pincode']
            item = request.form['item']
            quantity = int(request.form['quantity'])
            notes = request.form.get('notes', '')
            order_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()

            # Save to DynamoDB with full order details
            order_table.put_item(Item={
                'order_id': order_id,
                'name': name,
                'email': email,
                'phone': phone,
                'address': address,
                'city': city,
                'pincode': pincode,
                'item': item,
                'quantity': quantity,
                'notes': notes,
                'timestamp': timestamp,
                'status': 'pending',
                'total_amount': quantity * 100  # Sample pricing
            })

            # Send email notifications
            customer_message = f"Dear {name},\n\nYour order has been placed successfully!\n\nOrder ID: {order_id}\nItem: {item}\nQuantity: {quantity}\n\nWe'll contact you soon for delivery details.\n\nThank you for choosing Homemade Pickles & Snacks!"
            admin_message = f"New Order Received!\n\nOrder ID: {order_id}\nCustomer: {name}\nEmail: {email}\nPhone: {phone}\nItem: {item}\nQuantity: {quantity}\nAddress: {address}, {city} - {pincode}\nNotes: {notes}"
            
            send_email_notification(email, 'Order Confirmation - Homemade Pickles & Snacks', customer_message)
            send_email_notification(ADMIN_EMAIL, f'New Order - {order_id}', admin_message)

            session['last_order_id'] = order_id
            return redirect(url_for('sucess'))
        except Exception as e:
            flash(f'Order processing failed: {str(e)}', 'error')
            return render_template('order.html')
    return render_template('order.html')

@app.route('/notify')
def notify():
    # Send a sample SNS message
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message='A new order was received on Homemade Pickles & Snacks!',
        Subject='New Pickle Order Alert'
    )
    return "SNS notification sent!"

@app.route('/aws-info')
def aws_info():
    """Display AWS service information"""
    try:
        # Get EC2 instance info
        instance_id = get_instance_info()
        
        # Get IAM role info
        try:
            sts = boto3.client('sts', region_name='us-east-1')
            identity = sts.get_caller_identity()
            account_id = identity['Account']
            role_arn = identity.get('Arn', 'No role attached')
        except:
            account_id = 'Unknown'
            role_arn = 'No role attached'
        
        info = {
            'instance_id': instance_id,
            'account_id': account_id,
            'role_arn': role_arn,
            'region': 'us-east-1'
        }
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            message = request.form['message']
            contact_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()

            # Save contact inquiry to DynamoDB
            contact_table.put_item(Item={
                'contact_id': contact_id,
                'name': name,
                'email': email,
                'message': message,
                'timestamp': timestamp,
                'status': 'new'
            })

            # Send email notifications
            admin_message = f"New Contact Inquiry\n\nFrom: {name}\nEmail: {email}\nMessage: {message}"
            customer_message = f"Dear {name},\n\nThank you for contacting us! We have received your message and will get back to you soon.\n\nYour Message: {message}\n\nBest regards,\nHomemade Pickles & Snacks Team"
            
            send_email_notification(ADMIN_EMAIL, 'New Contact Inquiry', admin_message)
            send_email_notification(email, 'Thank you for contacting us', customer_message)
            
            return redirect(url_for('sucess'))
        except Exception as e:
            flash(f'Message sending failed: {str(e)}', 'error')
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            hashed_password = hash_password(password)

            # Check user in DynamoDB
            response = user_table.get_item(Key={'email': email})
            if 'Item' in response:
                stored_password = response['Item'].get('password')
                if stored_password == hashed_password:
                    session['user_email'] = email
                    session['user_name'] = response['Item'].get('name')
                    return redirect(url_for('home'))
            
            flash('Invalid email or password', 'error')
        except Exception as e:
            flash(f'Login failed: {str(e)}', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            hashed_password = hash_password(password)
            timestamp = datetime.utcnow().isoformat()

            # Check if user already exists
            response = user_table.get_item(Key={'email': email})
            if 'Item' in response:
                flash('User already exists', 'error')
                return render_template('signup.html')

            # Save user to DynamoDB
            user_table.put_item(Item={
                'email': email,
                'name': name,
                'password': hashed_password,
                'created_at': timestamp,
                'status': 'active'
            })

            # Send welcome email
            welcome_message = f"Dear {name},\n\nWelcome to Homemade Pickles & Snacks!\n\nYour account has been created successfully. You can now login and start ordering our delicious homemade pickles and snacks.\n\nThank you for joining us!\n\nBest regards,\nHomemade Pickles & Snacks Team"
            send_email_notification(email, 'Welcome to Homemade Pickles & Snacks!', welcome_message)
            
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Signup failed: {str(e)}', 'error')
    return render_template('signup.html')

@app.route('/sucess')
def sucess():
    return render_template('sucess.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        try:
            # Process checkout with DynamoDB integration
            name = request.form['fullName']
            email = request.form['email']
            phone = request.form['phone']
            address = request.form['address']
            notes = request.form.get('notes', '')
            order_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()

            # Save checkout details to DynamoDB
            order_table.put_item(Item={
                'order_id': order_id,
                'name': name,
                'email': email,
                'phone': phone,
                'address': address,
                'notes': notes,
                'timestamp': timestamp,
                'status': 'checkout_completed',
                'source': 'checkout'
            })

            # Send confirmation emails
            customer_message = f"Dear {name},\n\nYour checkout is complete!\n\nOrder ID: {order_id}\nWe'll process your order and contact you soon.\n\nThank you!"
            send_email_notification(email, 'Checkout Confirmation', customer_message)
            
            session['last_order_id'] = order_id
            return redirect(url_for('sucess'))
        except Exception as e:
            flash(f'Checkout failed: {str(e)}', 'error')
    return render_template('checkout.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/snacks')
def snacks():
    return render_template('snacks.html')

@app.route('/veg_pickles')
def veg_pickles():
    return render_template('veg_pickles.html')

@app.route('/non_veg_pickles')
def non_veg_pickles():
    return render_template('non_veg_pickles.html')


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)