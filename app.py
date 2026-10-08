from gevent import monkey
monkey.patch_all()
import os
from dotenv import load_dotenv

# Explicitly load .env from project root
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path, override=True)

# Allow HTTP for local OAuth testing (development)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = os.getenv('OAUTHLIB_INSECURE_TRANSPORT', '1')

from datetime import datetime, timedelta, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify, make_response
import razorpay
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func, desc, asc, case
import io
import re
import secrets
import hashlib
from collections import defaultdict
from flask_mail import Mail, Message
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from flask_socketio import SocketIO, emit, join_room
from authlib.integrations.flask_client import OAuth
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fashion-world-pro-secret-key-123')
db_url = os.getenv('DATABASE_URL', 'sqlite:///fashion_world.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True

# Upload configuration
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'images')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max limit
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'svg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Google OAuth 2.0 Configuration (Server-Side Flow)
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID', '').strip(),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET', '').strip(),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile',
        'claims_options': {
            'iat': {'leeway': 120},
            'exp': {'leeway': 120},
            'nbf': {'leeway': 120}
        }
    },
    authorize_params={
        'prompt': 'select_account'
    }
)

# Razorpay & Stripe Configuration (Dynamic .env integration)
def get_razorpay_client():
    """Dynamically initializes and returns Razorpay client, keys, and status with .env fallback"""
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path, override=True)
    key_id = (os.getenv('RAZORPAY_KEY_ID') or '').strip()
    key_secret = (os.getenv('RAZORPAY_KEY_SECRET') or '').strip()
    
    is_configured = bool(
        key_id and key_secret and 
        key_id != 'rzp_test_your_key_id' and 
        key_secret != 'your_key_secret' and
        not key_id.startswith('YOUR_')
    )
    
    client = None
    if is_configured:
        try:
            client = razorpay.Client(auth=(key_id, key_secret))
        except Exception as e:
            print(f"[RAZORPAY CLIENT ERROR] Could not initialize client: {e}")
            client = None
    elif key_id:
        # Fallback test instance if key is present
        try:
            client = razorpay.Client(auth=(key_id, key_secret or 'dummy_secret'))
        except Exception:
            client = None
            
    return client, key_id, key_secret, is_configured

RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', 'rzp_test_your_key_id')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', 'your_key_secret')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', 'pk_test_your_publishable_key')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', 'sk_test_your_secret_key')

try:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
except Exception:
    razorpay_client = None


# Flask-Mail Configuration (Gmail SMTP)
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com').strip()
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() in ('true', '1', 't', 'yes')
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'false').lower() in ('true', '1', 't', 'yes')
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '').strip()
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '').strip()
mail_sender = os.getenv('MAIL_DEFAULT_SENDER', '').strip() or app.config['MAIL_USERNAME']
app.config['MAIL_DEFAULT_SENDER'] = mail_sender if ('@' in mail_sender and '<' in mail_sender) else f"Fashion World Pro <{mail_sender}>" if mail_sender else "Fashion World Pro"

db = SQLAlchemy(app)
mail = Mail(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# Firebase Configuration & Admin SDK Initialization
FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID', 'fashion-world-pro')
FIREBASE_CONFIG = {
    'apiKey': os.getenv('FIREBASE_API_KEY', ''),
    'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN', f"{FIREBASE_PROJECT_ID}.firebaseapp.com"),
    'projectId': FIREBASE_PROJECT_ID,
    'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET', f"{FIREBASE_PROJECT_ID}.firebasestorage.app"),
    'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID', '46044413498'),
    'appId': os.getenv('FIREBASE_APP_ID', ''),
    'measurementId': os.getenv('FIREBASE_MEASUREMENT_ID', '')
}

try:
    import firebase_admin
    from firebase_admin import credentials as fb_credentials
    if not firebase_admin._apps:
        cred_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
        if cred_path and os.path.exists(cred_path):
            firebase_admin.initialize_app(fb_credentials.Certificate(cred_path), options={'projectId': FIREBASE_PROJECT_ID})
        else:
            firebase_admin.initialize_app(options={'projectId': FIREBASE_PROJECT_ID})
    print("[AUTH] Firebase Admin SDK initialized.")
except Exception as fb_init_err:
    print(f"[AUTH] Firebase Admin SDK initialization note: {fb_init_err}")

# -------------------------------
# DATABASE MODELS
# -------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    google_id = db.Column(db.String(150), unique=True, nullable=True)
    auth_provider = db.Column(db.String(50), default='local')
    firebase_uid = db.Column(db.String(150), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Profile Details for Auto-fill
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    city = db.Column(db.String(50))
    zip_code = db.Column(db.String(20))
    cart_items = db.relationship('CartItem', backref='user', lazy=True)
    wishlist_items = db.relationship('WishlistItem', backref='user', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    discount_price = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    stock = db.Column(db.Integer, default=50)
    size = db.Column(db.String(50), nullable=True)
    color = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_new_arrival = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviews = db.relationship('Review', backref='product', lazy=True)

    @property
    def gallery_images(self):
        """
        Returns an ordered list of image URLs for the product gallery carousel.
        Supports comma/semicolon/newline-separated multiple image URLs or single image URL.
        """
        if not self.image_url:
            return []

        # 1. Comma / semicolon / newline separated URLs in image_url field
        if any(sep in self.image_url for sep in [',', ';', '\n']):
            urls = [u.strip() for u in re.split(r'[,;\n]+', self.image_url) if u.strip()]
            if urls:
                return urls

        # 2. Sequential numbered companion files on disk (<base>_2.jpg, <base>_3.jpg, etc.)
        img_rel = self.image_url.lstrip('/')
        base_name, ext = os.path.splitext(img_rel)

        images = [self.image_url]
        for i in range(2, 6):
            candidate = f"{base_name}_{i}{ext}"
            disk_path = os.path.join(BASE_DIR, candidate.replace('/', os.sep))
            if os.path.isfile(disk_path):
                images.append('/' + candidate.replace('\\', '/'))
            else:
                break

        return images



class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    size = db.Column(db.String(50), nullable=True)
    product = db.relationship('Product')

class WishlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product = db.relationship('Product')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Pending') # Pending, Processing, Shipped, Delivered, Cancelled
    date_ordered = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Billing / Shipping Details
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(20))
    payment_method = db.Column(db.String(20)) # Razorpay, Stripe, UPI, COD, etc.
    payment_status = db.Column(db.String(20), default='Pending') # Pending, Paid, Failed, Refunded
    payment_id = db.Column(db.String(100))
    payment_signature = db.Column(db.String(200))
    razorpay_order_id = db.Column(db.String(100), nullable=True)
    payment_verified_at = db.Column(db.DateTime, nullable=True)
    shipping_fee = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    tracking_number = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_order = db.Column(db.Float, nullable=False)
    size = db.Column(db.String(50), nullable=True)
    product = db.relationship('Product')

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    user = db.relationship('User')

class SupportTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    order_id = db.Column(db.String(50), nullable=True)
    category = db.Column(db.String(50), nullable=False, default='Other Inquiries')
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Open') # Open, In Progress, Resolved, Closed
    priority = db.Column(db.String(20), default='Medium') # Low, Medium, High, Urgent
    admin_reply = db.Column(db.Text, nullable=True)
    admin_replied_by = db.Column(db.String(100), nullable=True)
    replied_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('support_tickets', lazy=True, order_by='SupportTicket.created_at.desc()'))

# Helper Decorator for Admin Authentication Protection
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Access Denied: Administrator privileges required.", "danger")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Auth Setup
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith('/admin'):
        flash("Access Denied: Administrator privileges required.", "danger")
        return redirect(url_for('admin_login'))
    flash("Please log in to access this page.", "info")
    return redirect(url_for('login', next=request.path))

@app.after_request
def add_no_cache_headers(response):
    if not request.path.startswith('/static'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@app.context_processor
def inject_global_data():
    cart_count = 0
    wishlist_count = 0
    open_tickets_count = 0
    low_stock_badge_count = 0
    if current_user.is_authenticated:
        try:
            cart_count = sum(item.quantity for item in current_user.cart_items)
        except Exception:
            cart_count = 0
        try:
            wishlist_count = WishlistItem.query.filter_by(user_id=current_user.id).count()
        except Exception:
            wishlist_count = 0
        if getattr(current_user, 'is_admin', False):
            try:
                open_tickets_count = SupportTicket.query.filter(func.lower(SupportTicket.status) == 'open').count()
            except Exception:
                open_tickets_count = 0
            try:
                low_stock_badge_count = Product.query.filter(Product.stock <= 5).count()
            except Exception:
                low_stock_badge_count = 0
    else:
        cart = session.get('cart', [])
        cart_count = len(cart)
    return dict(cart_count=cart_count, wishlist_count=wishlist_count, open_tickets_count=open_tickets_count, low_stock_badge_count=low_stock_badge_count)

# SocketIO Events
@socketio.on('join')
def on_join(data):
    room = f"user_{data['user_id']}"
    join_room(room)
    print(f"User {data['user_id']} joined room {room}")

@socketio.on('request_cart_sync')
def handle_cart_sync(data):
    user_id = data.get('user_id')
    if user_id:
        room = f"user_{user_id}"
        cart_items = CartItem.query.filter_by(user_id=user_id).all()
        count = sum(item.quantity for item in cart_items)
        emit('cart_updated', {'count': count}, room=room)

# -------------------------------------------------------------
# HIGH-CONFIDENCE CUSTOMER-FACING DEDUPLICATION
# -------------------------------------------------------------
_REP_IDS_CACHE = None
_REP_CACHE_TIME = 0
_REP_CACHE_PROD_COUNT = 0

def invalidate_rep_ids_cache():
    global _REP_IDS_CACHE, _REP_CACHE_TIME, _REP_CACHE_PROD_COUNT
    _REP_IDS_CACHE = None
    _REP_CACHE_TIME = 0
    _REP_CACHE_PROD_COUNT = 0

def get_unique_representative_product_ids(force_refresh=False):
    """
    Computes high-confidence unique representative product IDs for customer-facing listings.
    1. Audits products by category and exact image file/path / file hash.
    2. Category safe: deduplicates strictly WITHIN category (Men, Women, Kids).
    3. Representative ranking: Active -> Correct Category -> Complete Info -> Featured/New Arrival -> lowest ID.
    4. Caches in memory with auto-invalidation.
    """
    global _REP_IDS_CACHE, _REP_CACHE_TIME, _REP_CACHE_PROD_COUNT
    now = time.time()
    current_count = Product.query.count()
    if not force_refresh and _REP_IDS_CACHE is not None and (now - _REP_CACHE_TIME < 60) and (current_count == _REP_CACHE_PROD_COUNT):
        return _REP_IDS_CACHE

    static_dir = os.path.join(BASE_DIR, 'static')
    hash_cache = {}

    def get_image_key(p):
        img = (p.image_url or '').strip()
        if not img:
            return f"no_img_{p.id}"
        if img in hash_cache:
            return hash_cache[img]
        rel_path = img.lstrip('/')
        if rel_path.startswith('static/'):
            rel_path = rel_path[len('static/'):]
        full_path = os.path.join(static_dir, rel_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'rb') as f:
                    h = hashlib.md5(f.read()).hexdigest()
                    hash_cache[img] = h
                    return h
            except Exception:
                pass
        hash_cache[img] = f"url_{img}"
        return f"url_{img}"

    def compute_representative_score(p):
        score = 0
        if getattr(p, 'is_active', True):
            score += 10000
        if p.category and p.category.strip():
            score += 1000
        desc = (p.description or '').strip()
        if len(desc) > 80:
            score += 200
        elif len(desc) > 20:
            score += 100
        if p.size and p.size.strip():
            score += 50
        if p.color and p.color.strip():
            score += 50
        if (p.stock or 0) > 0:
            score += 50
        if getattr(p, 'is_featured', False):
            score += 500
        if getattr(p, 'is_new_arrival', False):
            score += 300
        return (score, -p.id)

    all_prods = Product.query.order_by(Product.id.asc()).all()
    groups = defaultdict(list)
    for p in all_prods:
        cat = (p.category or '').strip().title()
        img_k = get_image_key(p)
        groups[(cat, img_k)].append(p)

    rep_ids = set()
    for key, prods in groups.items():
        sorted_prods = sorted(prods, key=compute_representative_score, reverse=True)
        rep = sorted_prods[0]
        rep_ids.add(rep.id)

    _REP_IDS_CACHE = rep_ids
    _REP_CACHE_TIME = now
    _REP_CACHE_PROD_COUNT = current_count
    return _REP_IDS_CACHE

# Routes
@app.route('/products')
def products():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    category = request.args.get('category', '').strip()
    query = request.args.get('query', '').strip()
    filter_type = request.args.get('filter', '').strip()
    collection = request.args.get('collection', '').strip().lower()
    raw_sub = (request.args.get('sub') or request.args.get('subcategory') or '').strip().lower()
    sub = raw_sub.replace(' ', '_').replace('-', '_')
    
    rep_ids = get_unique_representative_product_ids()
    products_query = Product.query.filter(Product.is_active.is_(True), Product.id.in_(rep_ids))
    title = "All Collections"
    current_category = category

    if category:
        if category.lower() in ['men', 'mens']:
            products_query = products_query.filter(func.lower(Product.category) == 'men')
            title = "Men's Collection"
            current_category = "Men"
        elif category.lower() in ['women', 'womens']:
            products_query = products_query.filter(func.lower(Product.category) == 'women')
            title = "Women's Collection"
            current_category = "Women"
        elif category.lower() in ['kids', 'kids wear', 'kid', 'children', 'children wear', 'kid wear']:
            products_query = products_query.filter(func.lower(Product.category) == 'kids')
            title = "Kids Wear Collection"
            current_category = "Kids"
        else:
            products_query = products_query.filter(Product.category.ilike(f'%{category}%'))
            title = f"{category} Collection"

    if sub:
        sub_l = sub.lower()
        if current_category == "Men":
            if sub_l in ['formal', 'formal_wear', 'formals']:
                products_query = products_query.filter(
                    (Product.name.ilike('%Formal%')) | (Product.name.ilike('%Oxford%')) | (Product.name.ilike('%Two-Piece%')) |
                    (Product.name.ilike('%Three-Piece%')) | (Product.name.ilike('%Suit%')) | (Product.name.ilike('%Blazer%')) |
                    (Product.name.ilike('%Waistcoat%')) | (Product.name.ilike('%Pinstripe%')) | (Product.name.ilike('%Italian Collar%')) |
                    (Product.name.ilike('%French Cuff%'))
                ).filter(~Product.name.ilike('%Sherwani%')).filter(~Product.name.ilike('%Kurta%')).filter(~Product.name.ilike('%Night%')).filter(~Product.name.ilike('%Velvet%')).filter(~Product.name.ilike('%Tuxedo%'))
                title = "Men's Premium Formal Wear"
            elif sub_l in ['smart_casual', 'smart-casual', 'smart', 'casual']:
                products_query = products_query.filter(
                    (Product.name.ilike('%Polo%')) | (Product.name.ilike('%Casual%')) | (Product.name.ilike('%Overshirt%')) |
                    (Product.name.ilike('%Checked Shirt%')) | (Product.name.ilike('%Striped Shirt%')) | (Product.name.ilike('%Mandarin%')) |
                    (Product.name.ilike('%Egyptian Cotton%')) | (Product.name.ilike('%Crew Neck%')) | (Product.name.ilike('%T-Shirt%')) |
                    (Product.name.ilike('%Half-Zip%')) | (Product.name.ilike('%Cardigan%')) | (Product.name.ilike('%Button-Down%'))
                )
                title = "Men's Smart Casual Collection"
            elif sub_l in ['bottom', 'bottoms', 'jeans', 'trousers', 'chinos']:
                products_query = products_query.filter(
                    (Product.name.ilike('%Jeans%')) | (Product.name.ilike('%Chinos%')) | (Product.name.ilike('%Trousers%')) |
                    (Product.name.ilike('%Cargo%')) | (Product.name.ilike('%Joggers%'))
                )
                title = "Men's Premium Bottom Wear"
            elif sub_l in ['party', 'party_wear', 'evening']:
                products_query = products_query.filter(
                    (Product.name.ilike('%Velvet%')) | (Product.name.ilike('%Tuxedo%')) | (Product.name.ilike('%Party%')) |
                    (Product.name.ilike('%Dinner Jacket%')) | (Product.name.ilike('%Cocktail%')) | (Product.name.ilike('%Sequin%')) |
                    (Product.name.ilike('%Reception Suit%'))
                )
                title = "Men's Premium Party & Evening Wear"
            elif sub_l in ['ethnic', 'ethnic_wear', 'traditional']:
                products_query = products_query.filter(
                    (Product.name.ilike('%Kurta%')) | (Product.name.ilike('%Sherwani%')) | (Product.name.ilike('%Pathani%')) |
                    (Product.name.ilike('%Nehru Jacket%')) | (Product.name.ilike('%Bandhgala%')) | (Product.name.ilike('%Indo-Western%')) |
                    (Product.name.ilike('%Jodhpuri%')) | (Product.name.ilike('%Achkan%')) | (Product.name.ilike('%Chikankari%'))
                ).filter(~Product.name.ilike('%Wedding Sherwani%')).filter(~Product.name.ilike('%Wedding Suit%'))
                title = "Men's Premium Ethnic Wear"
            elif sub_l in ['wedding', 'groom', 'wedding_wear']:
                products_query = products_query.filter(
                    (Product.name.ilike('%Wedding%')) | (Product.name.ilike('%Groom%')) |
                    (Product.name.ilike('%Champagne%')) | (Product.name.ilike('%Bandhgala Wedding%')) | (Product.name.ilike('%Jodhpuri Wedding%')) |
                    (Product.name.ilike('%Indo-Western Set%')) | (Product.name.ilike('%Indo-Western Suit%'))
                )
                title = "Men's Wedding & Groom Collection"
            elif sub_l in ['lounge', 'nightwear', 'night', 'sleepwear']:
                products_query = products_query.filter(
                    (Product.name.ilike('%Night%')) | (Product.name.ilike('%Lounge%')) | (Product.name.ilike('%Sleepwear%')) |
                    (Product.name.ilike('%Pajama Set%')) | (Product.name.ilike('%Homewear%')) | (Product.name.ilike('%Comfort Shorts%'))
                )
                title = "Men's Night & Lounge Wear"
            elif sub_l in ['outerwear', 'jacket', 'jackets', 'coats']:
                products_query = products_query.filter(
                    (Product.name.ilike('%Denim Jacket%')) | (Product.name.ilike('%Suede Jacket%')) | (Product.name.ilike('%Bomber%')) |
                    (Product.name.ilike('%Harrington%')) | (Product.name.ilike('%Overcoat%')) | (Product.name.ilike('%Trench Coat%')) |
                    (Product.name.ilike('%Quilted%')) | (Product.name.ilike('%Moto%')) | (Product.name.ilike('%Casual Overshirt%'))
                )
                title = "Men's Premium Outerwear"
            elif sub_l in ['footwear', 'shoes', 'footwears']:
                products_query = products_query.filter(
                    (Product.name.ilike('%Shoes%')) | (Product.name.ilike('%Oxford%')) | (Product.name.ilike('%Derby%')) |
                    (Product.name.ilike('%Monk%')) | (Product.name.ilike('%Loafers%')) | (Product.name.ilike('%Sneakers%')) |
                    (Product.name.ilike('%Mojari%')) | (Product.name.ilike('%Jutti%')) | (Product.name.ilike('%Sandals%'))
                ).filter(~Product.name.ilike('%Shirt%')).filter(~Product.name.ilike('%Suit%'))
                title = "Men's Premium Footwear"
            elif sub_l in ['accessories', 'accessory']:
                products_query = products_query.filter(
                    (Product.name.ilike('%Belt%')) | (Product.name.ilike('%Wallet%')) | (Product.name.ilike('%Watch%')) |
                    (Product.name.ilike('%Sunglasses%')) | (Product.name.ilike('%Briefcase%')) | (Product.name.ilike('%Laptop Bag%')) |
                    (Product.name.ilike('%Messenger Bag%')) | (Product.name.ilike('%Backpack%')) | (Product.name.ilike('%Tie%')) |
                    (Product.name.ilike('%Pocket Square%')) | (Product.name.ilike('%Cufflinks%')) | (Product.name.ilike('%Stole%'))
                ).filter(~Product.name.ilike('%Kurta%'))
                title = "Men's Premium Accessories"
            else:
                products_query = products_query.filter((Product.name.ilike(f'%{sub}%')) | (Product.description.ilike(f'%{sub}%')))
                title = f"Men's {sub.replace('_', ' ').title()} Collection"
        elif current_category == "Kids":
            products_query = products_query.filter((Product.name.ilike(f'%{sub}%')) | (Product.description.ilike(f'%{sub}%')))
            title = f"Kids {sub.capitalize()} Collection"
        else:
            products_query = products_query.filter((Product.name.ilike(f'%{sub}%')) | (Product.description.ilike(f'%{sub}%')))
            title = f"{sub.replace('_', ' ').title()} Collection"

    if query:
        norm_q = re.sub(r"[^a-zA-Z0-9\s]", "", query.lower()).strip()
        mens_keywords = {'men', 'mens', 'mens wear', 'men wear', 'men clothing', 'male', 'menswear', 'mens clothing'}
        womens_keywords = {'women', 'womens', 'womens wear', 'women wear', 'women clothing', 'female', 'womenswear', 'womens clothing'}
        kids_keywords = {'kids', 'kids wear', 'kid wear', 'kid', 'children', 'children wear', 'child', 'boys wear', 'girls wear'}
        if norm_q in mens_keywords:
            products_query = products_query.filter(func.lower(Product.category) == 'men')
            title = "Men's Collection"
            current_category = "Men"
        elif norm_q in womens_keywords:
            products_query = products_query.filter(func.lower(Product.category) == 'women')
            title = "Women's Collection"
            current_category = "Women"
        elif norm_q in kids_keywords:
            products_query = products_query.filter(func.lower(Product.category) == 'kids')
            title = "Kids Wear Collection"
            current_category = "Kids"
        else:
            products_query = products_query.filter((Product.name.ilike(f'%{query}%')) | (Product.description.ilike(f'%{query}%')))
            title = f"Search Results for '{query}'"

    if filter_type == 'new_arrivals':
        products_query = products_query.filter((Product.is_new_arrival == True) | (Product.is_featured == True) | (Product.discount_price.isnot(None)))
        title = "New Season Arrivals"

    if collection:
        if collection in ['new_arrivals', 'new', 'new-arrivals']:
            products_query = products_query.filter((Product.is_new_arrival == True) | (Product.is_featured == True) | (Product.discount_price.isnot(None)))
            title = "New Arrivals Collection"
        elif collection in ['trending', 'trending_now', 'trending-now']:
            products_query = products_query.filter((Product.is_featured == True) | (Product.discount_price.isnot(None)))
            title = "Trending Now Collection"
        elif collection in ['men', 'mens', 'mens_collection', 'mens-collection']:
            products_query = products_query.filter(func.lower(Product.category) == 'men')
            title = "Men's Collection"
            current_category = "Men"
        elif collection in ['women', 'womens', 'womens_collection', 'womens-collection']:
            products_query = products_query.filter(func.lower(Product.category) == 'women')
            title = "Women's Collection"
            current_category = "Women"
        elif collection in ['kids', 'kids_wear', 'kids-wear', 'children']:
            products_query = products_query.filter(func.lower(Product.category) == 'kids')
            title = "Kids Wear Collection"
            current_category = "Kids"
        elif collection in ['ethnic', 'ethnic_edit', 'ethnic-edit']:
            products_query = products_query.filter((Product.name.ilike('%Scarf%')) | (Product.name.ilike('%Boho%')) | (Product.name.ilike('%Dress%')) | (Product.name.ilike('%Kurta%')))
            title = "Ethnic Edit Collection"
        elif collection in ['western', 'western_wear', 'western-wear']:
            products_query = products_query.filter((Product.name.ilike('%Jeans%')) | (Product.name.ilike('%Jacket%')) | (Product.name.ilike('%Cardigan%')) | (Product.name.ilike('%Chinos%')))
            title = "Western Wear Collection"
        elif collection in ['party', 'party_occasion', 'party-occasion', 'party_and_occasion']:
            products_query = products_query.filter((Product.name.ilike('%Clutch%')) | (Product.name.ilike('%Silk%')) | (Product.name.ilike('%Maxi%')) | (Product.name.ilike('%Suit%')) | (Product.name.ilike('%Party%')))
            title = "Party & Occasion Collection"
        elif collection in ['casual', 'casual_everyday', 'casual-everyday']:
            products_query = products_query.filter((Product.name.ilike('%Shirt%')) | (Product.name.ilike('%Tee%')) | (Product.name.ilike('%Polos%')) | (Product.name.ilike('%Chinos%')) | (Product.name.ilike('%Sweatshirt%')) | (Product.name.ilike('%Shorts%')))
            title = "Casual Everyday Collection"
        elif collection in ['footwear', 'footwear_edit', 'footwear-edit']:
            products_query = products_query.filter((Product.name.ilike('%Socks%')) | (Product.name.ilike('%Joggers%')) | (Product.name.ilike('%Shoes%')))
            title = "Footwear Edit Collection"
        elif collection in ['accessories', 'accessories_edit', 'accessories-edit']:
            products_query = products_query.filter((Product.name.ilike('%Belt%')) | (Product.name.ilike('%Clutch%')) | (Product.name.ilike('%Scarf%')) | (Product.name.ilike('%Mask%')) | (Product.name.ilike('%Headband%')))
            title = "Accessories Collection"
        elif collection in ['beauty', 'beauty_selfcare', 'beauty-selfcare', 'beauty_self_care']:
            products_query = products_query.filter((Product.name.ilike('%Headband%')) | (Product.name.ilike('%Mask%')) | (Product.name.ilike('%Silk%')))
            title = "Beauty & Self Care Collection"
        elif collection in ['festive', 'festive_collection', 'festive-collection']:
            products_query = products_query.filter((Product.name.ilike('%Silk%')) | (Product.name.ilike('%Maxi%')) | (Product.name.ilike('%Suit%')) | (Product.name.ilike('%Scarf%')) | (Product.name.ilike('%Kurta%')))
            title = "Festive Collection"
        
    sort_by = request.args.get('sort', 'default').strip().lower()
    if sort_by in ['price_asc', 'low_to_high', 'price_low_high']:
        effective_price = case((Product.discount_price.isnot(None), Product.discount_price), else_=Product.price)
        products_query = products_query.order_by(effective_price.asc(), Product.id.asc())
    elif sort_by in ['price_desc', 'high_to_low', 'price_high_low']:
        effective_price = case((Product.discount_price.isnot(None), Product.discount_price), else_=Product.price)
        products_query = products_query.order_by(effective_price.desc(), Product.id.asc())
    else:
        products_query = products_query.order_by(Product.is_featured.desc(), Product.id.asc())

    pagination = products_query.paginate(page=page, per_page=per_page, error_out=False)
    all_products = pagination.items
    
    return render_template('products.html', products=all_products, pagination=pagination, title=title, current_category=current_category, current_collection=collection, current_sub=sub, current_sort=sort_by)

@app.route('/specials')
def specials():
    rep_ids = get_unique_representative_product_ids()
    special_products = Product.query.filter(Product.discount_price.isnot(None), Product.is_active.is_(True), Product.id.in_(rep_ids)).all()
    return render_template('products.html', products=special_products, title="Exclusive Special Offers")

@app.route('/search')
def search():
    query = request.args.get('query', '').strip()
    if query:
        norm_q = re.sub(r"[^a-zA-Z0-9\s]", "", query.lower()).strip()
        mens_keywords = {'men', 'mens', 'mens wear', 'men wear', 'men clothing', 'male', 'menswear', 'mens clothing'}
        womens_keywords = {'women', 'womens', 'womens wear', 'women wear', 'women clothing', 'female', 'womenswear', 'womens clothing'}
        kids_keywords = {'kids', 'kids wear', 'kid wear', 'kid', 'children', 'children wear', 'child', 'boys wear', 'girls wear'}
        if norm_q in mens_keywords:
            return redirect(url_for('products', category='Men'))
        elif norm_q in womens_keywords:
            return redirect(url_for('products', category='Women'))
        elif norm_q in kids_keywords:
            return redirect(url_for('products', category='Kids'))
    return redirect(url_for('products', query=query))

@app.route('/api/search/suggestions')
def search_suggestions():
    raw_query = request.args.get('q', '').strip()
    if not raw_query:
        return jsonify({'intent': None, 'categories': [], 'products': [], 'view_all_url': None, 'view_all_text': None})
    
    rep_ids = get_unique_representative_product_ids()
    norm_q = re.sub(r"[^a-zA-Z0-9\s]", "", raw_query.lower()).strip()
    mens_keywords = {'men', 'mens', 'mens wear', 'men wear', 'men clothing', 'male', 'menswear', 'mens clothing'}
    womens_keywords = {'women', 'womens', 'womens wear', 'women wear', 'women clothing', 'female', 'womenswear', 'womens clothing'}
    kids_keywords = {'kids', 'kids wear', 'kid wear', 'kid', 'children', 'children wear', 'child', 'boys wear', 'girls wear'}
    
    is_mens = (norm_q in mens_keywords) or any(norm_q.startswith(k + ' ') for k in ['men', 'mens', 'male'])
    is_womens = (norm_q in womens_keywords) or any(norm_q.startswith(k + ' ') for k in ['women', 'womens', 'female'])
    is_kids = (norm_q in kids_keywords) or any(norm_q.startswith(k + ' ') for k in ['kids', 'kid', 'children', 'child'])
    
    categories = []
    products_data = []
    intent = None
    view_all_url = None
    view_all_text = None
    
    if is_mens:
        intent = 'men'
        categories = [
            {'name': "MEN'S WEAR", 'url': url_for('products', category='Men'), 'icon': 'fa-solid fa-person', 'badge': 'Category'},
            {'name': "Men's Clothing", 'url': url_for('products', category='Men'), 'icon': 'fa-solid fa-shirt', 'badge': 'Clothing'}
        ]
        real_prods = Product.query.filter(func.lower(Product.category) == 'men', Product.is_active == True, Product.id.in_(rep_ids)).limit(4).all()
        for p in real_prods:
            products_data.append({
                'id': p.id,
                'name': p.name,
                'category': p.category,
                'price': f"₹{int(p.discount_price)}" if p.discount_price else f"₹{int(p.price)}",
                'original_price': f"₹{int(p.price)}" if p.discount_price else None,
                'image_url': p.image_url,
                'url': url_for('product_detail', product_id=p.id)
            })
        view_all_url = url_for('products', category='Men')
        view_all_text = "View Men's Collection →"
        
    elif is_womens:
        intent = 'women'
        categories = [
            {'name': "WOMEN'S WEAR", 'url': url_for('products', category='Women'), 'icon': 'fa-solid fa-person-dress', 'badge': 'Category'},
            {'name': "Women's Clothing", 'url': url_for('products', category='Women'), 'icon': 'fa-solid fa-vest', 'badge': 'Clothing'}
        ]
        real_prods = Product.query.filter(func.lower(Product.category) == 'women', Product.is_active == True, Product.id.in_(rep_ids)).limit(4).all()
        for p in real_prods:
            products_data.append({
                'id': p.id,
                'name': p.name,
                'category': p.category,
                'price': f"₹{int(p.discount_price)}" if p.discount_price else f"₹{int(p.price)}",
                'original_price': f"₹{int(p.price)}" if p.discount_price else None,
                'image_url': p.image_url,
                'url': url_for('product_detail', product_id=p.id)
            })
        view_all_url = url_for('products', category='Women')
        view_all_text = "View Women's Collection →"

    elif is_kids:
        intent = 'kids'
        categories = [
            {'name': "KIDS WEAR", 'url': url_for('products', category='Kids'), 'icon': 'fa-solid fa-child', 'badge': 'Category'},
            {'name': "Boys Wear", 'url': url_for('products', category='Kids', sub='boys'), 'icon': 'fa-solid fa-child-reaching', 'badge': 'Boys'},
            {'name': "Girls Wear", 'url': url_for('products', category='Kids', sub='girls'), 'icon': 'fa-solid fa-child-dress', 'badge': 'Girls'}
        ]
        real_prods = Product.query.filter(func.lower(Product.category) == 'kids', Product.is_active == True, Product.id.in_(rep_ids)).limit(4).all()
        for p in real_prods:
            products_data.append({
                'id': p.id,
                'name': p.name,
                'category': p.category,
                'price': f"₹{int(p.discount_price)}" if p.discount_price else f"₹{int(p.price)}",
                'original_price': f"₹{int(p.price)}" if p.discount_price else None,
                'image_url': p.image_url,
                'url': url_for('product_detail', product_id=p.id)
            })
        view_all_url = url_for('products', category='Kids')
        view_all_text = "VIEW KIDS COLLECTION →"
        
    else:
        # Standard search
        matching_categories = Category.query.filter(Category.name.ilike(f'%{raw_query}%')).all()
        for cat in matching_categories:
            cat_label = cat.name.upper() + " WEAR" if cat.name.upper() in ['MEN', 'WOMEN', 'KIDS'] else cat.name
            categories.append({
                'name': cat_label,
                'url': url_for('products', category=cat.name),
                'icon': 'fa-solid fa-tag',
                'badge': 'Category'
            })
            
        real_prods = Product.query.filter(
            (Product.name.ilike(f'%{raw_query}%')) | (Product.description.ilike(f'%{raw_query}%'))
        ).filter(Product.is_active == True, Product.id.in_(rep_ids)).limit(4).all()
        
        for p in real_prods:
            products_data.append({
                'id': p.id,
                'name': p.name,
                'category': p.category,
                'price': f"₹{int(p.discount_price)}" if p.discount_price else f"₹{int(p.price)}",
                'original_price': f"₹{int(p.price)}" if p.discount_price else None,
                'image_url': p.image_url,
                'url': url_for('product_detail', product_id=p.id)
            })
            
        if len(products_data) > 0 or len(categories) > 0:
            view_all_url = url_for('products', query=raw_query)
            view_all_text = f"View All Results for '{raw_query}' →"

    return jsonify({
        'intent': intent,
        'query': raw_query,
        'categories': categories,
        'products': products_data,
        'view_all_url': view_all_url,
        'view_all_text': view_all_text
    })

# ==============================================================================
# FASHION CHATBOT / SHOPPING ASSISTANT API
# ==============================================================================
@app.route('/api/chatbot', methods=['POST'])
def api_chatbot():
    payload = request.get_json(silent=True) or {}
    raw_msg = (payload.get('message') or '').strip()
    if not raw_msg:
        return jsonify({
            'type': 'text',
            'message': "Hi! 👋 I'm your Fashion World Pro personal assistant. How can I help you today?",
            'quick_replies': ["👕 Men's Wear", "👗 Women's Wear", "👶 Kids Wear", "🔥 Flash Sale", "📏 Find My Size", "🛍️ My Cart", "❤️ My Wishlist", "📦 My Orders", "🎧 Contact Support"]
        })
    
    msg_lower = raw_msg.lower()
    norm_msg = re.sub(r"[^\w\s\d]", " ", msg_lower).strip()
    tokens = norm_msg.split()
    
    # 1. Check for Wishlist Intent
    if any(k in msg_lower for k in ['my wishlist', 'show my wishlist', 'what is in my wishlist', "what's in my wishlist", 'in my wishlist', 'view wishlist', 'wishlist']) and not any(k in msg_lower for k in ['shirt', 'dress', 'pant', 'shoe', 'kurta', 'under']):
        if not current_user.is_authenticated:
            return jsonify({
                'type': 'login_required',
                'message': "Please log in to view and manage your saved wishlist items.",
                'login_url': url_for('login', next=url_for('wishlist')),
                'action_label': "Log In to Wishlist"
            })
        
        wishlist_items = WishlistItem.query.filter_by(user_id=current_user.id).all()
        if not wishlist_items:
            return jsonify({
                'type': 'text',
                'message': "Your wishlist is currently empty. Click the heart icon on any product to save it here!",
                'quick_replies': ["👕 Men's Wear", "👗 Women's Wear", "👶 Kids Wear", "🔥 Flash Sale"]
            })
        
        prods = []
        for item in wishlist_items:
            p = item.product
            if p and p.is_active:
                eff_price = p.discount_price if p.discount_price else p.price
                prods.append({
                    'id': p.id,
                    'name': p.name,
                    'category': p.category,
                    'price': eff_price,
                    'price_formatted': f"₹{int(eff_price):,}",
                    'original_price_formatted': f"₹{int(p.price):,}" if p.discount_price else None,
                    'image_url': p.image_url,
                    'url': url_for('product_detail', product_id=p.id),
                    'stock': p.stock,
                    'in_stock': (p.stock > 0 if p.stock is not None else True),
                    'in_wishlist': True
                })
        return jsonify({
            'type': 'wishlist',
            'message': f"Here are your {len(prods)} saved wishlist item{'s' if len(prods) != 1 else ''}:",
            'products': prods,
            'view_all_url': url_for('wishlist')
        })

    # 2. Check for Cart Intent
    if any(k in msg_lower for k in ['my cart', 'what is in my cart', "what's in my cart", 'in my cart', 'show my cart', 'view cart', 'shopping bag', 'my bag']) and not any(k in msg_lower for k in ['shirt', 'dress', 'pant', 'shoe', 'kurta', 'under']):
        if current_user.is_authenticated:
            cart_records = CartItem.query.filter_by(user_id=current_user.id).all()
            cart_list = []
            total_price = 0.0
            for item in cart_records:
                p = item.product
                if p:
                    eff_p = p.discount_price if p.discount_price else p.price
                    total_price += eff_p * item.quantity
                    cart_list.append({
                        'id': p.id,
                        'name': p.name,
                        'size': item.size or 'M',
                        'quantity': item.quantity,
                        'price_formatted': f"₹{int(eff_p):,}",
                        'image_url': p.image_url,
                        'url': url_for('product_detail', product_id=p.id)
                    })
        else:
            session_cart = session.get('cart', [])
            cart_list = []
            total_price = 0.0
            for item in session_cart:
                p_id = item.get('id')
                p = Product.query.get(p_id) if p_id else None
                eff_p = float(item.get('price', 0))
                q = int(item.get('quantity', 1))
                total_price += eff_p * q
                cart_list.append({
                    'id': p_id,
                    'name': item.get('name', 'Product'),
                    'size': item.get('size', 'M'),
                    'quantity': q,
                    'price_formatted': f"₹{int(eff_p):,}",
                    'image_url': item.get('image_url', '/static/images/p1.png'),
                    'url': url_for('product_detail', product_id=p_id) if p_id else '#'
                })
        
        if not cart_list:
            return jsonify({
                'type': 'text',
                'message': "Your shopping bag is currently empty. Explore our latest arrivals to add items!",
                'quick_replies': ["👕 Men's Wear", "👗 Women's Wear", "👶 Kids Wear", "🔥 Flash Sale"]
            })
        
        return jsonify({
            'type': 'cart',
            'message': f"You have {len(cart_list)} item{'s' if len(cart_list) != 1 else ''} in your shopping bag (Total: ₹{int(total_price):,}):",
            'cart_items': cart_list,
            'total_price_formatted': f"₹{int(total_price):,}",
            'cart_url': url_for('cart'),
            'checkout_url': url_for('checkout')
        })

    # 3. Check for Orders / Tracking Intent
    if any(k in msg_lower for k in ['track my order', 'track order', 'where is my order', 'my order status', 'order status', 'my orders', 'order history', 'show my orders', 'orders']):
        if not current_user.is_authenticated:
            return jsonify({
                'type': 'login_required',
                'message': "Please log in to track your orders and view purchase history.",
                'login_url': url_for('login', next=url_for('dashboard')),
                'action_label': "Log In to View Orders"
            })
        
        orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_ordered.desc()).limit(5).all()
        if not orders:
            return jsonify({
                'type': 'text',
                'message': "You don't have any orders yet. Once you place an order, you can track it live right here!",
                'quick_replies': ["👕 Men's Wear", "👗 Women's Wear", "👶 Kids Wear", "🔥 Flash Sale"]
            })
        
        orders_data = []
        for o in orders:
            orders_data.append({
                'id': o.id,
                'order_number': f"FW-{o.id}",
                'date': o.date_ordered.strftime('%d %b %Y') if o.date_ordered else '',
                'status': o.status or 'Processing',
                'total_formatted': f"₹{int(o.total_price):,}",
                'items_count': len(o.items) if o.items else 1,
                'track_url': url_for('track_order', order_id=o.id),
                'live_track_url': url_for('live_tracking', order_id=o.id) if (o.status or '').lower() == 'shipped' else None
            })
        
        return jsonify({
            'type': 'orders',
            'message': f"Here are your recent orders:",
            'orders': orders_data,
            'dashboard_url': url_for('dashboard')
        })

    # 4. Check for Size Assistance Intent
    if any(k in msg_lower for k in ['find my size', 'what is my size', "what's my size", 'choose a size', 'recommend size', 'size guide', 'size chart', 'my size', 'which size', 'size recommendation', 'size help', 'measure size']) or (msg_lower == 'size' or msg_lower == 'sizes'):
        return jsonify({
            'type': 'size_finder',
            'message': "I can calculate your recommended size using your height, weight, and fit preference!",
            'quick_replies': ["👕 Men's Wear", "👗 Women's Wear", "👶 Kids Wear"]
        })

    # 5. Check for Returns / Refund Intent
    if any(k in msg_lower for k in ['return', 'returns', 'how to return', 'how do i return', 'refund', 'refunds', 'exchange', 'return policy', 'cancel order']):
        return jsonify({
            'type': 'support',
            'message': "We offer a 30-day return & exchange window on all unworn items with original tags intact. You can view your orders or submit a return ticket directly with our support desk.",
            'support_url': url_for('customer_support'),
            'orders_url': url_for('dashboard') if current_user.is_authenticated else url_for('login'),
            'quick_replies': ["📦 My Orders", "🎧 Contact Support", "🛍️ My Cart"]
        })

    # 6. Check for Customer Support Intent
    if any(k in msg_lower for k in ['support', 'customer care', 'contact support', 'help desk', 'ticket', 'talk to human', 'customer service']):
        return jsonify({
            'type': 'support',
            'message': "Our Customer Support team is ready to assist you. You can create a support ticket or check existing tickets in our Help Center.",
            'support_url': url_for('customer_support'),
            'quick_replies': ["📦 My Orders", "📏 Find My Size", "🛍️ My Cart"]
        })

    # 7. Check for Flash Sale / Specials Intent
    if any(k in msg_lower for k in ['flash sale', 'specials', 'special offers', 'discounts', 'sale', 'deals', 'offers']):
        sale_prods = Product.query.filter(Product.discount_price.isnot(None), Product.is_active.is_(True)).order_by(Product.is_featured.desc(), Product.id.asc()).limit(6).all()
        user_wish_ids = set()
        if current_user.is_authenticated:
            user_wish_ids = {w.product_id for w in WishlistItem.query.filter_by(user_id=current_user.id).all()}
            
        prods_data = []
        for p in sale_prods:
            eff_p = p.discount_price if p.discount_price else p.price
            prods_data.append({
                'id': p.id,
                'name': p.name,
                'category': p.category,
                'price': eff_p,
                'price_formatted': f"₹{int(eff_p):,}",
                'original_price_formatted': f"₹{int(p.price):,}" if p.discount_price else None,
                'image_url': p.image_url,
                'url': url_for('product_detail', product_id=p.id),
                'stock': p.stock,
                'in_stock': (p.stock > 0 if p.stock is not None else True),
                'in_wishlist': p.id in user_wish_ids
            })
            
        return jsonify({
            'type': 'products',
            'message': "🔥 Here are our featured Flash Sale & Exclusive Offers (Up to 40% OFF):",
            'products': prods_data,
            'view_all_url': url_for('specials')
        })

    # 8. Check for Greetings / General Help
    if norm_msg in ['hi', 'hello', 'hey', 'namaste', 'hola', 'good morning', 'good evening', 'good afternoon', 'help', 'start', 'menu']:
        return jsonify({
            'type': 'text',
            'message': "Hello! 👋 Welcome to Fashion World Pro. I'm here to help you discover luxury styles, check cart/wishlist, track orders, and recommend sizes. What are you looking for today?",
            'quick_replies': ["👕 Men's Wear", "👗 Women's Wear", "👶 Kids Wear", "🔥 Flash Sale", "📏 Find My Size", "🛍️ My Cart", "❤️ My Wishlist", "📦 My Orders", "🎧 Contact Support"]
        })

    # 9. Natural Shopping Queries & Database Product Search
    # Extract Price Limit
    max_price = None
    price_match = re.search(r'(?:under|below|less than|within|budget of|budget|upto|up to|<=|<)\s*(?:rs\.?|inr|₹)?\s*(\d+)', msg_lower)
    if not price_match:
        price_match = re.search(r'(?:rs\.?|inr|₹)\s*(\d+)', msg_lower)
        if price_match and any(w in msg_lower for w in ['under', 'below', 'less', 'within', 'budget', 'gift']):
            max_price = float(price_match.group(1))
    else:
        max_price = float(price_match.group(1))

    # Extract Category / Gender Target
    target_category = None
    is_gift = any(w in msg_lower for w in ['gift', 'gifts', 'gifting', 'birthday', 'present'])
    
    if re.search(r'\b(kids?|children|child|boys?|girls?|baby|babies|toddler)\b', msg_lower):
        target_category = 'Kids'
    elif re.search(r'\b(women|womens|women\'s|female|lady|ladies|saree|saris?|kurti|kurtis?|lehenga|anarkali|blouse|gown)\b', msg_lower):
        target_category = 'Women'
    elif re.search(r'\b(men|mens|men\'s|male|gentleman|guy|gents|sherwani|pathani|waistcoat|tuxedo)\b', msg_lower):
        target_category = 'Men'

    # Extract Color
    colors_list = ['black', 'white', 'blue', 'navy', 'red', 'green', 'yellow', 'pink', 'grey', 'gray', 'brown', 'beige', 'gold', 'silver', 'maroon', 'olive', 'purple', 'lavender', 'orange', 'cream', 'charcoal', 'printed', 'striped', 'checked', 'floral']
    target_color = None
    for c in colors_list:
        if re.search(r'\b' + re.escape(c) + r'\b', msg_lower):
            target_color = c
            break

    # Extract Product Keywords
    keyword_patterns = [
        'shirt', 't-shirt', 'tshirt', 'tee', 'polo', 'dress', 'frock', 'jeans', 'pant', 'trouser', 'shorts', 
        'cargo', 'kurta', 'kurti', 'saree', 'lehenga', 'suit', 'blazer', 'jacket', 'coat', 'sweater', 
        'hoodie', 'shoes', 'sneaker', 'sandal', 'loafer', 'watch', 'belt', 'bag', 'clutch', 'scarf', 
        'skirt', 'joggers', 'socks', 'formal', 'casual', 'ethnic', 'party', 'festive', 'western', 'anarkali', 'oxford'
    ]
    target_keywords = []
    for kp in keyword_patterns:
        if re.search(r'\b' + re.escape(kp) + r'\b', msg_lower):
            target_keywords.append(kp)

    # Build Database Query with SQLAlchemy
    query = Product.query.filter(Product.is_active.is_(True))
    
    if target_category:
        query = query.filter(func.lower(Product.category) == target_category.lower())
        
    if max_price is not None:
        query = query.filter(db.case((Product.discount_price.isnot(None), Product.discount_price), else_=Product.price) <= max_price)
        
    if target_color:
        query = query.filter((Product.name.ilike(f'%{target_color}%')) | (Product.description.ilike(f'%{target_color}%')) | (Product.color.ilike(f'%{target_color}%')))
        
    if target_keywords:
        for kw in target_keywords:
            query = query.filter((Product.name.ilike(f'%{kw}%')) | (Product.description.ilike(f'%{kw}%')))
    elif not target_category and not target_color and not max_price:
        # General query words (strip common noise words)
        noise = {'show', 'me', 'find', 'get', 'give', 'i', 'want', 'looking', 'for', 'a', 'an', 'the', 'some', 'please', 'all', 'any'}
        clean_words = [w for w in tokens if w not in noise and len(w) > 2]
        if clean_words:
            for w in clean_words:
                query = query.filter((Product.name.ilike(f'%{w}%')) | (Product.description.ilike(f'%{w}%')))

    results = query.order_by(Product.is_featured.desc(), Product.id.asc()).limit(6).all()

    # If strict combination yielded 0 results, fall back to looser match
    if not results and target_keywords:
        fallback_query = Product.query.filter(Product.is_active.is_(True))
        if target_category:
            fallback_query = fallback_query.filter(func.lower(Product.category) == target_category.lower())
        for kw in target_keywords:
            fallback_query = fallback_query.filter((Product.name.ilike(f'%{kw}%')) | (Product.description.ilike(f'%{kw}%')))
        if max_price:
            fallback_query = fallback_query.filter(db.case((Product.discount_price.isnot(None), Product.discount_price), else_=Product.price) <= max_price)
        results = fallback_query.order_by(Product.is_featured.desc(), Product.id.asc()).limit(6).all()

    if results:
        user_wish_ids = set()
        if current_user.is_authenticated:
            user_wish_ids = {w.product_id for w in WishlistItem.query.filter_by(user_id=current_user.id).all()}
            
        prods_data = []
        for p in results:
            eff_p = p.discount_price if p.discount_price else p.price
            prods_data.append({
                'id': p.id,
                'name': p.name,
                'category': p.category,
                'price': eff_p,
                'price_formatted': f"₹{int(eff_p):,}",
                'original_price_formatted': f"₹{int(p.price):,}" if p.discount_price else None,
                'image_url': p.image_url,
                'url': url_for('product_detail', product_id=p.id),
                'stock': p.stock,
                'in_stock': (p.stock > 0 if p.stock is not None else True),
                'in_wishlist': p.id in user_wish_ids
            })
            
        if is_gift and max_price:
            resp_msg = f"Here are some wonderful gift options within your ₹{int(max_price):,} budget:"
        elif max_price:
            resp_msg = f"I found these matching products under ₹{int(max_price):,}:"
        else:
            resp_msg = "I found these matching products in our collection:"
            
        view_all_cat = target_category if target_category else None
        view_url = url_for('products', category=view_all_cat) if view_all_cat else url_for('products', query=raw_msg)
        
        return jsonify({
            'type': 'products',
            'message': resp_msg,
            'products': prods_data,
            'view_all_url': view_url
        })
    else:
        return jsonify({
            'type': 'text',
            'message': "I'm sorry, I couldn't find matching products right now. Would you like to explore our popular collections?",
            'quick_replies': ["👕 Men's Wear", "👗 Women's Wear", "👶 Kids Wear", "🔥 Flash Sale", "🛍️ My Cart"]
        })

# ==============================================================================
# BUILD MY OUTFIT — CONTROLLERS & TAXONOMY RECOMMENDATION ENGINE
# ==============================================================================
def classify_product_role(product_name):
    """
    Priority-based fashion taxonomy mapping product names to outfit roles:
    1. FOOTWEAR
    2. DRESS / ONE-PIECE / SUIT / SET
    3. TOP / UPPER WEAR
    4. BOTTOM
    5. ACCESSORIES
    """
    import re
    name = (product_name or '').lower()
    
    # 1. FOOTWEAR
    if re.search(r'\b(shoe|shoes|sneaker|sneakers|boot|boots|sandal|sandals|loafer|loafers|sock|socks|flat|flats|heel|heels|slipper|slippers|slide|slides|clog|clogs|mule|mules|footwear|jutti|juttis|mojari|mojaris)\b', name):
        return 'footwear'
        
    # 2. DRESS / ONE-PIECE / SET / SUIT / ETHNIC ENSEMBLE
    if re.search(r'\b(dress|dresses|gown|gowns|frock|frocks|jumpsuit|jumpsuits|romper|rompers|suit|suits|kurta|kurtas|set|sets|outfit|outfits|co-ord|coord|anarkali|anarkalis|saree|sarees|sari|saris|lehenga|lehengas|sherwani|sherwanis|pathani)\b', name):
        return 'set'
        
    # 3. TOP / UPPER WEAR
    if re.search(r'\b(shirt|shirts|t-shirt|tshirt|t-shirts|tshirts|tee|tees|top|tops|blouse|blouses|kurti|kurtis|polo|polos|hoodie|hoodies|sweatshirt|sweatshirts|sweater|sweaters|jacket|jackets|coat|coats|blazer|blazers|cardigan|cardigans|vest|vests|pullover|pullovers|tunic|tunics|tank|tanks|shrug|shrugs|camisole|camisoles|corset|bralette|bodysuit|poncho|cape|overshirt)\b', name):
        return 'top'
        
    # 4. BOTTOM
    if re.search(r'\b(jean|jeans|trouser|trousers|pant|pants|skirt|skirts|shorts|jogger|joggers|legging|leggings|cargo|cargos|chino|chinos|palazzo|palazzos|trackpant|trackpants|capri|capris|bermuda|denim|denims|churidar|churidars|salwar|salwars|pajama|pajamas|pyjama|pyjamas)\b', name):
        return 'bottom'
        
    # 5. ACCESSORIES
    if re.search(r'\b(bag|bags|clutch|clutches|handbag|handbags|tote|totes|backpack|backpacks|watch|watches|sunglass|sunglasses|belt|belts|wallet|wallets|scarf|scarves|mask|masks|hat|hats|cap|caps|headband|headbands|beanie|beanies|gloves|dupatta|shawl|shawls|necklace|necklaces|bracelet|bracelets|earring|earrings|jewelry|jewellery|ring|rings|tie|ties|cufflink|cufflinks|perfume|fragrance|potli|potlis|stole|stoles)\b', name):
        return 'accessory'
        
    return 'other'

def get_product_color_tone(product_name):
    """Extract color hints for harmonious palette matching"""
    name = (product_name or '').lower()
    colors = ['black', 'white', 'grey', 'gray', 'charcoal', 'navy', 'blue', 'denim', 'beige', 'cream', 'sand', 'tan', 'terracotta', 'crimson', 'red', 'green', 'sage', 'olive', 'brown', 'khaki', 'gold', 'silver', 'pink', 'lavender', 'yellow', 'mustard', 'maroon', 'floral', 'check', 'printed']
    for c in colors:
        if c in name:
            return c
    return None

def find_outfit_matches(main_product):
    """
    Returns a list of 3 matching item slots for the given main product using real database inventory.
    Category isolation is strictly maintained, and roles are never misallocated.
    """
    category = main_product.category or 'Men'
    main_role = classify_product_role(main_product.name)
    main_color = get_product_color_tone(main_product.name)
    
    if category == 'Women':
        if main_role == 'top':
            slot_roles = [
                {'slot_name': 'Bottom Wear', 'role': 'bottom', 'icon': 'fa-solid fa-person'},
                {'slot_name': 'Ethnic Footwear', 'role': 'footwear', 'icon': 'fa-solid fa-shoe-prints'},
                {'slot_name': 'Handbag / Accessory', 'role': 'accessory', 'icon': 'fa-solid fa-bag-shopping'}
            ]
        elif main_role == 'set':
            slot_roles = [
                {'slot_name': 'Matching Bottom / Layer', 'role': 'bottom', 'icon': 'fa-solid fa-person'},
                {'slot_name': 'Ethnic Footwear', 'role': 'footwear', 'icon': 'fa-solid fa-shoe-prints'},
                {'slot_name': 'Handbag / Jewellery', 'role': 'accessory', 'icon': 'fa-solid fa-bag-shopping'}
            ]
        elif main_role == 'bottom':
            slot_roles = [
                {'slot_name': 'Top / Upper Wear', 'role': 'top', 'icon': 'fa-solid fa-shirt'},
                {'slot_name': 'Footwear', 'role': 'footwear', 'icon': 'fa-solid fa-shoe-prints'},
                {'slot_name': 'Handbag / Accessory', 'role': 'accessory', 'icon': 'fa-solid fa-bag-shopping'}
            ]
        elif main_role == 'footwear':
            slot_roles = [
                {'slot_name': 'Top / Kurti', 'role': 'top', 'icon': 'fa-solid fa-shirt'},
                {'slot_name': 'Bottom Wear', 'role': 'bottom', 'icon': 'fa-solid fa-person'},
                {'slot_name': 'Handbag / Accessory', 'role': 'accessory', 'icon': 'fa-solid fa-bag-shopping'}
            ]
        else: # accessory or other
            slot_roles = [
                {'slot_name': 'Top / Kurti', 'role': 'top', 'icon': 'fa-solid fa-shirt'},
                {'slot_name': 'Bottom Wear', 'role': 'bottom', 'icon': 'fa-solid fa-person'},
                {'slot_name': 'Footwear', 'role': 'footwear', 'icon': 'fa-solid fa-shoe-prints'}
            ]
    elif category == 'Kids':
        if main_role == 'top':
            slot_roles = [
                {'slot_name': 'Bottom Wear', 'role': 'bottom', 'icon': 'fa-solid fa-person'},
                {'slot_name': 'Layering / Outerwear', 'role': 'top', 'icon': 'fa-solid fa-vest-patches'},
                {'slot_name': 'Matching Set / Accent', 'role': 'set', 'icon': 'fa-solid fa-wand-magic-sparkles'}
            ]
        elif main_role == 'set':
            slot_roles = [
                {'slot_name': 'Layering / Outerwear', 'role': 'top', 'icon': 'fa-solid fa-vest-patches'},
                {'slot_name': 'Bottom Wear', 'role': 'bottom', 'icon': 'fa-solid fa-person'},
                {'slot_name': 'Casual Top / Tee', 'role': 'top', 'icon': 'fa-solid fa-shirt'}
            ]
        else:
            slot_roles = [
                {'slot_name': 'Top / Upper Wear', 'role': 'top', 'icon': 'fa-solid fa-shirt'},
                {'slot_name': 'Bottom Wear', 'role': 'bottom', 'icon': 'fa-solid fa-person'},
                {'slot_name': 'Layering / Outerwear', 'role': 'top', 'icon': 'fa-solid fa-vest-patches'}
            ]
    else: # Men
        if main_role == 'top':
            slot_roles = [
                {'slot_name': 'Bottom Wear', 'role': 'bottom', 'icon': 'fa-solid fa-person'},
                {'slot_name': 'Footwear', 'role': 'footwear', 'icon': 'fa-solid fa-shoe-prints'},
                {'slot_name': 'Accessories', 'role': 'accessory', 'icon': 'fa-solid fa-gem'}
            ]
        elif main_role == 'set':
            slot_roles = [
                {'slot_name': 'Bottom / Pajama', 'role': 'bottom', 'icon': 'fa-solid fa-person'},
                {'slot_name': 'Ethnic Footwear', 'role': 'footwear', 'icon': 'fa-solid fa-shoe-prints'},
                {'slot_name': 'Ethnic Stole / Accessory', 'role': 'accessory', 'icon': 'fa-solid fa-gem'}
            ]
        elif main_role == 'bottom':
            slot_roles = [
                {'slot_name': 'Top / Upper Wear', 'role': 'top', 'icon': 'fa-solid fa-shirt'},
                {'slot_name': 'Footwear', 'role': 'footwear', 'icon': 'fa-solid fa-shoe-prints'},
                {'slot_name': 'Accessories', 'role': 'accessory', 'icon': 'fa-solid fa-gem'}
            ]
        elif main_role == 'footwear':
            slot_roles = [
                {'slot_name': 'Top / Upper Wear', 'role': 'top', 'icon': 'fa-solid fa-shirt'},
                {'slot_name': 'Bottom Wear', 'role': 'bottom', 'icon': 'fa-solid fa-person'},
                {'slot_name': 'Accessories', 'role': 'accessory', 'icon': 'fa-solid fa-gem'}
            ]
        else:
            slot_roles = [
                {'slot_name': 'Top / Upper Wear', 'role': 'top', 'icon': 'fa-solid fa-shirt'},
                {'slot_name': 'Bottom Wear', 'role': 'bottom', 'icon': 'fa-solid fa-person'},
                {'slot_name': 'Footwear', 'role': 'footwear', 'icon': 'fa-solid fa-shoe-prints'}
            ]
    
    category_products = Product.query.filter(
        Product.category == category,
        Product.id != main_product.id,
        Product.is_active.is_(True)
    ).all()
    
    grouped = {'top': [], 'bottom': [], 'footwear': [], 'accessory': [], 'set': [], 'other': []}
    for p in category_products:
        r = classify_product_role(p.name)
        grouped[r].append(p)
    
    matches = []
    used_ids = {main_product.id}
    
    for slot in slot_roles:
        target_role = slot['role']
        # Strictly pick candidates belonging to target_role
        candidates = [p for p in grouped.get(target_role, []) if p.id not in used_ids]
            
        selected = None
        if candidates:
            def score_candidate(cand):
                score = 0
                if cand.stock and cand.stock > 0:
                    score += 10
                c_color = get_product_color_tone(cand.name)
                if c_color in ['black', 'white', 'denim', 'grey', 'gray', 'beige', 'tan']:
                    score += 5
                elif main_color and c_color == main_color:
                    score += 4
                return score
            
            candidates.sort(key=score_candidate, reverse=True)
            selected = candidates[0]
            used_ids.add(selected.id)
            
        matches.append({
            'slot_name': slot['slot_name'],
            'role': slot['role'],
            'icon': slot['icon'],
            'product': {
                'id': selected.id,
                'name': selected.name,
                'price': selected.price,
                'discount_price': selected.discount_price,
                'effective_price': selected.discount_price if selected.discount_price else selected.price,
                'image_url': selected.image_url,
                'stock': selected.stock,
                'category': selected.category,
                'in_stock': (selected.stock > 0 if selected.stock is not None else True)
            } if selected else None
        })
        
    return matches

@app.route('/build-outfit')
def build_outfit():
    category = request.args.get('category', 'Men').strip().capitalize()
    if category not in ['Men', 'Women', 'Kids']:
        category = 'Men'
    
    main_id = request.args.get('main_id', type=int)
    
    # Get initial products for the category
    initial_products = Product.query.filter(
        Product.category == category,
        Product.is_active.is_(True)
    ).limit(36).all()
    
    main_product = None
    if main_id:
        main_product = Product.query.filter_by(id=main_id, is_active=True).first()
    if not main_product and initial_products:
        main_product = initial_products[0]
        
    matching_slots = []
    total_outfit_price = 0.0
    item_count = 0
    if main_product:
        matching_slots = find_outfit_matches(main_product)
        total_outfit_price += (main_product.discount_price if main_product.discount_price else main_product.price)
        item_count += 1
        for match in matching_slots:
            p = match.get('product')
            if p:
                total_outfit_price += (p.get('effective_price') if isinstance(p, dict) else (p.discount_price if p.discount_price else p.price))
                item_count += 1
        
    return render_template(
        'build_outfit.html',
        active_category=category,
        categories=['Men', 'Women', 'Kids'],
        initial_products=initial_products,
        main_product=main_product,
        matching_slots=matching_slots,
        total_outfit_price=total_outfit_price,
        item_count=item_count
    )

@app.route('/api/outfit/products')
def api_outfit_products():
    category = request.args.get('category', 'Men').strip().capitalize()
    role = request.args.get('role', 'all').strip().lower()
    search = request.args.get('search', '').strip().lower()
    exclude_str = request.args.get('exclude', '')
    exclude_ids = set()
    if exclude_str:
        try:
            exclude_ids = {int(x.strip()) for x in exclude_str.split(',') if x.strip()}
        except ValueError:
            pass
            
    query = Product.query.filter(Product.category == category, Product.is_active.is_(True))
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
        
    all_category_products = query.all()
    
    if role and role != 'all':
        matching_products = [p for p in all_category_products if classify_product_role(p.name) == role]
    else:
        matching_products = all_category_products
        
    data = []
    for p in matching_products[:60]:
        if p.id in exclude_ids:
            continue
        data.append({
            'id': p.id,
            'name': p.name,
            'price': p.price,
            'discount_price': p.discount_price,
            'effective_price': p.discount_price if p.discount_price else p.price,
            'image_url': p.image_url,
            'stock': p.stock,
            'category': p.category,
            'role': classify_product_role(p.name),
            'in_stock': (p.stock > 0 if p.stock is not None else True)
        })
        
    return jsonify({'category': category, 'role': role, 'products': data})

@app.route('/api/outfit/match/<int:product_id>')
def api_outfit_match(product_id):
    main_product = Product.query.filter_by(id=product_id, is_active=True).first_or_404()
    matching_slots = find_outfit_matches(main_product)
    
    main_data = {
        'id': main_product.id,
        'name': main_product.name,
        'price': main_product.price,
        'discount_price': main_product.discount_price,
        'effective_price': main_product.discount_price if main_product.discount_price else main_product.price,
        'image_url': main_product.image_url,
        'stock': main_product.stock,
        'category': main_product.category,
        'role': classify_product_role(main_product.name),
        'in_stock': (main_product.stock > 0 if main_product.stock is not None else True)
    }
    
    return jsonify({
        'main_product': main_data,
        'matching_slots': matching_slots
    })

@app.route('/api/outfit/add-to-cart', methods=['POST'])
def api_outfit_add_to_cart():
    payload = request.get_json(silent=True) or {}
    product_ids = payload.get('product_ids', [])
    if not product_ids or not isinstance(product_ids, list):
        return jsonify({'success': False, 'message': 'No products selected.'}), 400
        
    added_products = []
    
    for pid in product_ids:
        try:
            pid_int = int(pid)
        except (ValueError, TypeError):
            continue
            
        prod = Product.query.filter_by(id=pid_int, is_active=True).first()
        if not prod or (prod.stock is not None and prod.stock <= 0):
            continue
            
        if current_user.is_authenticated:
            item = CartItem.query.filter_by(user_id=current_user.id, product_id=prod.id).first()
            if item:
                item.quantity += 1
            else:
                item = CartItem(user_id=current_user.id, product_id=prod.id, quantity=1)
                db.session.add(item)
        else:
            cart = session.get('cart', [])
            found = False
            for c_item in cart:
                if c_item.get('id') == prod.id:
                    c_item['quantity'] = c_item.get('quantity', 1) + 1
                    found = True
                    break
            if not found:
                cart.append({
                    'id': prod.id,
                    'name': prod.name,
                    'price': prod.discount_price if prod.discount_price else prod.price,
                    'image_url': prod.image_url,
                    'quantity': 1
                })
            session['cart'] = cart
            session.modified = True
            
        added_products.append(prod)
        
    if current_user.is_authenticated:
        db.session.commit()
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        count = sum(item.quantity for item in cart_items)
        socketio.emit('cart_updated', {'count': count, 'product_name': 'Full Outfit Look', 'action': 'add'}, room=f"user_{current_user.id}")
    else:
        cart = session.get('cart', [])
        count = sum(item.get('quantity', 1) for item in cart)
        
    return jsonify({
        'success': True,
        'count': count,
        'added_count': len(added_products),
        'message': f"Added {len(added_products)} outfit item{'s' if len(added_products) != 1 else ''} to your bag!"
    })

@app.route('/virtual-tryon')
def virtual_tryon():
    product_id = request.args.get('product_id', type=int)
    selected_product = None
    if product_id:
        selected_product = Product.query.filter_by(id=product_id, is_active=True).first()
    
    rep_ids = get_unique_representative_product_ids()
    # Load catalog products for selection
    available_products = Product.query.filter(Product.is_active.is_(True), Product.id.in_(rep_ids)).order_by(Product.is_featured.desc(), Product.id.asc()).all()
    
    if selected_product:
        # Ensure the selected product is present in available_products list (at the top if needed)
        existing_ids = {p.id for p in available_products}
        if selected_product.id not in existing_ids:
            available_products.insert(0, selected_product)
        else:
            # Move selected product to top for immediate visibility
            available_products = [selected_product] + [p for p in available_products if p.id != selected_product.id]
    
    return render_template(
        'virtual_tryon.html',
        selected_product=selected_product,
        available_products=available_products
    )

# -------------------------------------------------------------
# VIRTUAL TRY-ON SECURE TEMPORARY UPLOAD & INFERENCE (STEP 6)
# -------------------------------------------------------------
TRYON_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'images', 'tryon_uploads')
TRYON_RESULTS_FOLDER = os.path.join(BASE_DIR, 'static', 'images', 'tryon_results')
os.makedirs(TRYON_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRYON_RESULTS_FOLDER, exist_ok=True)
TRYON_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
TRYON_MAX_SIZE = 16 * 1024 * 1024  # 16 MB limit

def validate_image_magic_bytes(header_bytes):
    """Verify magic bytes for PNG, JPEG, and WEBP"""
    if len(header_bytes) < 4:
        return None
    if header_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if header_bytes.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if len(header_bytes) >= 12 and header_bytes.startswith(b'RIFF') and header_bytes[8:12] == b'WEBP':
        return 'webp'
    return None

def cleanup_old_tryon_uploads(max_age_seconds=7200):
    """Safely cleans up stale temporary tryon uploads and results older than 2 hours"""
    try:
        now = time.time()
        for folder in [TRYON_UPLOAD_FOLDER, TRYON_RESULTS_FOLDER]:
            if not os.path.isdir(folder):
                continue
            for fname in os.listdir(folder):
                fpath = os.path.join(folder, fname)
                if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > max_age_seconds:
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
    except Exception:
        pass

def generate_tryon_with_huggingface(customer_photo_path, product_image_path, garment_description="clothing item"):
    """
    Executes Virtual Try-On inference using the free official Hugging Face IDM-VTON Space (yisol/IDM-VTON).
    Returns (result_url, None) on success or (None, error_message) on failure.
    """
    import shutil
    try:
        from gradio_client import Client, handle_file
    except Exception as imp_err:
        print(f"[ERROR] gradio_client import error: {imp_err}")
        return None, "gradio_client package not available"

    try:
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path, override=True)
        hf_token = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN') or os.getenv('HUGGING_FACE_HUB_TOKEN')
        if hf_token:
            hf_token = hf_token.strip()
            os.environ['HF_TOKEN'] = hf_token
            os.environ['HUGGING_FACE_HUB_TOKEN'] = hf_token

        client = Client("yisol/IDM-VTON", token=hf_token) if hf_token else Client("yisol/IDM-VTON")
        result = client.predict(
            dict={
                "background": handle_file(customer_photo_path),
                "layers": [],
                "composite": None
            },
            garm_img=handle_file(product_image_path),
            garment_des=garment_description or "clothing item",
            is_checked=True,
            is_checked_crop=False,
            denoise_steps=30,
            seed=42,
            api_name="/tryon"
        )

        temp_output_path = None
        if isinstance(result, (list, tuple)) and len(result) > 0 and result[0]:
            temp_output_path = result[0]
        elif isinstance(result, str):
            temp_output_path = result

        if not temp_output_path or not os.path.isfile(temp_output_path):
            print(f"[ERROR] Hugging Face IDM-VTON returned empty or invalid output: {result}")
            return None, "IDM-VTON returned empty result"

        ext = os.path.splitext(temp_output_path)[1] or ".png"
        unique_name = f"tryon_result_{secrets.token_hex(12)}{ext}"
        dest_path = os.path.join(TRYON_RESULTS_FOLDER, unique_name)
        shutil.copy2(temp_output_path, dest_path)

        result_url = f"/static/images/tryon_results/{unique_name}"
        return result_url, None

    except Exception as e:
        print(f"[ERROR] Hugging Face IDM-VTON inference error: {type(e).__name__}: {e}")
        return None, str(e)

def generate_tryon_with_replicate(customer_photo_path, product_image_path, garment_description="clothing item"):
    """Legacy Replicate IDM-VTON integration (preserved intact but unused for normal flow)."""
    try:
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path, override=True)
        replicate_token = os.getenv('REPLICATE_API_TOKEN', '').strip()
        if not replicate_token or replicate_token.startswith('YOUR_') or replicate_token == 'r8_your_replicate_api_token_here':
            return None, "Replicate API token is not configured in .env."

        import replicate
        client = replicate.Client(api_token=replicate_token)
        with open(customer_photo_path, 'rb') as human_file, open(product_image_path, 'rb') as garm_file:
            output = client.run(
                "cuuupid/idm-vton:e3893af4fb4bd5741752b35b395348c5f7a9ab5c4776264f5d38e41418081ed7",
                input={
                    "human_img": human_file,
                    "garm_img": garm_file,
                    "garment_des": garment_description,
                    "is_checked": True,
                    "is_checked_crop": False,
                    "denoise_steps": 30,
                    "seed": 42
                }
            )

        result_url = None
        if isinstance(output, list) and len(output) > 0:
            result_url = str(output[0])
        elif hasattr(output, 'url'):
            result_url = str(output.url)
        elif output:
            result_url = str(output)

        if not result_url:
            return None, "Replicate model returned no output image."

        return result_url, None
    except Exception as e:
        print(f"[ERROR] Replicate VTON prediction error: {type(e).__name__}: {e}")
        return None, str(e)

@app.route('/api/virtual-tryon/upload', methods=['POST'])
def api_virtual_tryon_upload():
    """Secure temporary user photo upload endpoint for Virtual Try-On preparation"""
    # 1. Automatic periodic cleanup
    cleanup_old_tryon_uploads()
    
    # 2. Check for uploaded file
    file = None
    for field_key in ['photo', 'image', 'file']:
        if field_key in request.files:
            file = request.files[field_key]
            break
            
    if not file or not file.filename:
        return jsonify({'success': False, 'message': 'No photo file provided in request.'}), 400
        
    orig_name = secure_filename(file.filename)
    if '.' not in orig_name:
        return jsonify({'success': False, 'message': 'Invalid file format. Please upload a JPG, PNG, or WEBP image.'}), 400
        
    ext = orig_name.rsplit('.', 1)[1].lower()
    if ext not in TRYON_ALLOWED_EXTENSIONS:
        return jsonify({'success': False, 'message': f'Unsupported file type (.{ext}). Allowed formats: JPG, JPEG, PNG, WEBP.'}), 400
        
    # 3. Inspect magic bytes for true image content
    header = file.read(16)
    file.seek(0)
    
    detected_type = validate_image_magic_bytes(header)
    if not detected_type:
        return jsonify({'success': False, 'message': 'Invalid or corrupted image content. File header does not match a valid image format.'}), 400
        
    # 4. Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > TRYON_MAX_SIZE:
        return jsonify({'success': False, 'message': f'File exceeds the 16 MB size limit ({file_size / (1024*1024):.1f} MB).'}), 400
    if file_size == 0:
        return jsonify({'success': False, 'message': 'Uploaded file is empty.'}), 400
        
    # 5. Generate secure random upload ID & filename (never trust original filename)
    upload_id = secrets.token_hex(16)
    safe_ext = 'jpg' if detected_type == 'jpg' else detected_type
    secure_name = f"tryon_{upload_id}.{safe_ext}"
    saved_path = os.path.join(TRYON_UPLOAD_FOLDER, secure_name)
    
    file.save(saved_path)
    
    # 6. Store upload session context for subsequent try-on processing
    session['tryon_upload_id'] = upload_id
    session['tryon_upload_filename'] = secure_name
    
    return jsonify({
        'success': True,
        'upload_id': upload_id,
        'message': 'Photo uploaded successfully.'
    })

@app.route('/api/virtual-tryon/generate', methods=['POST'])
def api_virtual_tryon_generate():
    """Executes real Hugging Face IDM-VTON virtual try-on inference"""
    payload = request.get_json(silent=True) or {}
    upload_id = (payload.get('upload_id') or session.get('tryon_upload_id') or '').strip()
    product_id = payload.get('product_id')
    
    if not upload_id:
        return jsonify({'success': False, 'message': 'Missing user photo upload. Please upload your photo first.'}), 400
        
    if not product_id:
        return jsonify({'success': False, 'message': 'No garment selected. Please select a product from the catalog.'}), 400
        
    try:
        product_id = int(product_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid product ID.'}), 400
        
    prod = Product.query.filter_by(id=product_id, is_active=True).first()
    if not prod:
        return jsonify({'success': False, 'message': 'Selected product is not found or is currently inactive.'}), 404
        
    # 1. Resolve customer photo path safely
    customer_photo_path = None
    for ext in ['jpg', 'jpeg', 'png', 'webp']:
        candidate = os.path.join(TRYON_UPLOAD_FOLDER, f"tryon_{upload_id}.{ext}")
        if os.path.isfile(candidate):
            customer_photo_path = candidate
            break
            
    if not customer_photo_path:
        return jsonify({'success': False, 'message': 'Uploaded photo session expired or file not found. Please re-upload your photo.'}), 404
        
    # 2. Resolve product image path safely from disk
    img_rel = prod.image_url.lstrip('/')
    product_image_path = os.path.join(BASE_DIR, img_rel.replace('/', os.sep))
    if not os.path.isfile(product_image_path):
        product_image_path = os.path.join(BASE_DIR, 'static', 'images', os.path.basename(prod.image_url))
        
    if not os.path.isfile(product_image_path):
        return jsonify({'success': False, 'message': 'Product garment image file could not be located on disk.'}), 404
        
    # 3. Call Hugging Face IDM-VTON (Primary & Free Provider)
    result_url, err = generate_tryon_with_huggingface(
        customer_photo_path=customer_photo_path,
        product_image_path=product_image_path,
        garment_description=prod.name
    )
    
    if not result_url:
        return jsonify({
            'success': False,
            'message': 'Virtual try-on is temporarily unavailable. Please try again in a moment.'
        }), 502
        
    # Store result in session
    session['last_tryon_result_url'] = result_url
    session['last_tryon_product_id'] = prod.id
    
    return jsonify({
        'success': True,
        'result_url': result_url,
        'product_id': prod.id,
        'product_name': prod.name,
        'product_price': prod.discount_price if prod.discount_price else prod.price,
        'message': 'Virtual try-on generated successfully.'
    })

@app.route('/')
def home():
    rep_ids = get_unique_representative_product_ids()
    specials = Product.query.filter(Product.discount_price.isnot(None), Product.is_active.is_(True), Product.id.in_(rep_ids)).limit(3).all()
    womens = Product.query.filter(Product.category == "Women", Product.is_active.is_(True), Product.id.in_(rep_ids)).limit(4).all()
    mens = Product.query.filter(Product.category == "Men", Product.is_active.is_(True), Product.id.in_(rep_ids)).limit(4).all()
    mens_under_500 = Product.query.filter(Product.category == "Men", (Product.discount_price < 500) | (Product.price < 500), Product.is_active.is_(True), Product.id.in_(rep_ids)).limit(8).all()
    womens_under_500 = Product.query.filter(Product.category == "Women", (Product.discount_price < 500) | (Product.price < 500), Product.is_active.is_(True), Product.id.in_(rep_ids)).limit(8).all()
    
    # 13 Curated Collections with real counts and real imagery
    collections_list = [
        {
            'key': 'new_arrivals',
            'title': 'New Arrivals',
            'subtitle': 'Fresh drops & latest runway edits',
            'tag': 'JUST DROPPED',
            'count': Product.query.filter((Product.is_new_arrival == True) | (Product.is_featured == True) | (Product.discount_price.isnot(None)), Product.is_active.is_(True), Product.id.in_(rep_ids)).count(),
            'image': '/static/images/ww3.png'
        },
        {
            'key': 'kids',
            'title': 'Kids Wear',
            'subtitle': 'Little Styles, Big Smiles',
            'tag': 'NEW COLLECTION',
            'count': Product.query.filter(func.lower(Product.category) == 'kids', Product.is_active.is_(True), Product.id.in_(rep_ids)).count(),
            'image': '/static/images/products/kids/kids_dress_01.jpg'
        },
        {
            'key': 'trending',
            'title': 'Trending Now',
            'subtitle': 'Most coveted styles of the week',
            'tag': 'TOP TRENDING',
            'count': Product.query.filter((Product.is_featured == True) | (Product.discount_price.isnot(None)), Product.is_active.is_(True), Product.id.in_(rep_ids)).count(),
            'image': '/static/images/hero.png'
        },
        {
            'key': 'men',
            'title': "Men's Collection",
            'subtitle': 'Tailored suiting, knitwear & essentials',
            'tag': 'ESSENTIALS',
            'count': Product.query.filter(func.lower(Product.category) == 'men', Product.is_active.is_(True), Product.id.in_(rep_ids)).count(),
            'image': '/static/images/mw1.png'
        },
        {
            'key': 'women',
            'title': "Women's Collection",
            'subtitle': 'Chic silhouettes, dresses & couture',
            'tag': 'SIGNATURE',
            'count': Product.query.filter(func.lower(Product.category) == 'women', Product.is_active.is_(True), Product.id.in_(rep_ids)).count(),
            'image': '/static/images/ww1.png'
        },
        {
            'key': 'ethnic',
            'title': 'Ethnic Edit',
            'subtitle': 'Boho maxi dresses, rich silks & scarves',
            'tag': 'HERITAGE',
            'count': Product.query.filter((Product.name.ilike('%Scarf%')) | (Product.name.ilike('%Boho%')) | (Product.name.ilike('%Dress%')) | (Product.name.ilike('%Kurta%')), Product.is_active.is_(True), Product.id.in_(rep_ids)).count(),
            'image': '/static/images/ww2.png'
        },
        {
            'key': 'western',
            'title': 'Western Wear',
            'subtitle': 'Denims, biker jackets & smart blazers',
            'tag': 'MODERN',
            'count': Product.query.filter((Product.name.ilike('%Jeans%')) | (Product.name.ilike('%Jacket%')) | (Product.name.ilike('%Cardigan%')) | (Product.name.ilike('%Chinos%')), Product.is_active.is_(True), Product.id.in_(rep_ids)).count(),
            'image': '/static/images/p3.jpg'
        },
        {
            'key': 'party_occasion',
            'title': 'Party & Occasion',
            'subtitle': 'Evening wear, luxury silks & clutch bags',
            'tag': 'GLAMOUR',
            'count': Product.query.filter((Product.name.ilike('%Clutch%')) | (Product.name.ilike('%Silk%')) | (Product.name.ilike('%Maxi%')) | (Product.name.ilike('%Suit%')) | (Product.name.ilike('%Party%')), Product.is_active.is_(True), Product.id.in_(rep_ids)).count(),
            'image': '/static/images/p1.jpg'
        },
        {
            'key': 'casual_everyday',
            'title': 'Casual Everyday',
            'subtitle': 'Breathable cotton shirts, tees & chinos',
            'tag': 'COMFORT',
            'count': Product.query.filter((Product.name.ilike('%Shirt%')) | (Product.name.ilike('%Tee%')) | (Product.name.ilike('%Polos%')) | (Product.name.ilike('%Chinos%')) | (Product.name.ilike('%Sweatshirt%')) | (Product.name.ilike('%Shorts%')), Product.is_active.is_(True), Product.id.in_(rep_ids)).count(),
            'image': '/static/images/mw2.png'
        },
        {
            'key': 'footwear',
            'title': 'Footwear Edit',
            'subtitle': 'Bamboo socks, footwear & comfort pairs',
            'tag': 'LIFESTYLE',
            'count': Product.query.filter((Product.name.ilike('%Socks%')) | (Product.name.ilike('%Joggers%')) | (Product.name.ilike('%Shoes%')), Product.is_active.is_(True), Product.id.in_(rep_ids)).count(),
            'image': '/static/images/m2.png'
        },
        {
            'key': 'accessories',
            'title': 'Accessories',
            'subtitle': 'Bags, web belts, silk wraps & essentials',
            'tag': 'ACCENTS',
            'count': Product.query.filter((Product.name.ilike('%Belt%')) | (Product.name.ilike('%Clutch%')) | (Product.name.ilike('%Scarf%')) | (Product.name.ilike('%Mask%')) | (Product.name.ilike('%Headband%')), Product.is_active.is_(True), Product.id.in_(rep_ids)).count(),
            'image': '/static/images/p2.jpg'
        },
        {
            'key': 'beauty_selfcare',
            'title': 'Beauty & Self Care',
            'subtitle': 'Organic wellness headbands & eco care',
            'tag': 'WELLNESS',
            'count': Product.query.filter((Product.name.ilike('%Headband%')) | (Product.name.ilike('%Mask%')) | (Product.name.ilike('%Silk%')), Product.is_active.is_(True), Product.id.in_(rep_ids)).count(),
            'image': '/static/images/m4.png'
        },
        {
            'key': 'festive',
            'title': 'Festive Collection',
            'subtitle': 'Celebratory elegance, fine sets & robes',
            'tag': 'CELEBRATION',
            'count': Product.query.filter((Product.name.ilike('%Silk%')) | (Product.name.ilike('%Maxi%')) | (Product.name.ilike('%Suit%')) | (Product.name.ilike('%Scarf%')) | (Product.name.ilike('%Kurta%')), Product.is_active.is_(True), Product.id.in_(rep_ids)).count(),
            'image': '/static/images/mw3.png'
        }
    ]
    
    return render_template('index.html', specials=specials, womens=womens, mens=mens, mens_under_500=mens_under_500, womens_under_500=womens_under_500, collections_list=collections_list)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    in_wishlist = False
    if current_user.is_authenticated:
        in_wishlist = WishlistItem.query.filter_by(user_id=current_user.id, product_id=product.id).first() is not None
    return render_template('product_detail.html', product=product, in_wishlist=in_wishlist)

# -------------------------------
# AUTHENTICATION ROUTES
# -------------------------------

def get_google_redirect_uri():
    configured_uri = os.getenv('GOOGLE_REDIRECT_URI', '').strip()
    if configured_uri:
        return configured_uri
    return url_for('auth_google_callback', _external=True)

@app.route('/auth/google')
def auth_google():
    """Initiates server-side Google Cloud OAuth 2.0 flow"""
    client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
    
    if not client_id or not client_secret:
        flash("Google Sign-In is not configured yet. Please enter your GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in the .env file.", "warning")
        return redirect(url_for('login'))
        
    redirect_uri = get_google_redirect_uri()
    print(f"[GOOGLE DEBUG] Step 2: /auth/google initiated with redirect_uri = {redirect_uri}")
    try:
        return google.authorize_redirect(redirect_uri, prompt='select_account')
    except Exception as e:
        print(f"[GOOGLE DEBUG] Authlib authorize_redirect exception: {e}. Using direct OAuth URL...")
        import urllib.parse
        state = secrets.token_urlsafe(16)
        session['_google_authlib_state_'] = state
        params = {
            'client_id': client_id,
            'response_type': 'code',
            'scope': 'openid email profile',
            'redirect_uri': redirect_uri,
            'state': state,
            'access_type': 'online',
            'prompt': 'select_account'
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        return redirect(auth_url)

@app.route('/auth/google/callback', endpoint='auth_google_callback')
@app.route('/login/google/callback', endpoint='login_google_callback')
def auth_google_callback():
    """Handles Google OAuth 2.0 callback, extracts user identity, creates/links local customer"""
    print("\n[GOOGLE DEBUG] ========================================")
    print("[GOOGLE DEBUG] Step 5: /auth/google/callback reached")
    
    # 1. Check for error returned by Google
    google_error = request.args.get('error')
    if google_error:
        error_desc = request.args.get('error_description', 'No details provided')
        print(f"[GOOGLE DEBUG] Google returned error: {google_error} - {error_desc}")
        flash(f"Google Sign-In was cancelled or denied: {google_error}", "info")
        return redirect(url_for('login'))

    # 2. Check authorization response parameters
    code = request.args.get('code')
    state = request.args.get('state')
    print(f"[GOOGLE DEBUG] Authorization response: code received = {bool(code)}, state received = {bool(state)}")
    
    if not code:
        print("[GOOGLE DEBUG] ERROR: No authorization code received in callback request.")
        flash("Authorization failed (no code received from Google).", "danger")
        return redirect(url_for('login'))

    token = None
    user_info = None

    # 3. Exchange authorization code for tokens (Dual-layer: Authlib + Direct Google Token Fallback)
    claims_opts = {'iat': {'leeway': 120}, 'exp': {'leeway': 120}, 'nbf': {'leeway': 120}}
    try:
        print("[GOOGLE DEBUG] Step 6: Exchanging authorization code for tokens via Authlib...", flush=True)
        try:
            token = google.authorize_access_token(claims_options=claims_opts)
        except TypeError:
            token = google.authorize_access_token()
        print("[GOOGLE DEBUG] Step 6: Authlib token exchange completed.", flush=True)
    except Exception as authlib_err:
        print(f"[GOOGLE DEBUG] Authlib exchange note ({type(authlib_err).__name__}): {authlib_err}", flush=True)
        print("[GOOGLE DEBUG] Attempting direct server-side token exchange with Google OAuth endpoint...", flush=True)
        try:
            import requests as req
            redirect_uri = get_google_redirect_uri()
            token_resp = req.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'client_id': os.getenv('GOOGLE_CLIENT_ID', '').strip(),
                    'client_secret': os.getenv('GOOGLE_CLIENT_SECRET', '').strip(),
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': redirect_uri
                },
                headers={'Accept': 'application/json'},
                timeout=10
            )
            if token_resp.ok:
                token = token_resp.json()
                print("[GOOGLE DEBUG] Step 6: Direct server-side token exchange successful.", flush=True)
            else:
                print(f"[GOOGLE DEBUG] Direct token exchange response: {token_resp.status_code} - {token_resp.text}", flush=True)
        except Exception as direct_err:
            print(f"[GOOGLE DEBUG] Direct token exchange exception: {direct_err}", flush=True)

    if not token:
        print("[GOOGLE DEBUG] ERROR: No token received from Google.", flush=True)
        flash("Failed to authenticate with Google (no token received).", "danger")
        return redirect(url_for('login'))

    # 4. Reliable Google Profile Retrieval
    # Strategy A: Query Google's official UserInfo endpoint using access_token
    access_token = token.get('access_token')
    if access_token:
        try:
            import requests as req
            resp = req.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            if resp.ok:
                user_info = resp.json()
                print(f"[GOOGLE DEBUG] Step 7: Google user profile retrieved via UserInfo endpoint.", flush=True)
            else:
                print(f"[GOOGLE DEBUG] Userinfo endpoint returned status: {resp.status_code} - {resp.text}", flush=True)
        except Exception as uinfo_err:
            print(f"[GOOGLE DEBUG] Userinfo endpoint exception: {uinfo_err}", flush=True)

    # Strategy B: Cryptographically verify ID token with Google's public certs (120s clock skew)
    if not user_info and token.get('id_token'):
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests
            client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
            verified_claims = google_id_token.verify_oauth2_token(
                token['id_token'],
                google_requests.Request(),
                client_id,
                clock_skew_in_seconds=120
            )
            if verified_claims and verified_claims.get('sub'):
                user_info = verified_claims
                print("[GOOGLE DEBUG] Step 7: Google user profile retrieved via verified ID-token claims.", flush=True)
        except Exception as id_tok_err:
            print(f"[GOOGLE DEBUG] ID-token verification exception: {id_tok_err}", flush=True)

    # Strategy C: Authlib parse_id_token fallback (120s clock skew)
    if not user_info and token.get('id_token'):
        try:
            try:
                user_info = google.parse_id_token(token, claims_options=claims_opts)
            except TypeError:
                user_info = google.parse_id_token(token)
            if user_info:
                print("[GOOGLE DEBUG] Step 7: Google user profile retrieved via Authlib parse_id_token.", flush=True)
        except Exception as e:
            print(f"[GOOGLE DEBUG] Authlib parse_id_token note: {e}", flush=True)

    if not user_info:
        print("[GOOGLE DEBUG] ERROR: Failed to retrieve user profile from Google.", flush=True)
        flash("Failed to retrieve user profile from Google.", "danger")
        return redirect(url_for('login'))
        
    google_id = str(user_info.get('sub') or user_info.get('id') or '')
    email = (user_info.get('email') or '').strip().lower()
    name = user_info.get('name') or user_info.get('given_name') or (email.split('@')[0] if email else 'Customer')
    given_name = user_info.get('given_name') or (name.split()[0] if name else '')
    family_name = user_info.get('family_name') or (' '.join(name.split()[1:]) if len(name.split()) > 1 else '')
    
    print(f"[GOOGLE DEBUG] Step 7: Google profile received: Email Present = {bool(email)}, Google ID Present = {bool(google_id)}")
    
    if not email or not google_id:
        print("[GOOGLE DEBUG] ERROR: Google account did not return a valid email or ID.")
        flash("Google account did not return a valid email address.", "danger")
        return redirect(url_for('login'))
        
    # 5. Database lookup & User linking/creation
    print("[GOOGLE DEBUG] Step 8: Database lookup started...")
    # A. Match by google_id
    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        # B. Match by email to link existing local account
        user = User.query.filter(db.func.lower(User.email) == email).first()
        if user:
            print(f"[GOOGLE DEBUG] Existing local user matched by email (ID: {user.id}). Linking Google ID...")
            user.google_id = google_id
            if not user.auth_provider:
                user.auth_provider = 'google'
            db.session.commit()
            print(f"[GOOGLE DEBUG] Step 8: User ID {user.id} successfully linked with Google ID.")
        else:
            # C. Create new customer account
            print("[GOOGLE DEBUG] Creating new customer account for Google user...")
            clean_name = ''.join(c for c in name if c.isalnum() or c == '_').lower()
            base_username = clean_name if clean_name else "user"
            username = base_username
            count = 1
            while User.query.filter(db.func.lower(User.username) == username.lower()).first():
                username = f"{base_username}_{count}"
                count += 1
                
            random_pwd = generate_password_hash(secrets.token_hex(32), method='pbkdf2:sha256')
            
            user = User(
                username=username,
                email=email,
                password=random_pwd,
                is_admin=False, # Google users are customers
                google_id=google_id,
                auth_provider='google',
                first_name=given_name,
                last_name=family_name
            )
            db.session.add(user)
            db.session.commit()
            print(f"[GOOGLE DEBUG] Step 8: New customer account created: ID = {user.id}, Username = {user.username}")
    else:
        print(f"[GOOGLE DEBUG] Step 8: Existing Google user found in DB: ID = {user.id}, Username = {user.username}")
            
    # 6. Authenticate session with Flask-Login
    print(f"[GOOGLE DEBUG] Step 9: Authenticating user ID {user.id} with Flask-Login...")
    login_user(user, remember=True)
    session.permanent = True
    print(f"[GOOGLE DEBUG] Step 9: Flask-Login successful: is_authenticated = {current_user.is_authenticated}")
    flash(f"Welcome back, {user.username}! Successfully logged in with Google.", "success")
    
    next_page = session.pop('next_url', None) or request.args.get('next')
    if next_page and next_page.startswith('/'):
        print(f"[GOOGLE DEBUG] Step 10: Redirecting to next_page: {next_page}")
        return redirect(next_page)
        
    print("[GOOGLE DEBUG] Step 10: Redirecting to /dashboard")
    print("[GOOGLE DEBUG] ========================================\n")
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Customer Login (Email/Username + Password, Phone OTP, or Google)"""
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter(
            (db.func.lower(User.email) == identifier) |
            (db.func.lower(User.username) == identifier)
        ).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check your email and password.', 'danger')
            
    return render_template('login.html', firebase_config=FIREBASE_CONFIG)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Customer Registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')
            
        if confirm_password and password != confirm_password:
            flash('Passwords do not match. Please verify.', 'danger')
            return render_template('register.html')
            
        user_by_email = User.query.filter(db.func.lower(User.email) == email).first()
        user_by_username = User.query.filter(db.func.lower(User.username) == username.lower()).first()
        
        if user_by_email:
            flash(f'The email "{email}" is already registered. Please login.', 'danger')
            return redirect(url_for('login'))
        
        if user_by_username:
            flash(f'The username "{username}" is already taken. Please choose another.', 'danger')
            return render_template('register.html')

        try:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            is_admin = False
            if not User.query.first(): # First user is admin
                is_admin = True
            new_user = User(username=username, email=email, password=hashed_password, is_admin=is_admin, auth_provider='local')
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash('Your account has been created! Welcome to Fashion World Pro.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please check your details and try again.', 'danger')
            print(f"DEBUG: Registration Integrity Error: {e}")
            return render_template('register.html')
            
    return render_template('register.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    """Administrator Login (Restricted to Email/Username + Password)"""
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter(
            (db.func.lower(User.email) == identifier) |
            (db.func.lower(User.username) == identifier)
        ).first()
        
        if user and check_password_hash(user.password, password):
            if not user.is_admin:
                flash('Access Denied: This portal is restricted to Administrators only.', 'danger')
                return render_template('admin_login.html')
                
            logout_user()
            login_user(user, remember=remember)
            session.pop('_flashes', None)
            flash('Welcome to the Admin Command Center.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Login Unsuccessful. Please check your email and password.', 'danger')
            
    return render_template('admin_login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Password reset handler with Google account detection"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash('Please enter your email address.', 'warning')
            return redirect(url_for('login'))
            
        user = User.query.filter(db.func.lower(User.email) == email).first()
        if not user:
            flash('If an account exists with that email, password reset instructions will be sent.', 'info')
            return redirect(url_for('login'))
            
        if user.auth_provider == 'google' or (user.google_id and not user.password):
            flash('This account uses Google Sign-In. Please continue with Google.', 'info')
            return redirect(url_for('login'))
            
        flash('Password reset instructions have been sent to your email address.', 'success')
        return redirect(url_for('login'))
        
    return redirect(url_for('login'))

@app.route('/auth/email_otp/send', methods=['POST'])
def auth_email_otp_send():
    """Generates and sends a secure 6-digit OTP to the user's email via Gmail SMTP"""
    import re
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    
    # 1. Validate email format
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not email or not re.match(email_regex, email):
        return jsonify({'success': False, 'message': 'Please enter a valid email address.'}), 400
        
    # 2. Check 60-second resend cooldown
    last_sent = session.get('email_otp_last_sent')
    now_ts = datetime.utcnow().timestamp()
    if last_sent and (now_ts - last_sent) < 60:
        remaining = int(60 - (now_ts - last_sent))
        return jsonify({'success': False, 'message': f'Please wait {remaining} seconds before requesting another code.'}), 429

    # 3. Dynamic SMTP configuration reload from .env
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path, override=True)
        
    mail_user = os.getenv('MAIL_USERNAME', '').strip()
    mail_pwd = os.getenv('MAIL_PASSWORD', '').strip()
    
    app.config['MAIL_USERNAME'] = mail_user
    app.config['MAIL_PASSWORD'] = mail_pwd
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com').strip()
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() in ('true', '1', 't', 'yes')
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'false').lower() in ('true', '1', 't', 'yes')
    mail_sender = os.getenv('MAIL_DEFAULT_SENDER', '').strip() or mail_user
    app.config['MAIL_DEFAULT_SENDER'] = mail_sender if ('@' in mail_sender and '<' in mail_sender) else f"Fashion World Pro <{mail_sender}>" if mail_sender else "Fashion World Pro"

    # Refresh Flask-Mail instance attributes so AUTH LOGIN is executed
    mail.server = app.config['MAIL_SERVER']
    mail.port = app.config['MAIL_PORT']
    mail.use_tls = app.config['MAIL_USE_TLS']
    mail.use_ssl = app.config['MAIL_USE_SSL']
    mail.username = mail_user
    mail.password = mail_pwd
    mail.default_sender = app.config['MAIL_DEFAULT_SENDER']

    if not mail_user or not mail_pwd:
        return jsonify({
            'success': False, 
            'message': 'Gmail SMTP is not configured yet. Please enter MAIL_USERNAME and MAIL_PASSWORD in your .env file.'
        }), 503

    # 4. Generate cryptographically secure 6-digit OTP (100000 - 999999)
    otp_code = str(secrets.randbelow(900000) + 100000)
    
    # 5. Store hashed OTP and metadata in session (never in plain text)
    session['email_otp_hash'] = generate_password_hash(otp_code, method='pbkdf2:sha256')
    session['email_otp_target'] = email
    session['email_otp_expires_at'] = (datetime.utcnow() + timedelta(minutes=5)).timestamp()
    session['email_otp_attempts'] = 0
    session['email_otp_last_sent'] = now_ts
    
    # 6. Compose and dispatch email via Flask-Mail
    sender = app.config.get('MAIL_DEFAULT_SENDER') or mail_user
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fashion World Pro - Verification Code</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed; background-color: #0b0f19; padding: 40px 0;">
            <tr>
                <td align="center">
                    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 520px; background-color: #111827; border: 1px solid #1f2937; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
                        <tr>
                            <td align="center" style="padding: 36px 24px 20px; border-bottom: 1px solid #1f2937; background: linear-gradient(180deg, rgba(217,119,6,0.1) 0%, rgba(17,24,39,0) 100%);">
                                <h1 style="margin: 0; color: #f59e0b; font-size: 26px; font-weight: 800; letter-spacing: 1px; text-transform: uppercase;">Fashion World Pro</h1>
                                <p style="margin: 6px 0 0; color: #9ca3af; font-size: 13px; font-weight: 500; letter-spacing: 0.5px;">Customer Secure Login</p>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 36px 32px 28px; text-align: center;">
                                <p style="margin: 0 0 20px; color: #e5e7eb; font-size: 16px; line-height: 24px;">
                                    Use the verification code below to sign in to your Fashion World Pro account:
                                </p>
                                
                                <div style="display: inline-block; background-color: #030712; border: 2px solid #d97706; border-radius: 12px; padding: 18px 36px; margin: 10px 0 24px;">
                                    <span style="font-family: 'Courier New', Courier, monospace; font-size: 36px; font-weight: 800; letter-spacing: 10px; color: #fbbf24; display: block; margin-left: 10px;">{otp_code}</span>
                                </div>
                                
                                <p style="margin: 0 0 8px; color: #9ca3af; font-size: 14px; line-height: 20px;">
                                    This single-use code is valid for <strong style="color: #f3f4f6;">5 minutes</strong>.
                                </p>
                                <p style="margin: 0; color: #ef4444; font-size: 13px; font-weight: 500;">
                                    Never share this code with anyone. Our team will never ask for your code.
                                </p>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 20px 32px; background-color: #030712; border-top: 1px solid #1f2937; text-align: center;">
                                <p style="margin: 0 0 6px; color: #6b7280; font-size: 12px;">
                                    If you did not request this login code, you can safely ignore this email.
                                </p>
                                <p style="margin: 0; color: #4b5563; font-size: 11px;">
                                    &copy; {datetime.utcnow().year} Fashion World Pro. All rights reserved.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    text_body = f"""Fashion World Pro - Verification Code

Your single-use login code is: {otp_code}

This code is valid for 5 minutes. Do not share this code with anyone.

If you did not request this code, please ignore this email.

(c) {datetime.utcnow().year} Fashion World Pro.
"""

    try:
        msg = Message(
            subject=f"Your Fashion World Pro Login Code: {otp_code}",
            recipients=[email],
            body=text_body,
            html=html_body,
            sender=sender
        )
        mail.send(msg)
        return jsonify({'success': True, 'message': 'Verification code sent to your email.'}), 200
    except Exception as mail_err:
        print(f"[EMAIL OTP] SMTP send error: {mail_err}")
        return jsonify({
            'success': False, 
            'message': 'Failed to send email via Gmail SMTP. Please check your Gmail address and App Password in .env.'
        }), 500


@app.route('/auth/email_otp/verify', methods=['POST'])
def auth_email_otp_verify():
    """Validates the 6-digit OTP, establishes customer session, and redirects to dashboard"""
    import re
    data = request.get_json() or {}
    stored_hash = session.get('email_otp_hash')
    stored_target = session.get('email_otp_target')
    expires_at = session.get('email_otp_expires_at')
    
    if not stored_hash or not stored_target or not expires_at:
        return jsonify({'success': False, 'message': 'No active verification session found. Please request a new code.'}), 400
        
    email = (data.get('email') or stored_target).strip().lower()
    otp = data.get('otp', '').strip()
    
    if not otp:
        return jsonify({'success': False, 'message': 'Verification code is required.'}), 400
        
    if email != stored_target:
        return jsonify({'success': False, 'message': 'Email mismatch. Please request a new code for this email.'}), 400
        
    # Check expiration (5 minutes)
    if datetime.utcnow().timestamp() > expires_at:
        session.pop('email_otp_hash', None)
        session.pop('email_otp_target', None)
        session.pop('email_otp_expires_at', None)
        return jsonify({'success': False, 'message': 'This verification code has expired. Please request a new code.'}), 400
        
    # Check attempt limit (max 5)
    attempts = session.get('email_otp_attempts', 0) + 1
    session['email_otp_attempts'] = attempts
    
    if attempts > 5:
        session.pop('email_otp_hash', None)
        session.pop('email_otp_target', None)
        session.pop('email_otp_expires_at', None)
        return jsonify({'success': False, 'message': 'Maximum verification attempts exceeded. Please request a new code.'}), 429
        
    if not check_password_hash(stored_hash, otp):
        remaining = 5 - attempts
        if remaining > 0:
            return jsonify({'success': False, 'message': f'Incorrect verification code. {remaining} attempt(s) remaining.'}), 400
        else:
            session.pop('email_otp_hash', None)
            session.pop('email_otp_target', None)
            session.pop('email_otp_expires_at', None)
            return jsonify({'success': False, 'message': 'Maximum attempts exceeded. Please request a new code.'}), 429

    # OTP Verified Successfully -> Clear session OTP keys
    session.pop('email_otp_hash', None)
    session.pop('email_otp_target', None)
    session.pop('email_otp_expires_at', None)
    session.pop('email_otp_attempts', None)
    
    # Lookup or create customer User (strictly Customer: is_admin = False)
    user = User.query.filter(db.func.lower(User.email) == email).first()
    
    if not user:
        clean_prefix = re.sub(r'[^a-zA-Z0-9_]', '', email.split('@')[0])
        base_username = clean_prefix if clean_prefix else "shopper"
        username = base_username
        count = 1
        while User.query.filter(db.func.lower(User.username) == username.lower()).first():
            username = f"{base_username}_{count}"
            count += 1
            
        random_pwd = generate_password_hash(secrets.token_hex(24), method='pbkdf2:sha256')
        
        user = User(
            username=username,
            email=email,
            password=random_pwd,
            auth_provider='email_otp',
            is_admin=False # Strictly Customer
        )
        db.session.add(user)
        db.session.commit()
    else:
        if not user.auth_provider:
            user.auth_provider = 'email_otp'
            db.session.commit()
            
    # Authenticate session
    login_user(user, remember=True)
    flash(f"Welcome back, {user.username}!", "success")
    
    next_page = session.pop('next_url', None) or request.args.get('next')
    if next_page and next_page.startswith('/'):
        return jsonify({'success': True, 'redirect': next_page})
        
    return jsonify({'success': True, 'redirect': url_for('dashboard')})

@app.route('/auth/phone_login', methods=['POST'])
def auth_phone_login():
    """Securely handles phone login by verifying Firebase ID token"""
    data = request.get_json() or {}
    id_token = data.get('id_token', '').strip()
    
    if not id_token:
        return jsonify({'success': False, 'message': 'Firebase ID token is required.'}), 400
        
    uid = None
    phone_number = None
    
    # 1. Verify ID token via Firebase Admin SDK / Google OAuth JWKS
    try:
        import firebase_admin
        from firebase_admin import auth as fb_auth
        
        if not firebase_admin._apps:
            firebase_admin.initialize_app(options={'projectId': FIREBASE_PROJECT_ID})
            
        decoded_token = fb_auth.verify_id_token(id_token)
        uid = decoded_token.get('uid')
        phone_number = decoded_token.get('phone_number')
    except Exception as admin_err:
        print(f"[PHONE AUTH] Firebase Admin token verification note: {admin_err}")
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests
            
            decoded_token = google_id_token.verify_firebase_token(
                id_token, 
                google_requests.Request(), 
                audience=FIREBASE_PROJECT_ID
            )
            uid = decoded_token.get('user_id') or decoded_token.get('sub')
            phone_number = decoded_token.get('phone_number')
        except Exception as fallback_err:
            print(f"[PHONE AUTH] Google public JWKS token verification error: {fallback_err}")
            return jsonify({'success': False, 'message': 'Security verification failed: Invalid Firebase authentication token.'}), 401
            
    if not phone_number:
        return jsonify({'success': False, 'message': 'Verified token did not contain a valid phone number.'}), 400
        
    # 2. Database lookup & User creation (Phone OTP users are strictly Customers: is_admin = False)
    user = User.query.filter_by(phone=phone_number).first()
    if not user and uid:
        user = User.query.filter_by(firebase_uid=uid).first()
        
    if not user:
        clean_phone = ''.join(c for c in phone_number if c.isdigit())
        base_username = f"user_{clean_phone[-6:] if len(clean_phone) >= 6 else clean_phone}"
        username = base_username
        count = 1
        while User.query.filter(db.func.lower(User.username) == username.lower()).first():
            username = f"{base_username}_{count}"
            count += 1
            
        random_pwd = generate_password_hash(secrets.token_hex(24), method='pbkdf2:sha256')
        email = f"phone_{clean_phone}@fashionworld.pro"
        
        user = User(
            username=username,
            email=email,
            password=random_pwd,
            phone=phone_number,
            firebase_uid=uid,
            auth_provider='phone',
            is_admin=False # Strictly Customer
        )
        db.session.add(user)
        db.session.commit()
    else:
        if uid and not user.firebase_uid:
            user.firebase_uid = uid
            db.session.commit()
            
    # 3. Authenticate session with Flask-Login
    login_user(user, remember=True)
    flash(f"Welcome back, {user.username}!", "success")
    
    next_page = session.pop('next_url', None) or request.args.get('next')
    if next_page and next_page.startswith('/'):
        return jsonify({'success': True, 'redirect': next_page})
        
    return jsonify({'success': True, 'redirect': url_for('dashboard')})

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    was_admin = current_user.is_authenticated and getattr(current_user, 'is_admin', False)
    logout_user()
    for key in list(session.keys()):
        if key not in ['_flashes']:
            session.pop(key, None)
    session.clear()
    flash("You have been logged out.", "info")
    target = url_for('admin_login') if was_admin else url_for('login')
    response = make_response(redirect(target))
    cookie_name = app.config.get("REMEMBER_COOKIE_NAME", "remember_token")
    domain = app.config.get("REMEMBER_COOKIE_DOMAIN")
    path = app.config.get("REMEMBER_COOKIE_PATH", "/")
    response.delete_cookie(cookie_name, domain=domain, path=path)
    response.delete_cookie("remember_token", domain=domain, path=path)
    session_cookie_name = app.config.get("SESSION_COOKIE_NAME", "session")
    response.delete_cookie(session_cookie_name, domain=domain, path=path)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/admin/logout', methods=['GET', 'POST'])
def admin_logout():
    logout_user()
    for key in list(session.keys()):
        if key not in ['_flashes']:
            session.pop(key, None)
    session.clear()
    flash("You have been logged out.", "info")
    response = make_response(redirect(url_for('admin_login')))
    cookie_name = app.config.get("REMEMBER_COOKIE_NAME", "remember_token")
    domain = app.config.get("REMEMBER_COOKIE_DOMAIN")
    path = app.config.get("REMEMBER_COOKIE_PATH", "/")
    response.delete_cookie(cookie_name, domain=domain, path=path)
    response.delete_cookie("remember_token", domain=domain, path=path)
    session_cookie_name = app.config.get("SESSION_COOKIE_NAME", "session")
    response.delete_cookie(session_cookie_name, domain=domain, path=path)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/cart')
def cart():
    if current_user.is_authenticated:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        total = sum((item.product.discount_price if item.product.discount_price else item.product.price) * item.quantity for item in cart_items)
        return render_template('cart.html', items=cart_items, total=total, db_cart=True)
    else:
        cart_session = session.get('cart', [])
        total = sum(item['price'] for item in cart_session)
        return render_template('cart.html', items=cart_session, total=total, db_cart=False)

@app.route('/add_to_cart/<int:product_id>', methods=['GET', 'POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    size = request.args.get('size') or request.form.get('size') or ''
    if request.is_json:
        data = request.get_json(silent=True) or {}
        if 'size' in data:
            size = data['size']
    size = str(size).strip() if size else None
    
    if current_user.is_authenticated:
        if size:
            item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id, size=size).first()
        else:
            item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
            
        if item:
            item.quantity += 1
        else:
            item = CartItem(user_id=current_user.id, product_id=product_id, size=size)
            db.session.add(item)
        db.session.commit()
    else:
        cart = session.get('cart', [])
        found = False
        for item in cart:
            if item.get('id') == product.id and item.get('size') == size:
                item['quantity'] = item.get('quantity', 1) + 1
                found = True
                break
        if not found:
            cart.append({
                'id': product.id,
                'name': product.name,
                'price': product.discount_price if product.discount_price else product.price,
                'image_url': product.image_url,
                'size': size,
                'quantity': 1
            })
        session['cart'] = cart
        session.modified = True
    
    # Real-time Cart Sync
    if current_user.is_authenticated:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        count = sum(item.quantity for item in cart_items)
        socketio.emit('cart_updated', {'count': count, 'product_name': product.name, 'size': size, 'action': 'add'}, room=f"user_{current_user.id}")
    else:
        count = sum(item.get('quantity', 1) for item in session.get('cart', []))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        size_label = f" (Size: {size})" if size else ""
        return jsonify({'success': True, 'count': count, 'product_name': product.name, 'size': size, 'message': f'{product.name}{size_label} added to cart!'})
    
    size_label = f" (Size: {size})" if size else ""
    flash(f'{product.name}{size_label} added to cart!', 'success')
    return redirect(request.referrer or url_for('cart'))

@app.route('/buy_now/<int:product_id>', methods=['GET', 'POST'])
def buy_now(product_id):
    product = Product.query.get_or_404(product_id)
    size = request.args.get('size') or request.form.get('size') or ''
    if request.is_json:
        data = request.get_json(silent=True) or {}
        if 'size' in data:
            size = data['size']
    size = str(size).strip() if size else None
    
    if current_user.is_authenticated:
        if size:
            item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id, size=size).first()
        else:
            item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
            
        if item:
            item.quantity += 1
        else:
            item = CartItem(user_id=current_user.id, product_id=product_id, size=size)
            db.session.add(item)
        db.session.commit()
    else:
        cart = session.get('cart', [])
        found = False
        for item in cart:
            if item.get('id') == product.id and item.get('size') == size:
                item['quantity'] = item.get('quantity', 1) + 1
                found = True
                break
        if not found:
            cart.append({
                'id': product.id,
                'name': product.name,
                'price': product.discount_price if product.discount_price else product.price,
                'image_url': product.image_url,
                'size': size,
                'quantity': 1
            })
        session['cart'] = cart
        session.modified = True
    
    if current_user.is_authenticated:
        return redirect(url_for('checkout'))
    else:
        return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:item_id>')
def remove_from_cart(item_id):
    if current_user.is_authenticated:
        item = CartItem.query.get_or_404(item_id)
        if item.user_id == current_user.id:
            db.session.delete(item)
            db.session.commit()
    else:
        cart = session.get('cart', [])
        cart = [item for item in cart if item['id'] != item_id]
        session['cart'] = cart
    
    # Real-time Cart Sync
    if current_user.is_authenticated:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        count = sum(item.quantity for item in cart_items)
        socketio.emit('cart_updated', {'count': count, 'action': 'remove'}, room=f"user_{current_user.id}")
        
    return redirect(url_for('cart'))

@app.route('/update_cart_quantity/<int:item_id>', methods=['POST'])
def update_cart_quantity(item_id):
    action = request.form.get('action') # 'increase' or 'decrease'
    if current_user.is_authenticated:
        item = CartItem.query.get_or_404(item_id)
        if item.user_id == current_user.id:
            if action == 'increase':
                if item.product and item.product.stock is not None and item.quantity >= item.product.stock:
                    flash(f"Cannot add more. Available stock limit ({item.product.stock}) reached.", "warning")
                else:
                    item.quantity += 1
            elif action == 'decrease':
                if item.quantity > 1:
                    item.quantity -= 1
                else:
                    db.session.delete(item)
            db.session.commit()
    else:
        cart = session.get('cart', [])
        for item in cart:
            if item.get('id') == item_id:
                if action == 'increase':
                    item['quantity'] = item.get('quantity', 1) + 1
                elif action == 'decrease':
                    if item.get('quantity', 1) > 1:
                        item['quantity'] = item.get('quantity', 1) - 1
                    else:
                        cart.remove(item)
                break
        session['cart'] = cart
        
    return redirect(url_for('cart'))

@app.route('/wishlist')
@login_required
def wishlist():
    items = WishlistItem.query.filter_by(user_id=current_user.id).all()
    return render_template('wishlist.html', items=items)

@app.route('/add_to_wishlist/<int:product_id>', methods=['GET', 'POST'])
def add_to_wishlist(product_id):
    if not current_user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'redirect': url_for('login', next=url_for('product_detail', product_id=product_id)), 'message': 'Please log in to manage your wishlist.'}), 401
        flash('Please log in to manage your wishlist.', 'info')
        return redirect(url_for('login', next=request.referrer or url_for('product_detail', product_id=product_id)))
        
    product = Product.query.get_or_404(product_id)
    item = WishlistItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if not item:
        item = WishlistItem(user_id=current_user.id, product_id=product_id)
        db.session.add(item)
        db.session.commit()
        msg = f'Added to wishlist!'
        action = 'added'
    else:
        msg = f'Already in wishlist!'
        action = 'already_exists'
        
    count = WishlistItem.query.filter_by(user_id=current_user.id).count()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'success': True, 'action': action, 'in_wishlist': True, 'count': count, 'message': msg})
        
    flash(msg, 'success')
    return redirect(request.referrer or url_for('wishlist'))

@app.route('/remove_from_wishlist/<int:product_id>', methods=['GET', 'POST', 'DELETE'])
def remove_from_wishlist(product_id):
    if not current_user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'redirect': url_for('login'), 'message': 'Please log in to manage your wishlist.'}), 401
        flash('Please log in to manage your wishlist.', 'info')
        return redirect(url_for('login', next=request.referrer or url_for('wishlist')))
        
    product = Product.query.get_or_404(product_id)
    WishlistItem.query.filter_by(user_id=current_user.id, product_id=product_id).delete()
    db.session.commit()
    count = WishlistItem.query.filter_by(user_id=current_user.id).count()
    msg = f'Removed from wishlist!'
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'success': True, 'action': 'removed', 'in_wishlist': False, 'count': count, 'message': msg})
        
    flash(msg, 'info')
    return redirect(request.referrer or url_for('wishlist'))

@app.route('/toggle_wishlist/<int:product_id>', methods=['GET', 'POST'])
def toggle_wishlist(product_id):
    if not current_user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'redirect': url_for('login', next=url_for('product_detail', product_id=product_id)), 'message': 'Please log in to manage your wishlist.'}), 401
        flash('Please log in to manage your wishlist.', 'info')
        return redirect(url_for('login', next=request.referrer or url_for('product_detail', product_id=product_id)))
        
    product = Product.query.get_or_404(product_id)
    item = WishlistItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        in_wishlist = False
        msg = f'Removed from wishlist!'
        action = 'removed'
    else:
        new_item = WishlistItem(user_id=current_user.id, product_id=product_id)
        db.session.add(new_item)
        db.session.commit()
        in_wishlist = True
        msg = f'Added to wishlist!'
        action = 'added'
        
    count = WishlistItem.query.filter_by(user_id=current_user.id).count()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'success': True, 'action': action, 'in_wishlist': in_wishlist, 'count': count, 'message': msg})
        
    flash(msg, 'success' if in_wishlist else 'info')
    return redirect(request.referrer or url_for('wishlist'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('products'))
    
    total = sum((item.product.discount_price if item.product.discount_price else item.product.price) * item.quantity for item in cart_items)
    
    # Get dynamic Razorpay client configuration status
    _, key_id, _, is_configured = get_razorpay_client()
    
    if request.method == 'POST':
        # Fallback direct submission handler for COD or standard forms
        payment_method = (request.form.get('payment_method') or 'cod').lower()
        first_name = (request.form.get('first_name') or current_user.first_name or current_user.username or '').strip()
        last_name = (request.form.get('last_name') or current_user.last_name or '').strip()
        phone = (request.form.get('phone') or current_user.phone or '').strip()
        address = (request.form.get('address') or current_user.address or '').strip()
        city = (request.form.get('city') or current_user.city or '').strip()
        state = (request.form.get('state') or current_user.state or '').strip()
        zip_code = (request.form.get('zip_code') or current_user.zip_code or '').strip()
        
        if payment_method == 'cod':
            new_order = Order(
                user_id=current_user.id, 
                total_price=total,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
                payment_method='COD',
                payment_status='Pending',
                status='Pending'
            )
            db.session.add(new_order)
            db.session.flush()

            for item in cart_items:
                order_item = OrderItem(
                    order_id=new_order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price_at_order=item.product.discount_price if item.product.discount_price else item.product.price,
                    size=item.size
                )
                db.session.add(order_item)
                if item.product and item.product.stock is not None:
                    item.product.stock = max(0, item.product.stock - item.quantity)
                db.session.delete(item)
                
            db.session.commit()
            
            # Send notifications safely
            try:
                send_order_email(new_order)
            except Exception as mail_err:
                print(f"[MAIL ERROR] {mail_err}")
                
            flash(f'Order placed successfully (Cash on Delivery)! Order ID: FW-{new_order.id}', 'success')
            return redirect(url_for('track_order', order_id=new_order.id))
        else:
            # Online orders must go through Razorpay Checkout popup
            flash('Please complete payment through the secure Razorpay Checkout window.', 'info')
            return redirect(url_for('checkout'))
        
    return render_template(
        'checkout.html', 
        total=total, 
        items=cart_items, 
        stripe_key=STRIPE_PUBLISHABLE_KEY, 
        razorpay_key=key_id,
        razorpay_configured=is_configured
    )

@app.route('/api/pincode/<pincode>')
def api_pincode_lookup(pincode):
    """Proxy endpoint for Indian postal PIN code lookup with caching, timeout protection & administrative district normalization"""
    clean_pin = ''.join(c for c in str(pincode or '') if c.isdigit())
    if len(clean_pin) != 6:
        return jsonify([{'Status': 'Error', 'Message': 'Invalid PIN code format. Must be 6 digits.', 'PostOffice': None}]), 400
        
    try:
        import requests as req
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        resp = req.get(f'https://api.postalpincode.in/pincode/{clean_pin}', headers=headers, timeout=8)
        if resp.ok:
            data = resp.json()
            # Normalize reorganized administrative districts (e.g. 522612 -> Palnadu)
            if clean_pin == '522612' and isinstance(data, list) and len(data) > 0:
                if data[0].get('Status') == 'Success' and isinstance(data[0].get('PostOffice'), list):
                    for po in data[0]['PostOffice']:
                        if po.get('District', '').lower() == 'guntur':
                            po['District'] = 'Palnadu'
            return jsonify(data)
        return jsonify([{'Status': 'Error', 'Message': 'Postal service unavailable', 'PostOffice': None}]), 502
    except Exception as e:
        print(f"[PINCODE API] Error: {e}")
        return jsonify([{'Status': 'Error', 'Message': 'Postal service connection timeout', 'PostOffice': None}]), 500

@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    payment_method = (request.form.get('payment_method') or 'cod').lower()
    if payment_method == 'cod':
        return redirect(url_for('cod_success', **request.form))
    else:
        # All online payment methods (Razorpay, Cards, UPI) are initialized via AJAX Razorpay Checkout modal
        return redirect(url_for('checkout'))

@app.route('/cod_success', methods=['GET', 'POST'])
@login_required
def cod_success():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items: 
        return redirect(url_for('home'))
    
    total = sum((item.product.discount_price if item.product.discount_price else item.product.price) * item.quantity for item in cart_items)
    
    first_name = (request.args.get('first_name') or current_user.first_name or current_user.username or '').strip()
    last_name = (request.args.get('last_name') or current_user.last_name or '').strip()
    phone = (request.args.get('phone') or current_user.phone or '').strip()
    address = (request.args.get('address') or current_user.address or '').strip()
    city = (request.args.get('city') or current_user.city or '').strip()
    state = (request.args.get('state') or current_user.state or '').strip()
    zip_code = (request.args.get('zip_code') or current_user.zip_code or '').strip()
    
    new_order = Order(
        user_id=current_user.id,
        total_price=total,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        address=address,
        city=city,
        state=state,
        zip_code=zip_code,
        payment_method='COD',
        payment_status='Pending',
        status='Pending'
    )
    db.session.add(new_order)
    db.session.flush()

    for item in cart_items:
        order_item = OrderItem(
            order_id=new_order.id, 
            product_id=item.product_id, 
            quantity=item.quantity, 
            price_at_order=item.product.discount_price if item.product.discount_price else item.product.price,
            size=item.size
        )
        db.session.add(order_item)
        if item.product and item.product.stock is not None:
            item.product.stock = max(0, item.product.stock - item.quantity)
        db.session.delete(item)
    
    db.session.commit()
    try:
        send_order_email(new_order)
    except Exception as e:
        print(f"[MAIL ERROR] {e}")
        
    flash("Order Placed Successfully (Cash on Delivery)", "success")
    return redirect(url_for('track_order', order_id=new_order.id))

@app.route('/upi_payment')
@login_required
def upi_payment():
    flash("UPI payments are securely processed through Razorpay Checkout.", "info")
    return redirect(url_for('checkout'))

@app.route('/create_order', methods=['POST'])
@login_required
def create_order():
    """
    Creates an official Razorpay Order from server-verified cart totals.
    Calculates total in paise (INR * 100) strictly from database items.
    """
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return jsonify({'success': False, 'error': 'Your cart is empty. Please add items before checking out.'}), 400
    
    total = sum((item.product.discount_price if item.product.discount_price else item.product.price) * item.quantity for item in cart_items)
    amount_paise = int(round(total * 100))
    
    if amount_paise < 100:
        return jsonify({'success': False, 'error': 'Minimum checkout amount is ₹1.00.'}), 400
    
    client, key_id, key_secret, is_configured = get_razorpay_client()
    if not client or not key_id:
        return jsonify({
            'success': False, 
            'error': 'Razorpay payment gateway is not configured in .env. Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to enable online checkout.'
        }), 503
    
    try:
        receipt_id = f"rcpt_fw_{current_user.id}_{int(time.time())}"
        order_data = {
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': receipt_id,
            'payment_capture': 1,
            'notes': {
                'user_id': str(current_user.id),
                'user_email': str(current_user.email or ''),
                'platform': 'Fashion World Pro'
            }
        }
        razorpay_order = client.order.create(data=order_data)
        
        return jsonify({
            'success': True,
            'order_id': razorpay_order['id'],
            'amount': amount_paise,
            'currency': 'INR',
            'key': key_id,
            'name': f"{current_user.first_name or current_user.username or ''} {current_user.last_name or ''}".strip() or current_user.username,
            'email': current_user.email,
            'phone': current_user.phone or ''
        })
    except Exception as e:
        print(f"[RAZORPAY ORDER CREATION ERROR] {e}")
        return jsonify({'success': False, 'error': f'Failed to initiate payment: {str(e)}'}), 500

@app.route('/verify_payment', methods=['POST'])
@login_required
def verify_payment():
    """
    Verifies Razorpay payment signature server-side and creates confirmed Order in database.
    Prevents duplicate orders, deducts inventory, and sends confirmation emails.
    """
    data = request.get_json(silent=True) or {}
    
    razorpay_payment_id = (data.get('razorpay_payment_id') or '').strip()
    razorpay_order_id = (data.get('razorpay_order_id') or '').strip()
    razorpay_signature = (data.get('razorpay_signature') or '').strip()
    
    if not razorpay_payment_id or not razorpay_order_id or not razorpay_signature:
        return jsonify({'status': 'failure', 'error': 'Missing required payment verification parameters.'}), 400
    
    # 1. Check for duplicate processing (idempotency protection)
    existing_order = Order.query.filter(
        (Order.payment_id == razorpay_payment_id) |
        ((Order.razorpay_order_id == razorpay_order_id) & (Order.payment_status == 'Paid'))
    ).first()
    if existing_order:
        return jsonify({
            'status': 'success', 
            'order_id': existing_order.id,
            'already_processed': True,
            'message': 'Payment already verified.',
            'redirect_url': url_for('track_order', order_id=existing_order.id)
        })
    
    # 2. Server-side Razorpay Signature Verification
    client, key_id, key_secret, is_configured = get_razorpay_client()
    if not client or not key_secret:
        return jsonify({'status': 'failure', 'error': 'Razorpay gateway credentials missing or unconfigured.'}), 500
        
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }
    
    try:
        client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError as sig_err:
        print(f"[RAZORPAY VERIFY FAILED] Signature mismatch: {sig_err}")
        return jsonify({'status': 'failure', 'error': 'Payment signature verification failed. Untrusted transaction.'}), 400
    except Exception as verify_err:
        print(f"[RAZORPAY VERIFY ERROR] {verify_err}")
        return jsonify({'status': 'failure', 'error': f'Payment verification error: {str(verify_err)}'}), 400
    
    # 3. Create official order from server-side cart
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        # Check if another request just created the order
        recent_order = Order.query.filter_by(user_id=current_user.id, payment_id=razorpay_payment_id).first()
        if recent_order:
            return jsonify({
                'status': 'success', 
                'order_id': recent_order.id, 
                'redirect_url': url_for('track_order', order_id=recent_order.id)
            })
        return jsonify({'status': 'failure', 'error': 'No active items in cart to create order.'}), 400
        
    total = sum((item.product.discount_price if item.product.discount_price else item.product.price) * item.quantity for item in cart_items)
    
    first_name = (data.get('first_name') or current_user.first_name or current_user.username or '').strip()
    last_name = (data.get('last_name') or current_user.last_name or '').strip()
    phone = (data.get('phone') or current_user.phone or '').strip()
    address = (data.get('address') or current_user.address or '').strip()
    city = (data.get('city') or current_user.city or '').strip()
    state = (data.get('state') or current_user.state or '').strip()
    zip_code = (data.get('zip_code') or current_user.zip_code or '').strip()
    
    try:
        new_order = Order(
            user_id=current_user.id, 
            total_price=total,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            payment_method='Razorpay',
            payment_status='Paid',
            status='Paid',
            payment_id=razorpay_payment_id,
            razorpay_order_id=razorpay_order_id,
            payment_signature=razorpay_signature,
            payment_verified_at=datetime.utcnow()
        )
        db.session.add(new_order)
        db.session.flush()

        for item in cart_items:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price_at_order=item.product.discount_price if item.product.discount_price else item.product.price,
                size=item.size
            )
            db.session.add(order_item)
            if item.product and item.product.stock is not None:
                item.product.stock = max(0, item.product.stock - item.quantity)
            db.session.delete(item)
            
        # Update user profile address if empty
        if not current_user.address or not current_user.phone:
            if first_name and not current_user.first_name: current_user.first_name = first_name
            if last_name and not current_user.last_name: current_user.last_name = last_name
            if address and not current_user.address: current_user.address = address
            if city and not current_user.city: current_user.city = city
            if zip_code and not current_user.zip_code: current_user.zip_code = zip_code
            if phone and not current_user.phone: current_user.phone = phone
            
        db.session.commit()
        
        # Send confirmation notifications
        try:
            send_order_email(new_order)
        except Exception as e:
            print(f"[NOTIFICATION EMAIL ERROR] {e}")
        try:
            send_order_sms(new_order)
        except Exception as e:
            print(f"[NOTIFICATION SMS ERROR] {e}")
            
        return jsonify({
            'status': 'success', 
            'order_id': new_order.id,
            'message': 'Payment successfully verified!',
            'redirect_url': url_for('track_order', order_id=new_order.id)
        })
    except Exception as e:
        db.session.rollback()
        print(f"[DATABASE ORDER SAVE ERROR] {e}")
        return jsonify({'status': 'failure', 'error': 'Database error while saving order.'}), 500


@app.route('/invoice/<int:order_id>')
@login_required
def invoice(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('Permission denied.', 'danger')
        return redirect(url_for('home'))
    
    return render_template('invoice.html', order=order)

# Notification Helpers
def send_order_email(order):
    try:
        msg = Message(f"Order Confirmation - FW-{order.id}",
                      recipients=[order.user.email])
        msg.body = f"Hello {order.first_name},\n\nThank you for your order! Your order ID is FW-{order.id}.\nTotal Amount: INR {order.total_price:,.2f}\n\nWe will notify you once it's shipped."
        msg.html = render_template('email_order_success.html', order=order)
        mail.send(msg)
        print(f"SUCCESS: Email sent to {order.user.email}")
    except Exception as e:
        print(f"ERROR: Failed to send email: {e}")

def send_order_sms(order):
    # Simulated SMS logic (Replace with Twilio/Nexmo API)
    phone = order.user.phone or "N/A"
    print(f"SMS NOTIFICATION SENT: TO {phone} - 'Hello {order.first_name}, your order FW-{order.id} for INR {order.total_price:,.2f} has been placed successfully. Thank you!'")

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    if request.form.get('first_name') is not None:
        current_user.first_name = request.form.get('first_name').strip()
    if request.form.get('last_name') is not None:
        current_user.last_name = request.form.get('last_name').strip()
    if request.form.get('phone') is not None:
        current_user.phone = request.form.get('phone').strip()
    if request.form.get('address') is not None:
        current_user.address = request.form.get('address').strip()
    if request.form.get('city') is not None:
        current_user.city = request.form.get('city').strip()
    if request.form.get('zip_code') is not None:
        current_user.zip_code = request.form.get('zip_code').strip()
    db.session.commit()
    flash('Profile and address updated successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/track/<int:order_id>')
@login_required
def track_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('home'))
        
    # Calculate delivery date based on order date + 5 days
    delivery_date = (order.date_ordered + timedelta(days=5)).strftime('%d %B %Y')
    
    return render_template('track.html', order=order, delivery_date=delivery_date)

@app.route('/live_tracking/<int:order_id>')
@login_required
def live_tracking(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('home'))
    
    # Start tracking simulation in background if order is Shipped
    if order.status == 'Shipped':
        threading.Thread(target=simulate_delivery, args=(order_id, order.user_id)).start()
        
    return render_template('live_tracking.html', order=order)

def simulate_delivery(order_id, user_id):
    """Simulates delivery agent movement from warehouse to customer"""
    # Sample path: Bangalore Warehouse to some address
    path = [
        {"lat": 12.9716, "lng": 77.5946}, # Warehouse
        {"lat": 12.9800, "lng": 77.6000},
        {"lat": 12.9900, "lng": 77.6100},
        {"lat": 13.0000, "lng": 77.6200},
        {"lat": 13.0100, "lng": 77.6300},
        {"lat": 13.0200, "lng": 77.6411}  # Delivery Point
    ]
    
    for step in path:
        time.sleep(5) # Wait 5 seconds between updates
        socketio.emit('delivery_update', {
            'order_id': order_id,
            'location': step,
            'status': 'Moving' if step != path[-1] else 'Arrived'
        }, room=f"user_{user_id}")
        
        if step == path[-1]:
            # Update order status to Delivered in DB automatically for simulation
            with app.app_context():
                order = Order.query.get(order_id)
                if order:
                    order.status = 'Delivered'
                    db.session.commit()
                    socketio.emit('order_status_updated', {
                        'order_id': order_id,
                        'status': 'Delivered',
                        'message': "Agent has arrived! Your order is delivered."
                    }, room=f"user_{user_id}")

@app.route('/dashboard')
@login_required
def dashboard():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_ordered.desc()).all()
    total_orders_count = len(user_orders)
    delivered_count = sum(1 for o in user_orders if (o.status or '').strip().lower() == 'delivered')
    pending_count = sum(1 for o in user_orders if (o.status or '').strip().lower() in ['pending', 'processing', 'shipped', 'paid', 'order placed'])
    wishlist_count = WishlistItem.query.filter_by(user_id=current_user.id).count()
    return render_template('dashboard.html', 
                           orders=user_orders,
                           total_orders_count=total_orders_count,
                           delivered_count=delivered_count,
                           pending_count=pending_count,
                           wishlist_count=wishlist_count)

@app.route('/orders')
@app.route('/account')
@login_required
def orders():
    return redirect(url_for('dashboard'))

@app.route('/add_review/<int:product_id>', methods=['POST'])
@login_required
def add_review(product_id):
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    if rating:
        review = Review(product_id=product_id, user_id=current_user.id, rating=int(rating), comment=comment)
        db.session.add(review)
        db.session.commit()
        flash('Thank you for your review!', 'success')
    return redirect(url_for('product_detail', product_id=product_id))

# -------------------------------
# ADMIN SUITE ROUTES & CONTROLLERS
# -------------------------------

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Main Admin Command Center & Real-time Metrics Dashboard matching luxury reference design"""
    orders = Order.query.order_by(Order.date_ordered.desc()).all()
    products_count = Product.query.count()
    customers_count = User.query.filter_by(is_admin=False).count()
    
    # Financial KPI Metrics
    total_revenue = sum(o.total_price for o in orders if o.status != 'Cancelled')
    total_orders = len(orders)
    
    today_dt = date.today()
    orders_today = [o for o in orders if o.date_ordered and o.date_ordered.date() == today_dt]
    today_revenue = sum(o.total_price for o in orders_today if o.status != 'Cancelled')
    
    month_start = today_dt.replace(day=1)
    orders_month = [o for o in orders if o.date_ordered and o.date_ordered.date() >= month_start]
    month_revenue = sum(o.total_price for o in orders_month if o.status != 'Cancelled')
    
    # Pending Orders & Inventory Alert counts
    pending_orders = [o for o in orders if (o.status or '').strip().lower() == 'pending']
    pending_orders_count = len(pending_orders)
    low_stock_count = Product.query.filter(Product.stock <= 5).count()
    
    # Support Ticket counts
    total_tickets = SupportTicket.query.count()
    open_tickets = SupportTicket.query.filter(func.lower(SupportTicket.status) == 'open').count()
    in_progress_tickets = SupportTicket.query.filter(func.lower(SupportTicket.status) == 'in progress').count()
    resolved_tickets = SupportTicket.query.filter(func.lower(SupportTicket.status).in_(['resolved', 'closed'])).count()
    
    # Multi-period chart datasets: 7 Days, 30 Days, 90 Days, 1 Year
    def get_period_data(days_count, date_format='%d %b'):
        labels = []
        rev_vals = []
        ord_vals = []
        for i in range(days_count - 1, -1, -1):
            t_day = today_dt - timedelta(days=i)
            day_orders = [o for o in orders if o.date_ordered and o.date_ordered.date() == t_day]
            day_rev = sum(o.total_price for o in day_orders if o.status != 'Cancelled')
            labels.append(t_day.strftime(date_format))
            rev_vals.append(round(day_rev, 2))
            ord_vals.append(len(day_orders))
        return {'labels': labels, 'revenue': rev_vals, 'orders': ord_vals}

    chart_7d = get_period_data(7, '%a, %d %b')
    chart_30d = get_period_data(30, '%d %b')
    
    # 90 Days (Aggregated by 3-day buckets or weekly)
    labels_90d = []
    rev_90d = []
    ord_90d = []
    for i in range(12, -1, -1):
        bucket_start = today_dt - timedelta(days=(i * 7 + 6))
        bucket_end = today_dt - timedelta(days=(i * 7))
        b_orders = [o for o in orders if o.date_ordered and bucket_start <= o.date_ordered.date() <= bucket_end]
        b_rev = sum(o.total_price for o in b_orders if o.status != 'Cancelled')
        labels_90d.append(bucket_end.strftime('%d %b'))
        rev_90d.append(round(b_rev, 2))
        ord_90d.append(len(b_orders))
    chart_90d = {'labels': labels_90d, 'revenue': rev_90d, 'orders': ord_90d}
    
    # 1 Year (12 Months)
    labels_1y = []
    rev_1y = []
    ord_1y = []
    for i in range(11, -1, -1):
        m_year = today_dt.year
        m_month = today_dt.month - i
        while m_month <= 0:
            m_month += 12
            m_year -= 1
        m_date = date(m_year, m_month, 1)
        m_orders = [o for o in orders if o.date_ordered and o.date_ordered.year == m_year and o.date_ordered.month == m_month]
        m_rev = sum(o.total_price for o in m_orders if o.status != 'Cancelled')
        labels_1y.append(m_date.strftime('%b %Y'))
        rev_1y.append(round(m_rev, 2))
        ord_1y.append(len(m_orders))
    chart_1y = {'labels': labels_1y, 'revenue': rev_1y, 'orders': ord_1y}

    # Order Status Distribution
    status_counts = {'Pending': 0, 'Processing': 0, 'Shipped': 0, 'Delivered': 0, 'Cancelled': 0}
    for o in orders:
        st = (o.status or 'Pending').capitalize()
        if st in status_counts:
            status_counts[st] += 1
        else:
            status_counts['Pending'] += 1
            
    status_chart_data = {
        'labels': list(status_counts.keys()),
        'values': list(status_counts.values()),
        'percentages': [
            round((cnt / total_orders * 100) if total_orders > 0 else 0, 1)
            for cnt in status_counts.values()
        ]
    }
    
    # Recent Orders (Top 5-10)
    recent_orders = orders[:10]
    
    # Top Selling Products (Calculated dynamically from OrderItem)
    order_items = OrderItem.query.all()
    product_sales = {}
    for item in order_items:
        if item.product_id not in product_sales:
            prod_obj = item.product
            product_sales[item.product_id] = {
                'id': item.product_id,
                'name': prod_obj.name if prod_obj else f'Product #{item.product_id}',
                'category': prod_obj.category if prod_obj else 'General',
                'image_url': prod_obj.image_url if prod_obj else '/static/images/p1.jpg',
                'sold': 0,
                'revenue': 0.0
            }
        product_sales[item.product_id]['sold'] += item.quantity
        product_sales[item.product_id]['revenue'] += (item.price_at_order * item.quantity)
        
    top_selling_products = sorted(product_sales.values(), key=lambda x: x['sold'], reverse=True)[:5]
    if not top_selling_products:
        # Fallback if catalog is fresh
        popular_prods = Product.query.order_by(Product.id.desc()).limit(5).all()
        top_selling_products = [
            {
                'id': p.id,
                'name': p.name,
                'category': p.category,
                'image_url': p.image_url,
                'sold': max(1, 20 - i * 3),
                'revenue': round((p.discount_price or p.price) * max(1, 20 - i * 3), 2)
            } for i, p in enumerate(popular_prods)
        ]
        
    # Inventory Alerts (Products with stock <= 5, sorted by lowest stock)
    inventory_alerts = Product.query.filter(Product.stock <= 5).order_by(Product.stock.asc()).limit(5).all()
    if not inventory_alerts:
        # If no items below 5, show lowest stock products
        inventory_alerts = Product.query.order_by(Product.stock.asc()).limit(5).all()
        
    # Recent Customers
    recent_customers = User.query.filter_by(is_admin=False).order_by(User.id.desc()).limit(4).all()
    
    # Sparkline trends for top 6 KPI cards
    sparklines = {
        'revenue': [v for v in chart_30d['revenue'][-7:]] or [10, 20, 15, 30, 25, 40, 35],
        'orders': [v for v in chart_30d['orders'][-7:]] or [1, 3, 2, 5, 4, 6, 8],
        'customers': [1, 2, 1, 3, 2, 4, 3],
        'products': [products_count - 5, products_count - 3, products_count - 2, products_count - 1, products_count, products_count, products_count],
        'pending': [max(0, pending_orders_count + 2), max(0, pending_orders_count + 1), pending_orders_count, pending_orders_count + 1, pending_orders_count],
        'tickets': [total_tickets, open_tickets + 1, open_tickets, open_tickets]
    }
    
    return render_template(
        'admin/dashboard.html',
        total_revenue=total_revenue,
        today_revenue=today_revenue,
        month_revenue=month_revenue,
        orders_today_count=len(orders_today),
        total_orders=total_orders,
        total_products=products_count,
        total_customers=customers_count,
        pending_orders_count=pending_orders_count,
        low_stock_count=low_stock_count,
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        in_progress_tickets=in_progress_tickets,
        resolved_tickets=resolved_tickets,
        recent_orders=recent_orders,
        top_selling_products=top_selling_products,
        inventory_alerts=inventory_alerts,
        recent_customers=recent_customers,
        chart_7d=chart_7d,
        chart_30d=chart_30d,
        chart_90d=chart_90d,
        chart_1y=chart_1y,
        status_chart_data=status_chart_data,
        sparklines=sparklines,
        today_formatted=today_dt.strftime('%A, %d %B %Y')
    )

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard_alias():
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/api/search')
@admin_required
def admin_api_search():
    """Global admin search endpoint for orders, products, customers, and tickets"""
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify({'results': []})
        
    results = []
    # Search Orders
    clean_q = q.replace('#', '').replace('FW-', '').replace('fw-', '')
    orders_q = Order.query.filter(
        (Order.first_name.ilike(f'%{q}%')) |
        (Order.last_name.ilike(f'%{q}%')) |
        (Order.phone.ilike(f'%{q}%')) |
        (Order.city.ilike(f'%{q}%'))
    )
    if clean_q.isdigit():
        orders_q = orders_q.union(Order.query.filter(Order.id == int(clean_q)))
    for o in orders_q.limit(4).all():
        results.append({
            'type': 'Order',
            'icon': 'fa-solid fa-receipt',
            'title': f'Order #FW-{o.id} — {o.first_name} {o.last_name}',
            'subtitle': f'₹{o.total_price:,.2f} • {o.status} • {o.date_ordered.strftime("%d %b %Y") if o.date_ordered else ""}',
            'url': url_for('admin_order_detail', order_id=o.id)
        })
        
    # Search Products
    for p in Product.query.filter((Product.name.ilike(f'%{q}%')) | (Product.category.ilike(f'%{q}%'))).limit(4).all():
        results.append({
            'type': 'Product',
            'icon': 'fa-solid fa-shirt',
            'title': p.name,
            'subtitle': f'Category: {p.category} • Price: ₹{(p.discount_price or p.price):,.2f} • Stock: {p.stock}',
            'url': url_for('admin_edit_product', product_id=p.id)
        })
        
    # Search Customers
    for u in User.query.filter_by(is_admin=False).filter((User.username.ilike(f'%{q}%')) | (User.email.ilike(f'%{q}%')) | (User.phone.ilike(f'%{q}%'))).limit(3).all():
        results.append({
            'type': 'Customer',
            'icon': 'fa-solid fa-user',
            'title': f'{u.username} ({u.first_name or ""} {u.last_name or ""})',
            'subtitle': f'Email: {u.email} • Phone: {u.phone or "N/A"}',
            'url': url_for('admin_customer_detail', customer_id=u.id)
        })
        
    # Search Tickets
    for t in SupportTicket.query.filter((SupportTicket.ticket_number.ilike(f'%{q}%')) | (SupportTicket.subject.ilike(f'%{q}%')) | (SupportTicket.customer_name.ilike(f'%{q}%'))).limit(3).all():
        results.append({
            'type': 'Ticket',
            'icon': 'fa-solid fa-headset',
            'title': f'Ticket #{t.ticket_number} — {t.subject}',
            'subtitle': f'Customer: {t.customer_name} • Status: {t.status}',
            'url': url_for('admin_support_detail', ticket_id=t.id)
        })
        
    return jsonify({'results': results})

@app.route('/admin/products')
@admin_required
def admin_products():
    """Manage catalog inventory with search, category filters and pagination"""
    page = request.args.get('page', 1, type=int)
    query = request.args.get('query', '').strip()
    selected_category = request.args.get('category', '').strip()
    stock_status = request.args.get('stock_status', '').strip()
    
    products_query = Product.query
    
    if query:
        products_query = products_query.filter(
            (Product.name.ilike(f'%{query}%')) | 
            (Product.description.ilike(f'%{query}%')) |
            (Product.category.ilike(f'%{query}%'))
        )
        
    if selected_category:
        products_query = products_query.filter_by(category=selected_category)
        
    if stock_status == 'in_stock':
        products_query = products_query.filter(Product.stock > 5)
    elif stock_status == 'low_stock':
        products_query = products_query.filter(Product.stock > 0, Product.stock <= 5)
    elif stock_status == 'out_of_stock':
        products_query = products_query.filter(Product.stock <= 0)
        
    pagination = products_query.order_by(Product.id.desc()).paginate(page=page, per_page=20, error_out=False)
    categories = Category.query.filter_by(is_active=True).all()
    if not categories:
        # Fallback to distinct product categories if category table is empty
        distinct_cats = db.session.query(Product.category).distinct().all()
        categories = [type('Cat', (), {'name': c[0]})() for c in distinct_cats if c[0]]
        
    return render_template(
        'admin/products.html',
        products=pagination.items,
        pagination=pagination,
        categories=categories,
        query=query,
        selected_category=selected_category,
        stock_status=stock_status
    )

@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    """Add a new product with image file upload or URL"""
    categories = Category.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price_val = request.form.get('price', '').strip()
        discount_val = request.form.get('discount_price', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        stock = int(request.form.get('stock', 50))
        size = request.form.get('size', '').strip()
        color = request.form.get('color', '').strip()
        is_active = True if request.form.get('is_active') else False
        is_featured = True if request.form.get('is_featured') else False
        is_new_arrival = True if request.form.get('is_new_arrival') else False
        
        if not name or not price_val or not category or not description:
            flash("Please fill in all mandatory fields.", "danger")
            return render_template('admin/product_form.html', is_edit=False, categories=categories)
            
        try:
            price = float(price_val)
            discount_price = float(discount_val) if discount_val else None
        except ValueError:
            flash("Invalid price value entered.", "danger")
            return render_template('admin/product_form.html', is_edit=False, categories=categories)
            
        # Handle Image File Upload or URL
        image_url = request.form.get('image_url', '').strip() or '/static/images/p1.jpg'
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename and allowed_file(file.filename):
                fname = secure_filename(f"{secrets.token_hex(6)}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                image_url = f"/static/images/{fname}"
                
        # Ensure category exists in Category table
        cat_obj = Category.query.filter(func.lower(Category.name) == category.lower()).first()
        if not cat_obj:
            cat_obj = Category(name=category, description=f"Catalog category for {category}", is_active=True)
            db.session.add(cat_obj)
            
        new_product = Product(
            name=name,
            price=price,
            discount_price=discount_price,
            category=category,
            description=description,
            image_url=image_url,
            stock=stock,
            size=size,
            color=color,
            is_active=is_active,
            is_featured=is_featured,
            is_new_arrival=is_new_arrival
        )
        db.session.add(new_product)
        db.session.commit()
        
        flash(f'Product "{name}" created successfully and added to the store catalog!', 'success')
        return redirect(url_for('admin_products'))
        
    return render_template('admin/product_form.html', is_edit=False, categories=categories)

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    """Edit existing product details"""
    product = Product.query.get_or_404(product_id)
    categories = Category.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        product.name = request.form.get('name', '').strip()
        product.category = request.form.get('category', '').strip()
        product.description = request.form.get('description', '').strip()
        product.stock = int(request.form.get('stock', 0))
        product.size = request.form.get('size', '').strip()
        product.color = request.form.get('color', '').strip()
        product.is_active = True if request.form.get('is_active') else False
        product.is_featured = True if request.form.get('is_featured') else False
        product.is_new_arrival = True if request.form.get('is_new_arrival') else False
        
        try:
            product.price = float(request.form.get('price', product.price))
            disc = request.form.get('discount_price', '').strip()
            product.discount_price = float(disc) if disc else None
        except ValueError:
            flash("Invalid pricing entered.", "danger")
            return render_template('admin/product_form.html', is_edit=True, product=product, categories=categories)
            
        # Check for new image upload
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename and allowed_file(file.filename):
                fname = secure_filename(f"{secrets.token_hex(6)}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                product.image_url = f"/static/images/{fname}"
        elif request.form.get('image_url'):
            product.image_url = request.form.get('image_url').strip()
            
        db.session.commit()
        flash(f'Product "{product.name}" updated successfully.', 'success')
        return redirect(url_for('admin_products'))
        
    return render_template('admin/product_form.html', is_edit=True, product=product, categories=categories)

@app.route('/admin/products/delete/<int:product_id>', methods=['GET', 'POST'])
@app.route('/admin/delete_product/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_delete_product_action(product_id):
    """Safely remove product from catalog"""
    product = Product.query.get_or_404(product_id)
    # Clear associated cart and wishlist items first to protect referential integrity
    CartItem.query.filter_by(product_id=product_id).delete()
    WishlistItem.query.filter_by(product_id=product_id).delete()
    Review.query.filter_by(product_id=product_id).delete()
    
    prod_name = product.name
    db.session.delete(product)
    db.session.commit()
    flash(f'Product "{prod_name}" has been deleted.', 'info')
    return redirect(url_for('admin_products'))

@app.route('/admin/products/toggle/<int:product_id>', methods=['POST'])
@admin_required
def admin_toggle_product(product_id):
    """Toggle product visibility in store"""
    product = Product.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()
    status_str = "Active (Visible)" if product.is_active else "Hidden"
    flash(f'Product "{product.name}" is now {status_str}.', 'success')
    return redirect(request.referrer or url_for('admin_products'))

@app.route('/admin/products/quick_stock/<int:product_id>', methods=['POST'])
@admin_required
def admin_quick_stock_update(product_id):
    """Quick stock count update from alert table"""
    product = Product.query.get_or_404(product_id)
    new_stock = request.form.get('new_stock', type=int)
    if new_stock is not None and new_stock >= 0:
        product.stock = new_stock
        db.session.commit()
        flash(f'Stock for "{product.name}" updated to {new_stock} units.', 'success')
    return redirect(request.referrer or url_for('admin_low_stock'))

@app.route('/admin/categories')
@admin_required
def admin_categories():
    """Category taxonomy management"""
    categories = Category.query.all()
    # Compute product counts per category
    counts_raw = db.session.query(Product.category, func.count(Product.id)).group_by(Product.category).all()
    category_counts = {c[0]: c[1] for c in counts_raw if c[0]}
    
    return render_template('admin/categories.html', categories=categories, category_counts=category_counts)

@app.route('/admin/categories/add', methods=['POST'])
@admin_required
def admin_add_category():
    """Create a new category"""
    name = request.form.get('name', '').strip()
    desc = request.form.get('description', '').strip()
    is_active = True if request.form.get('is_active') else False
    
    if not name:
        flash("Category name cannot be empty.", "warning")
        return redirect(url_for('admin_categories'))
        
    existing = Category.query.filter(func.lower(Category.name) == name.lower()).first()
    if existing:
        flash(f'Category "{name}" already exists.', 'warning')
        return redirect(url_for('admin_categories'))
        
    cat = Category(name=name, description=desc, is_active=is_active)
    db.session.add(cat)
    db.session.commit()
    flash(f'Category "{name}" added successfully.', 'success')
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/delete/<int:category_id>', methods=['POST'])
@admin_required
def admin_delete_category(category_id):
    """Delete a category"""
    cat = Category.query.get_or_404(category_id)
    cat_name = cat.name
    db.session.delete(cat)
    db.session.commit()
    flash(f'Category "{cat_name}" removed.', 'info')
    return redirect(url_for('admin_categories'))

@app.route('/admin/orders')
@admin_required
def admin_orders():
    """Customer Orders list with filtering, search and status badges"""
    page = request.args.get('page', 1, type=int)
    query = request.args.get('query', '').strip()
    status_filter = request.args.get('status', '').strip()
    payment_filter = request.args.get('payment_status', '').strip()
    
    orders_query = Order.query
    
    if query:
        clean_q = query.replace('#', '').replace('FW-', '').replace('fw-', '').strip()
        filter_conds = [
            Order.first_name.ilike(f'%{query}%'),
            Order.last_name.ilike(f'%{query}%'),
            Order.phone.ilike(f'%{query}%'),
            Order.city.ilike(f'%{query}%')
        ]
        if clean_q.isdigit():
            filter_conds.append(Order.id == int(clean_q))
        # Match user email
        user_matches = User.query.filter(User.email.ilike(f'%{query}%')).all()
        if user_matches:
            user_ids = [u.id for u in user_matches]
            filter_conds.append(Order.user_id.in_(user_ids))
            
        from sqlalchemy import or_
        orders_query = orders_query.filter(or_(*filter_conds))
        
    if status_filter:
        orders_query = orders_query.filter(Order.status == status_filter)
        
    if payment_filter:
        orders_query = orders_query.filter(Order.payment_status == payment_filter)
        
    pagination = orders_query.order_by(Order.date_ordered.desc()).paginate(page=page, per_page=15, error_out=False)
    
    return render_template(
        'admin/orders.html',
        orders=pagination.items,
        pagination=pagination,
        query=query,
        status_filter=status_filter,
        payment_filter=payment_filter
    )

@app.route('/admin/orders/<int:order_id>')
@admin_required
def admin_order_detail(order_id):
    """Full order view with customer purchase details, items and fulfillment controls"""
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_detail.html', order=order)

@app.route('/admin/orders/<int:order_id>/update', methods=['POST'])
@app.route('/update_order_status/<int:order_id>', methods=['POST'])
@admin_required
def admin_update_order_status(order_id):
    """Update order status, payment status, tracking number and notify customer"""
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    payment_status = request.form.get('payment_status')
    tracking_number = request.form.get('tracking_number')
    
    if new_status:
        order.status = new_status
    if payment_status:
        order.payment_status = payment_status
    if tracking_number is not None:
        order.tracking_number = tracking_number.strip()
        
    db.session.commit()
    
    # Real-time WebSocket Notification to Customer Room
    socketio.emit('order_status_updated', {
        'order_id': order.id,
        'status': order.status,
        'payment_status': order.payment_status,
        'tracking_number': order.tracking_number,
        'message': f"Your order #FW-{order.id} status updated to '{order.status}'."
    }, room=f"user_{order.user_id}")
    
    flash(f"Order #FW-{order.id} updated successfully.", "success")
    return redirect(url_for('admin_order_detail', order_id=order.id))

@app.route('/admin/customers')
@admin_required
def admin_customers():
    """Customer directory with order counts and lifetime spend"""
    page = request.args.get('page', 1, type=int)
    query = request.args.get('query', '').strip()
    
    users_query = User.query.filter_by(is_admin=False)
    
    if query:
        users_query = users_query.filter(
            (User.username.ilike(f'%{query}%')) |
            (User.email.ilike(f'%{query}%')) |
            (User.first_name.ilike(f'%{query}%')) |
            (User.last_name.ilike(f'%{query}%')) |
            (User.phone.ilike(f'%{query}%'))
        )
        
    pagination = users_query.order_by(User.id.desc()).paginate(page=page, per_page=15, error_out=False)
    
    # Calculate spend and order stats per customer
    all_orders = Order.query.all()
    customer_order_counts = {}
    customer_spend_totals = {}
    for o in all_orders:
        customer_order_counts[o.user_id] = customer_order_counts.get(o.user_id, 0) + 1
        if o.status != 'Cancelled':
            customer_spend_totals[o.user_id] = customer_spend_totals.get(o.user_id, 0.0) + o.total_price
            
    return render_template(
        'admin/customers.html',
        customers=pagination.items,
        pagination=pagination,
        customer_order_counts=customer_order_counts,
        customer_spend_totals=customer_spend_totals,
        query=query
    )

@app.route('/admin/customers/<int:customer_id>')
@admin_required
def admin_customer_detail(customer_id):
    """Customer purchase history: Shows exactly which customer purchased what items"""
    customer = User.query.get_or_404(customer_id)
    orders = Order.query.filter_by(user_id=customer_id).order_by(Order.date_ordered.desc()).all()
    total_spent = sum(o.total_price for o in orders if o.status != 'Cancelled')
    
    return render_template(
        'admin/customer_detail.html',
        customer=customer,
        orders=orders,
        total_spent=total_spent
    )

@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    """Store sales, revenue and product analytics"""
    orders = Order.query.filter(Order.status != 'Cancelled').all()
    total_sales = sum(o.total_price for o in orders)
    total_orders_count = len(orders)
    avg_order_value = (total_sales / total_orders_count) if total_orders_count > 0 else 0.0
    
    # Calculate units sold and product popularity
    order_items = OrderItem.query.all()
    total_units_sold = sum(item.quantity for item in order_items)
    
    product_sales = {}
    for item in order_items:
        if item.product_id not in product_sales:
            product_sales[item.product_id] = {
                'name': item.product.name if item.product else f'Product #{item.product_id}',
                'units': 0,
                'revenue': 0.0
            }
        product_sales[item.product_id]['units'] += item.quantity
        product_sales[item.product_id]['revenue'] += (item.price_at_order * item.quantity)
        
    top_products = sorted(product_sales.values(), key=lambda x: x['revenue'], reverse=True)[:10]
    
    # Top spending customers
    customer_spend = {}
    for o in orders:
        if o.user_id not in customer_spend:
            customer_spend[o.user_id] = {
                'name': f"{o.first_name or ''} {o.last_name or ''}".strip() or (o.user.username if o.user else 'Customer'),
                'email': o.user.email if o.user else 'N/A',
                'orders': 0,
                'spent': 0.0
            }
        customer_spend[o.user_id]['orders'] += 1
        customer_spend[o.user_id]['spent'] += o.total_price
        
    top_customers = sorted(customer_spend.values(), key=lambda x: x['spent'], reverse=True)[:10]
    
    # Monthly sales trajectory (Last 6 Months)
    monthly_labels = []
    monthly_values = []
    today_dt = date.today()
    for i in range(5, -1, -1):
        # Calculate month
        m_year = today_dt.year
        m_month = today_dt.month - i
        while m_month <= 0:
            m_month += 12
            m_year -= 1
        m_date = date(m_year, m_month, 1)
        m_label = m_date.strftime('%b %Y')
        m_rev = sum(o.total_price for o in orders if o.date_ordered and o.date_ordered.year == m_year and o.date_ordered.month == m_month)
        monthly_labels.append(m_label)
        monthly_values.append(round(m_rev, 2))
        
    monthly_chart_data = {
        'labels': monthly_labels,
        'values': monthly_values
    }
    
    # Category sales breakdown
    category_sales = {}
    for item in order_items:
        cat_name = item.product.category if item.product else 'Other'
        category_sales[cat_name] = category_sales.get(cat_name, 0.0) + (item.price_at_order * item.quantity)
        
    category_chart_data = {
        'labels': list(category_sales.keys()) if category_sales else ['Men', 'Women'],
        'values': [round(v, 2) for v in category_sales.values()] if category_sales else [0, 0]
    }
    
    return render_template(
        'admin/analytics.html',
        total_sales=total_sales,
        avg_order_value=avg_order_value,
        total_units_sold=total_units_sold,
        top_products=top_products,
        top_customers=top_customers,
        monthly_chart_data=monthly_chart_data,
        category_chart_data=category_chart_data
    )

@app.route('/admin/low-stock')
@admin_required
def admin_low_stock():
    """Low stock inventory alert dashboard"""
    low_stock_items = Product.query.filter(Product.stock <= 5).order_by(Product.stock.asc()).all()
    return render_template('admin/low_stock.html', low_stock_items=low_stock_items)

@app.route('/admin/settings')
@app.route('/admin/settings/account')
@admin_required
def admin_account_settings():
    """Administrator Account & Security Settings Page"""
    return render_template('admin/account_settings.html')

@app.route('/admin/settings/store')
@admin_required
def admin_store_settings():
    """Store operational, branding, and integration settings"""
    store_meta = {
        'store_name': 'Fashion World Pro',
        'store_tagline': 'Style Beyond Trends',
        'support_email': os.getenv('MAIL_DEFAULT_SENDER') or os.getenv('MAIL_USERNAME', 'support@fashionworld.pro'),
        'currency': 'INR (₹)',
        'low_stock_threshold': 5,
        'delivery_days': 5,
        'razorpay_configured': bool(os.getenv('RAZORPAY_KEY_ID')),
        'google_oauth_configured': bool(os.getenv('GOOGLE_CLIENT_ID')),
        'gmail_smtp_configured': bool(os.getenv('MAIL_PASSWORD')),
        'pincode_api_active': True,
        'socketio_active': True
    }
    return render_template('admin/store_settings.html', store_meta=store_meta)

@app.route('/admin/settings/profile', methods=['POST'])
@admin_required
def admin_update_profile():
    """Update administrator name, display name, contact information"""
    username = request.form.get('username', '').strip()
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    phone = request.form.get('phone', '').strip()
    
    if not username:
        flash("Username / Admin Name cannot be empty.", "warning")
        return redirect(url_for('admin_account_settings'))
        
    # Prevent duplicate username across other users
    existing_user = User.query.filter(func.lower(User.username) == username.lower(), User.id != current_user.id).first()
    if existing_user:
        flash(f"The username '{username}' is already in use by another account.", "danger")
        return redirect(url_for('admin_account_settings'))
        
    current_user.username = username
    current_user.first_name = first_name
    current_user.last_name = last_name
    current_user.phone = phone
    db.session.commit()
    
    flash("Administrator profile details updated successfully.", "success")
    return redirect(url_for('admin_account_settings'))

@app.route('/admin/settings/change_email', methods=['POST'])
@admin_required
def admin_change_email():
    """Securely update administrator email address after password verification"""
    new_email = request.form.get('new_email', '').strip().lower()
    confirm_email = request.form.get('confirm_new_email', '').strip().lower()
    current_password = request.form.get('current_password', '')
    
    if not new_email or not confirm_email or not current_password:
        flash("All fields are required to update administrator email.", "danger")
        return redirect(url_for('admin_account_settings'))
        
    if new_email != confirm_email:
        flash("New email addresses do not match. Please verify.", "danger")
        return redirect(url_for('admin_account_settings'))
        
    if '@' not in new_email or '.' not in new_email.split('@')[-1]:
        flash("Please enter a valid email address format.", "danger")
        return redirect(url_for('admin_account_settings'))
        
    if new_email == current_user.email.lower():
        flash("New email is identical to your current email address.", "info")
        return redirect(url_for('admin_account_settings'))
        
    # Verify current password
    if not check_password_hash(current_user.password, current_password):
        flash("Incorrect current password. Email change request denied.", "danger")
        return redirect(url_for('admin_account_settings'))
        
    # Check for duplicate email across all users
    existing_email = User.query.filter(func.lower(User.email) == new_email, User.id != current_user.id).first()
    if existing_email:
        flash(f"The email address '{new_email}' is already registered to another user.", "danger")
        return redirect(url_for('admin_account_settings'))
        
    # Apply new email
    old_email = current_user.email
    user = db.session.get(User, current_user.id) if hasattr(db.session, 'get') else User.query.get(current_user.id)
    user.email = new_email
    db.session.commit()
    
    flash(f"Administrator email updated successfully from '{old_email}' to '{new_email}'.", "success")
    return redirect(url_for('admin_account_settings'))

@app.route('/admin/settings/change_password', methods=['POST'])
@admin_required
def admin_change_password():
    """Securely update administrator password, then invalidate session to force re-login"""
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_new_password', '')
    
    if not current_password or not new_password or not confirm_password:
        flash("All password fields are mandatory.", "danger")
        return redirect(url_for('admin_account_settings'))
        
    # Verify current password
    if not check_password_hash(current_user.password, current_password):
        flash("Current password verification failed. Password was not changed.", "danger")
        return redirect(url_for('admin_account_settings'))
        
    if new_password != confirm_password:
        flash("New password and confirmation password do not match.", "danger")
        return redirect(url_for('admin_account_settings'))
        
    if len(new_password) < 6:
        flash("New password must be at least 6 characters in length.", "danger")
        return redirect(url_for('admin_account_settings'))
        
    if check_password_hash(current_user.password, new_password):
        flash("New password must be different from your current password.", "warning")
        return redirect(url_for('admin_account_settings'))
        
    # Hash new password with pbkdf2:sha256 (project standard)
    hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
    user = db.session.get(User, current_user.id) if hasattr(db.session, 'get') else User.query.get(current_user.id)
    user.password = hashed_password
    db.session.commit()
    
    # Invalidate session and log out
    logout_user()
    session.clear()
    flash("Administrator password changed successfully! Please log in with your new password.", "success")
    return redirect(url_for('admin_login'))

# -------------------------------
# MARKETING & PROMOTIONS ROUTES
# -------------------------------

@app.route('/admin/marketing/banners')
@admin_required
def admin_banners_offers():
    """Manage promotional banners, hero collections, and discount offers"""
    featured_products = Product.query.filter_by(is_featured=True).limit(10).all()
    special_offers = Product.query.filter(Product.discount_price.isnot(None)).order_by(Product.id.desc()).limit(15).all()
    new_arrivals = Product.query.filter_by(is_new_arrival=True).limit(10).all()
    return render_template(
        'admin/marketing_banners.html',
        featured_products=featured_products,
        special_offers=special_offers,
        new_arrivals=new_arrivals
    )

@app.route('/admin/marketing/coupons')
@admin_required
def admin_coupons():
    """Store coupon codes and discount management"""
    # Active promotion codes
    coupons = [
        {'code': 'FASHION20', 'discount': '20% OFF', 'type': 'Percentage', 'min_spend': 1999, 'status': 'Active', 'usage_count': 42},
        {'code': 'WELCOME10', 'discount': '10% OFF', 'type': 'First Order', 'min_spend': 999, 'status': 'Active', 'usage_count': 128},
        {'code': 'FESTIVE500', 'discount': '₹500 OFF', 'type': 'Flat Discount', 'min_spend': 2999, 'status': 'Active', 'usage_count': 19},
        {'code': 'FREESHIP', 'discount': 'Free Shipping', 'type': 'Shipping', 'min_spend': 499, 'status': 'Active', 'usage_count': 310}
    ]
    return render_template('admin/marketing_coupons.html', coupons=coupons)

@app.route('/admin/marketing/reviews')
@admin_required
def admin_reviews():
    """Customer ratings and product reviews moderation"""
    reviews = Review.query.order_by(Review.id.desc()).all()
    avg_rating_raw = db.session.query(func.avg(Review.rating)).scalar() or 5.0
    total_reviews_count = len(reviews)
    return render_template(
        'admin/marketing_reviews.html',
        reviews=reviews,
        avg_rating=round(float(avg_rating_raw), 1),
        total_reviews_count=total_reviews_count
    )

@app.route('/admin/marketing/reviews/delete/<int:review_id>', methods=['POST'])
@admin_required
def admin_delete_review(review_id):
    """Safely delete inappropriate or spam product review"""
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash("Review has been successfully removed.", "info")
    return redirect(url_for('admin_reviews'))

# -------------------------------
# CUSTOMER SUPPORT & TICKETING ROUTES
# -------------------------------

@app.route('/support')
@login_required
def customer_support():
    """Customer Support Portal: Submit a ticket & view previous tickets"""
    prefilled_order_id = request.args.get('order_id', '').strip()
    my_tickets = SupportTicket.query.filter_by(user_id=current_user.id).order_by(SupportTicket.created_at.desc()).all()
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_ordered.desc()).all()
    
    return render_template(
        'support.html',
        my_tickets=my_tickets,
        user_orders=user_orders,
        prefilled_order_id=prefilled_order_id
    )

@app.route('/support/create', methods=['POST'])
@login_required
def create_support_ticket():
    """Process customer support ticket submission"""
    name = request.form.get('name', '').strip() or f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or current_user.username
    email = request.form.get('email', '').strip() or current_user.email
    order_id = request.form.get('order_id', '').strip()
    category = request.form.get('category', 'General Inquiry').strip()
    subject = request.form.get('subject', '').strip()
    message = request.form.get('message', '').strip()
    priority = request.form.get('priority', 'Medium').strip()

    if not subject or not message:
        flash("Please provide both a subject and a message for your support request.", "danger")
        return redirect(url_for('customer_support', order_id=order_id))

    # Generate unique ticket number: FW-TKT-XXXXXX
    ticket_num = f"FW-TKT-{secrets.randbelow(900000) + 100000}"
    while SupportTicket.query.filter_by(ticket_number=ticket_num).first():
        ticket_num = f"FW-TKT-{secrets.randbelow(900000) + 100000}"

    new_ticket = SupportTicket(
        ticket_number=ticket_num,
        user_id=current_user.id,
        customer_name=name,
        customer_email=email,
        order_id=order_id if order_id else None,
        category=category,
        subject=subject,
        message=message,
        priority=priority,
        status='Open'
    )
    db.session.add(new_ticket)
    db.session.commit()

    flash(f"Your support ticket #{ticket_num} has been successfully submitted! Our team will get back to you shortly.", "success")
    return redirect(url_for('view_support_ticket', ticket_number=ticket_num))

@app.route('/support/ticket/<ticket_number>')
@login_required
def view_support_ticket(ticket_number):
    """View customer support ticket details and admin replies"""
    ticket = SupportTicket.query.filter_by(ticket_number=ticket_number).first_or_404()
    
    # Strict Authorization: customer can only view their own tickets; admins can view any
    if ticket.user_id != current_user.id and not current_user.is_admin:
        flash("Permission denied: You cannot access this support ticket.", "danger")
        return redirect(url_for('customer_support'))

    related_order = None
    if ticket.order_id:
        clean_oid = ticket.order_id.replace('FW-', '').replace('#', '').strip()
        if clean_oid.isdigit():
            related_order = Order.query.get(int(clean_oid))

    return render_template('support_ticket_detail.html', ticket=ticket, related_order=related_order)

# -------------------------------
# ADMIN CUSTOMER SUPPORT SUITE
# -------------------------------

@app.route('/admin/support')
@admin_required
def admin_support_tickets():
    """Admin Support Dashboard: Manage and review all customer tickets"""
    status_filter = request.args.get('status', 'all').strip()
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()
    
    tickets_query = SupportTicket.query
    
    if status_filter and status_filter.lower() != 'all':
        tickets_query = tickets_query.filter(func.lower(SupportTicket.status) == status_filter.lower())
        
    if category_filter:
        tickets_query = tickets_query.filter(SupportTicket.category == category_filter)
        
    if search_query:
        tickets_query = tickets_query.filter(
            (SupportTicket.ticket_number.ilike(f'%{search_query}%')) |
            (SupportTicket.customer_name.ilike(f'%{search_query}%')) |
            (SupportTicket.customer_email.ilike(f'%{search_query}%')) |
            (SupportTicket.subject.ilike(f'%{search_query}%')) |
            (SupportTicket.order_id.ilike(f'%{search_query}%'))
        )
        
    tickets = tickets_query.order_by(SupportTicket.created_at.desc()).all()
    
    total_tickets = SupportTicket.query.count()
    open_tickets = SupportTicket.query.filter(func.lower(SupportTicket.status) == 'open').count()
    in_progress_tickets = SupportTicket.query.filter(func.lower(SupportTicket.status) == 'in progress').count()
    resolved_tickets = SupportTicket.query.filter(func.lower(SupportTicket.status).in_(['resolved', 'closed'])).count()
    
    return render_template(
        'admin/support_tickets.html',
        tickets=tickets,
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        in_progress_tickets=in_progress_tickets,
        resolved_tickets=resolved_tickets,
        current_filter=status_filter,
        category_filter=category_filter,
        search_query=search_query
    )

@app.route('/admin/support/<int:ticket_id>')
@admin_required
def admin_support_detail(ticket_id):
    """Admin single ticket view with reply form and status changer"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    related_order = None
    if ticket.order_id:
        clean_oid = ticket.order_id.replace('FW-', '').replace('#', '').strip()
        if clean_oid.isdigit():
            related_order = Order.query.get(int(clean_oid))
            
    return render_template('admin/support_ticket_detail.html', ticket=ticket, related_order=related_order)

@app.route('/admin/support/<int:ticket_id>/reply', methods=['POST'])
@admin_required
def admin_support_reply(ticket_id):
    """Submit administrator reply and update ticket status"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    reply_text = request.form.get('reply_text', '').strip()
    new_status = request.form.get('status', '').strip()
    
    if not reply_text:
        flash("Reply message cannot be empty.", "warning")
        return redirect(url_for('admin_support_detail', ticket_id=ticket.id))
        
    ticket.admin_reply = reply_text
    ticket.admin_replied_by = current_user.username or "Fashion World Support Team"
    ticket.replied_at = datetime.utcnow()
    
    if new_status:
        ticket.status = new_status
    elif ticket.status == 'Open':
        ticket.status = 'In Progress'
        
    db.session.commit()
    
    # Send optional email notification to customer
    send_ticket_reply_email(ticket)
    
    flash(f"Reply successfully posted for Ticket #{ticket.ticket_number}! Status: {ticket.status}.", "success")
    return redirect(url_for('admin_support_detail', ticket_id=ticket.id))

@app.route('/admin/support/<int:ticket_id>/status', methods=['POST'])
@admin_required
def admin_support_update_status(ticket_id):
    """Update support ticket status from admin panel"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    new_status = request.form.get('status', '').strip()
    if new_status in ['Open', 'In Progress', 'Resolved', 'Closed']:
        ticket.status = new_status
        db.session.commit()
        flash(f"Ticket #{ticket.ticket_number} status updated to {new_status}.", "success")
    return redirect(request.referrer or url_for('admin_support_tickets'))

def send_ticket_reply_email(ticket):
    """Send customer an email notification about the admin reply"""
    try:
        if not ticket.customer_email:
            return
        # Refresh dynamic Mail credentials if present from .env
        mail_user = os.getenv('MAIL_USERNAME', '').strip()
        mail_pwd = os.getenv('MAIL_PASSWORD', '').strip()
        if mail_user and mail_pwd:
            mail.username = mail_user
            mail.password = mail_pwd
            
        msg = Message(
            subject=f"Update on Support Ticket #{ticket.ticket_number} - Fashion World Pro",
            recipients=[ticket.customer_email]
        )
        msg.body = f"Hello {ticket.customer_name},\n\nOur support team has updated your ticket #{ticket.ticket_number}:\n\nStatus: {ticket.status}\nSubject: {ticket.subject}\n\nAdmin Reply:\n{ticket.admin_reply}\n\nYou can view full details in your account dashboard.\n\nBest regards,\nFashion World Pro Support"
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
            <h2 style="color: #0f172a; margin-top: 0;">Support Ticket Update</h2>
            <p>Hello <strong>{ticket.customer_name}</strong>,</p>
            <p>Our support team has replied to your ticket <strong>#{ticket.ticket_number}</strong>.</p>
            <div style="background: #f8fafc; padding: 15px; border-left: 4px solid #c5a880; margin: 15px 0; border-radius: 4px;">
                <p style="margin: 0 0 8px 0;"><strong>Status:</strong> <span style="background: #dcfce7; color: #15803d; padding: 3px 8px; border-radius: 4px; font-weight: 600;">{ticket.status}</span></p>
                <p style="margin: 0 0 8px 0;"><strong>Subject:</strong> {ticket.subject}</p>
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 10px 0;">
                <p style="margin: 0; font-style: italic; color: #334155;"><strong>Response:</strong><br>{ticket.admin_reply}</p>
            </div>
            <p style="color: #64748b; font-size: 13px;">Thank you for shopping with Fashion World Pro.</p>
        </div>
        """
        mail.send(msg)
        print(f"[SUPPORT EMAIL] Notification sent to {ticket.customer_email}")
    except Exception as e:
        print(f"[SUPPORT EMAIL] Note: Email notification skipped or failed: {e}")

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email')
    if email:
        flash(f'Thank you! {email} has been subscribed to our newsletter.', 'success')
    return redirect(url_for('home'))

# Database initialization script
def seed_db():
    with app.app_context():
        # Non-destructive schema migration for SQLite
        import sqlite3
        db_path = os.path.join(app.instance_path, 'fashion_world.db')
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(user)")
                existing_cols = [col[1] for col in cursor.fetchall()]
                if 'google_id' not in existing_cols:
                    cursor.execute("ALTER TABLE user ADD COLUMN google_id VARCHAR(150)")
                if 'auth_provider' not in existing_cols:
                    cursor.execute("ALTER TABLE user ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'local'")
                if 'firebase_uid' not in existing_cols:
                    cursor.execute("ALTER TABLE user ADD COLUMN firebase_uid VARCHAR(150)")
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Schema migration note: {e}")
                
        db.create_all()
        # Only seed products if database has no products
        if not Product.query.first():
            # Core curated products for Men and Women
            products = [
                Product(name="Silk Satin Blouse", price=4599.00, discount_price=3599.00, description="Luxurious silk satin blouse with a sophisticated drape.", image_url="/static/images/p1.jpg", category="Women"),
                Product(name="Minimalist Wool Coat", price=7990.00, discount_price=5990.00, description="A timeless minimalist wool coat for everyday elegancy.", image_url="/static/images/p2.jpg", category="Women"),
                Product(name="Slim Fit Denim", price=3450.00, description="Classic slim-fit denim jeans with high durability.", image_url="/static/images/p3.jpg", category="Women"),
                Product(name="Oversized Knit Sweater", price=3990.00, description="Cozy oversized knit sweater for chilly days.", image_url="/static/images/p5.jpg", category="Women"),
                Product(name="Linen Wrap Dress", price=5450.00, description="Breathable linen dress with a flattering wrap silhouette.", image_url="/static/images/p6.jpg", category="Women"),
                Product(name="Premium Linen Shirt", price=3190.00, description="A breathable cream linen shirt for casual or semi-formal looks.", image_url="/static/images/p7.jpg", category="Men"),
                Product(name="Charcoal Cashmere Sweater", price=6250.00, discount_price=4450.00, description="Exquisite charcoal grey cashmere for pure luxury.", image_url="/static/images/p8.jpg", category="Men"),
                Product(name="Executive Navy Suit", price=15490.00, discount_price=12990.00, description="A perfectly tailored navy blue suit for the board room or weddings.", image_url="/static/images/p1.jpg", category="Men"),
                # New Under 500 items from earlier
                Product(name="Essential White Tee", price=499.00, discount_price=299.00, description="100% organic cotton basic white tee.", image_url="/static/images/m1.png", category="Men"),
                Product(name="Classic Leather Belt", price=899.00, discount_price=499.00, description="Durable brown leather belt.", image_url="/static/images/m2.png", category="Men"),
                Product(name="Performance Crew Socks", price=399.00, discount_price=199.00, description="Moisture-wicking cushion socks.", image_url="/static/images/m3.png", category="Men"),
                Product(name="Casual Cotton Shorts", price=990.00, discount_price=450.00, description="Lightweight cotton chine shorts.", image_url="/static/images/m4.png", category="Men")
            ]
            
            # Bulk generation for "2000+ items" (Men and Women only)
            import random
            m_categories = ["Regular Fit Tee", "Pure Cotton Shirt", "Essential Chinos", "Signature Polos", "Modern Knit Sweatshirt", "Cargo Joggers", "Summer Linen Shirt", "Bamboo Fiber Socks", "Eco-friendly Mask", "Canvas Web Belt"]
            w_categories = ["Elegant Ribbed Top", "Minimalist Midi Skirt", "Straight Leg Jeans", "Lightweight Cardigan", "Silk Blend Scarf", "Boho Maxi Dress", "Classic Biker Jacket", "Organic Headband", "Fabric Clutch Bag", "Soft Cotton Camisole"]
            colors = ["Jet Black", "Cloud White", "Sage Green", "Desert Sand", "Navy Night", "Heather Grey", "Crimson Red", "Forest Green", "Royal Blue", "Slate Grey", "Pale Lavender", "Terracotta", "Olive Drab", "Midnight Blue"]
            
            m_images = ["m1.png", "m2.png", "m3.png", "m4.png", "m5.png", "m6.png", "mw1.png", "mw2.png", "mw3.png", "mw4.png", "u1.png", "u2.png", "u3.png"]
            w_images = ["p1.jpg", "p2.jpg", "p3.jpg", "p5.jpg", "p6.jpg", "p7.jpg", "ww1.png", "ww2.png", "ww3.png", "u1.png", "u2.png", "u3.png", "u4.png"]
            
            bulk_items = []
            for i in range(2200): # Expanding the catalog significantly
                is_men = (i % 2 == 0)
                category = "Men" if is_men else "Women"
                name_options = m_categories if is_men else w_categories
                color = colors[random.randint(0, len(colors)-1)]
                
                # Massive focus on "Under 500" - 70% chance of price being under 500
                if i < 1500 or random.random() < 0.7:
                    price = float(random.randint(99, 499))
                else:
                    price = float(random.randint(500, 999))
                    
                discount = None
                if random.random() > 0.7: # 30% items on sale
                    discount = price * 0.75 # 25% off
                    if discount < 99: discount = 99
                    
                img = random.choice(m_images if is_men else w_images)
                item_name = f"{color} {random.choice(name_options)} #{i+1000}"
                
                bulk_items.append(Product(
                    name=item_name,
                    price=price,
                    discount_price=discount,
                    description=f"High-quality sustainable {category.lower()}'s piece in {color}. Designed for durability and minimalist aesthetic.",
                    image_url=f"/static/images/{img}",
                    category=category
                ))
                
            db.session.add_all(products)
            db.session.bulk_save_objects(bulk_items)
            db.session.commit()
            
        # Admin Account - Only create default admin if NO administrator exists at all in the database
        if not User.query.filter_by(is_admin=True).first():
            admin_email = "admin@fashionworld.pro"
            hashed_admin_pass = generate_password_hash("admin123", method='pbkdf2:sha256')
            admin_user = User(username="Admin", email=admin_email, password=hashed_admin_pass, is_admin=True)
            db.session.add(admin_user)
            db.session.commit()
            print("[INFO] Default admin initialized.")

if __name__ == '__main__':
    seed_db()
    
    g_id_status = "PRESENT" if os.getenv('GOOGLE_CLIENT_ID', '').strip() else "MISSING"
    g_secret_status = "PRESENT" if os.getenv('GOOGLE_CLIENT_SECRET', '').strip() else "MISSING"
    
    print("\n========================================================")
    print(f"[INFO] Project Path: {BASE_DIR}")
    print(f"[INFO] Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("[INFO] Fashion World Pro is launching...")
    print("[INFO] URL: http://127.0.0.1:5000")
    print("[INFO] Real-time Engine: Gevent Enabled")
    print(f"[AUTH] Google OAuth: GOOGLE_CLIENT_ID = {g_id_status} | GOOGLE_CLIENT_SECRET = {g_secret_status}")
    print("========================================================\n")
    # Using use_reloader=False on Windows prevents double-start socket error
    socketio.run(app, host='127.0.0.1', port=5000, debug=True, use_reloader=False)
