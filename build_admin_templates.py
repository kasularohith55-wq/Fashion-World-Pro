# Admin builder script for Fashion World Pro
import os

TEMPLATES_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates', 'admin')
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# 1. admin_base.html
ADMIN_BASE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Admin Portal | Fashion World Pro{% endblock %}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Lora:ital,wght@0,600;1,600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        :root {
            --admin-primary: #1e293b;
            --admin-secondary: #0f172a;
            --admin-accent: #c5a880;
            --admin-accent-hover: #b0936b;
            --admin-accent-light: #fbf7f0;
            --admin-success: #10b981;
            --admin-warning: #f59e0b;
            --admin-danger: #ef4444;
            --admin-info: #3b82f6;
            --admin-bg: #f8fafc;
            --admin-card-bg: #ffffff;
            --admin-border: #e2e8f0;
            --admin-text-main: #1e293b;
            --admin-text-muted: #64748b;
            --sidebar-width: 270px;
            --header-height: 70px;
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
            --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 10px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 20px rgba(0, 0, 0, 0.08);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        body {
            background-color: var(--admin-bg);
            color: var(--admin-text-main);
            min-height: 100vh;
            display: flex;
            overflow-x: hidden;
        }

        .admin-sidebar {
            width: var(--sidebar-width);
            background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
            color: #f8fafc;
            position: fixed;
            top: 0;
            left: 0;
            bottom: 0;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 4px 0 24px rgba(0, 0, 0, 0.12);
        }

        .sidebar-brand {
            height: var(--header-height);
            display: flex;
            align-items: center;
            padding: 0 24px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            gap: 12px;
            text-decoration: none;
        }

        .sidebar-brand i.brand-icon {
            font-size: 20px;
            color: var(--admin-accent);
            background: rgba(197, 168, 128, 0.15);
            width: 38px;
            height: 38px;
            border-radius: var(--radius-sm);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .brand-text-wrapper {
            display: flex;
            flex-direction: column;
        }

        .brand-title {
            font-family: 'Lora', serif;
            font-size: 16px;
            font-weight: 600;
            color: #ffffff;
            letter-spacing: 0.5px;
        }

        .brand-badge {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--admin-accent);
            font-weight: 700;
        }

        .sidebar-menu {
            flex: 1;
            padding: 16px 14px;
            overflow-y: auto;
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .menu-category-label {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #64748b;
            padding: 14px 12px 6px 12px;
        }

        .sidebar-item a {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 11px 14px;
            color: #94a3b8;
            text-decoration: none;
            font-size: 13.5px;
            font-weight: 500;
            border-radius: var(--radius-sm);
            transition: all 0.2s ease;
        }

        .sidebar-item a i {
            font-size: 16px;
            width: 20px;
            text-align: center;
            color: #94a3b8;
            transition: color 0.2s ease;
        }

        .sidebar-item a:hover {
            color: #ffffff;
            background: rgba(255, 255, 255, 0.06);
        }

        .sidebar-item a:hover i {
            color: var(--admin-accent);
        }

        .sidebar-item.active a {
            background: var(--admin-accent);
            color: #0f172a;
            font-weight: 700;
            box-shadow: 0 4px 12px rgba(197, 168, 128, 0.35);
        }

        .sidebar-item.active a i {
            color: #0f172a;
        }

        .sidebar-footer {
            padding: 16px;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
            background: rgba(0, 0, 0, 0.25);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .admin-user-info {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .admin-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: var(--admin-accent);
            color: #0f172a;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 14px;
        }

        .admin-user-text {
            display: flex;
            flex-direction: column;
        }

        .admin-username {
            font-size: 13px;
            font-weight: 600;
            color: #ffffff;
        }

        .admin-role {
            font-size: 11px;
            color: var(--admin-accent);
        }

        .logout-btn {
            color: #94a3b8;
            text-decoration: none;
            font-size: 16px;
            padding: 8px;
            border-radius: var(--radius-sm);
            transition: all 0.2s ease;
        }

        .logout-btn:hover {
            color: var(--admin-danger);
            background: rgba(239, 68, 68, 0.15);
        }

        .admin-main {
            margin-left: var(--sidebar-width);
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            width: calc(100% - var(--sidebar-width));
        }

        .admin-header {
            height: var(--header-height);
            background: var(--admin-card-bg);
            border-bottom: 1px solid var(--admin-border);
            padding: 0 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 900;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .sidebar-toggle-btn {
            display: none;
            background: none;
            border: none;
            font-size: 20px;
            color: var(--admin-text-main);
            cursor: pointer;
        }

        .page-header-title {
            font-size: 20px;
            font-weight: 700;
            color: var(--admin-secondary);
        }

        .header-right {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .store-preview-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: var(--admin-accent-light);
            color: var(--admin-secondary);
            border: 1px solid rgba(197, 168, 128, 0.4);
            border-radius: var(--radius-sm);
            font-size: 13px;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.2s ease;
        }

        .store-preview-btn:hover {
            background: var(--admin-accent);
            color: #ffffff;
        }

        .live-status-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 20px;
            background: #dcfce7;
            color: #15803d;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #16a34a;
            box-shadow: 0 0 0 2px rgba(22, 163, 74, 0.2);
            animation: pulse-dot 2s infinite;
        }

        @keyframes pulse-dot {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(22, 163, 74, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(22, 163, 74, 0); }
        }

        .admin-content {
            padding: 28px 32px;
            flex: 1;
        }

        .admin-alerts {
            margin-bottom: 24px;
        }

        .admin-alert {
            padding: 14px 20px;
            border-radius: var(--radius-sm);
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: var(--shadow-sm);
        }

        .admin-alert.success { background: #ecfdf5; color: #065f46; border-left: 4px solid var(--admin-success); }
        .admin-alert.danger, .admin-alert.error { background: #fef2f2; color: #991b1b; border-left: 4px solid var(--admin-danger); }
        .admin-alert.warning { background: #fffbeb; color: #92400e; border-left: 4px solid var(--admin-warning); }
        .admin-alert.info { background: #eff6ff; color: #1e40af; border-left: 4px solid var(--admin-info); }

        .alert-close {
            background: none;
            border: none;
            font-size: 18px;
            cursor: pointer;
            color: inherit;
            opacity: 0.7;
        }
        .alert-close:hover { opacity: 1; }

        .admin-card {
            background: var(--admin-card-bg);
            border: 1px solid var(--admin-border);
            border-radius: var(--radius-md);
            padding: 24px;
            box-shadow: var(--shadow-sm);
            margin-bottom: 24px;
        }

        .card-header-flex {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 12px;
        }

        .card-title {
            font-size: 17px;
            font-weight: 700;
            color: var(--admin-secondary);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .btn-admin-primary {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: var(--admin-secondary);
            color: #ffffff;
            padding: 9px 18px;
            border-radius: var(--radius-sm);
            font-size: 13.5px;
            font-weight: 600;
            text-decoration: none;
            border: none;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .btn-admin-primary:hover {
            background: #1e293b;
            transform: translateY(-1px);
        }

        .btn-admin-accent {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: var(--admin-accent);
            color: #0f172a;
            padding: 9px 18px;
            border-radius: var(--radius-sm);
            font-size: 13.5px;
            font-weight: 700;
            text-decoration: none;
            border: none;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .btn-admin-accent:hover {
            background: var(--admin-accent-hover);
            transform: translateY(-1px);
        }

        .btn-admin-outline {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: transparent;
            color: var(--admin-text-main);
            padding: 8px 16px;
            border-radius: var(--radius-sm);
            font-size: 13.5px;
            font-weight: 600;
            text-decoration: none;
            border: 1px solid var(--admin-border);
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .btn-admin-outline:hover {
            background: #f1f5f9;
            border-color: #cbd5e1;
        }

        .btn-admin-sm {
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 600;
            border-radius: 6px;
        }

        .btn-admin-danger {
            background: #fee2e2;
            color: var(--admin-danger);
            border: 1px solid #fca5a5;
        }

        .btn-admin-danger:hover {
            background: var(--admin-danger);
            color: #ffffff;
        }

        .table-responsive {
            overflow-x: auto;
            width: 100%;
        }

        .admin-table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }

        .admin-table th {
            background: #f8fafc;
            color: var(--admin-text-muted);
            font-size: 11.5px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 12px 14px;
            border-bottom: 1px solid var(--admin-border);
            white-space: nowrap;
        }

        .admin-table td {
            padding: 14px;
            font-size: 13.5px;
            color: var(--admin-text-main);
            border-bottom: 1px solid var(--admin-border);
            vertical-align: middle;
        }

        .admin-table tr:hover td {
            background: #fbfcfd;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
        }

        .status-badge.pending { background: #fef3c7; color: #92400e; }
        .status-badge.processing { background: #e0f2fe; color: #0369a1; }
        .status-badge.shipped { background: #f3e8ff; color: #7e22ce; }
        .status-badge.delivered, .status-badge.paid, .status-badge.active { background: #dcfce7; color: #15803d; }
        .status-badge.cancelled, .status-badge.failed, .status-badge.inactive, .status-badge.out-of-stock { background: #fee2e2; color: #b91c1c; }
        .status-badge.refunded, .status-badge.low-stock { background: #ffedd5; color: #c2410c; }

        .pagination-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 20px;
            flex-wrap: wrap;
            gap: 12px;
        }

        .pagination-links {
            display: flex;
            gap: 6px;
        }

        .page-link {
            padding: 6px 12px;
            border: 1px solid var(--admin-border);
            background: #ffffff;
            color: var(--admin-text-main);
            text-decoration: none;
            border-radius: var(--radius-sm);
            font-size: 13px;
            font-weight: 600;
            transition: all 0.2s;
        }

        .page-link:hover, .page-link.active {
            background: var(--admin-secondary);
            color: #ffffff;
            border-color: var(--admin-secondary);
        }

        .page-link.disabled {
            opacity: 0.4;
            pointer-events: none;
        }

        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }

        .form-group {
            margin-bottom: 18px;
        }

        .form-group label {
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: var(--admin-secondary);
            margin-bottom: 6px;
        }

        .form-control {
            width: 100%;
            padding: 10px 14px;
            border: 1px solid var(--admin-border);
            border-radius: var(--radius-sm);
            font-size: 14px;
            background: #ffffff;
            color: var(--admin-text-main);
            transition: border-color 0.2s;
        }

        .form-control:focus {
            outline: none;
            border-color: var(--admin-accent);
            box-shadow: 0 0 0 3px rgba(197, 168, 128, 0.2);
        }

        textarea.form-control {
            min-height: 100px;
            resize: vertical;
        }

        @media (max-width: 1024px) {
            .admin-sidebar {
                transform: translateX(-100%);
            }
            .admin-sidebar.show {
                transform: translateX(0);
            }
            .admin-main {
                margin-left: 0;
                width: 100%;
            }
            .sidebar-toggle-btn {
                display: block;
            }
        }

        @media (max-width: 768px) {
            .admin-content {
                padding: 16px;
            }
            .admin-header {
                padding: 0 16px;
            }
        }
    </style>
    {% block extra_head %}{% endblock %}
</head>
<body>
    <aside class="admin-sidebar" id="adminSidebar">
        <a href="{{ url_for('admin_dashboard') }}" class="sidebar-brand">
            <i class="fa-solid fa-gem brand-icon"></i>
            <div class="brand-text-wrapper">
                <span class="brand-title">Fashion World</span>
                <span class="brand-badge">Admin Suite</span>
            </div>
        </a>

        <ul class="sidebar-menu">
            <li class="menu-category-label">Overview</li>
            <li class="sidebar-item {% if request.endpoint == 'admin_dashboard' %}active{% endif %}">
                <a href="{{ url_for('admin_dashboard') }}">
                    <i class="fa-solid fa-chart-pie"></i>
                    <span>Dashboard</span>
                </a>
            </li>
            <li class="sidebar-item {% if request.endpoint == 'admin_analytics' %}active{% endif %}">
                <a href="{{ url_for('admin_analytics') }}">
                    <i class="fa-solid fa-chart-line"></i>
                    <span>Sales Analytics</span>
                </a>
            </li>

            <li class="menu-category-label">Inventory & Catalog</li>
            <li class="sidebar-item {% if request.endpoint == 'admin_products' %}active{% endif %}">
                <a href="{{ url_for('admin_products') }}">
                    <i class="fa-solid fa-shirt"></i>
                    <span>All Products</span>
                </a>
            </li>
            <li class="sidebar-item {% if request.endpoint == 'admin_add_product' %}active{% endif %}">
                <a href="{{ url_for('admin_add_product') }}">
                    <i class="fa-solid fa-circle-plus"></i>
                    <span>Add New Product</span>
                </a>
            </li>
            <li class="sidebar-item {% if request.endpoint == 'admin_categories' %}active{% endif %}">
                <a href="{{ url_for('admin_categories') }}">
                    <i class="fa-solid fa-layer-group"></i>
                    <span>Categories</span>
                </a>
            </li>
            <li class="sidebar-item {% if request.endpoint == 'admin_low_stock' %}active{% endif %}">
                <a href="{{ url_for('admin_low_stock') }}">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <span>Stock Alerts</span>
                </a>
            </li>

            <li class="menu-category-label">Sales & Purchases</li>
            <li class="sidebar-item {% if request.endpoint in ['admin_orders', 'admin_order_detail'] %}active{% endif %}">
                <a href="{{ url_for('admin_orders') }}">
                    <i class="fa-solid fa-bag-shopping"></i>
                    <span>Customer Orders</span>
                </a>
            </li>
            <li class="sidebar-item {% if request.endpoint in ['admin_customers', 'admin_customer_detail'] %}active{% endif %}">
                <a href="{{ url_for('admin_customers') }}">
                    <i class="fa-solid fa-users"></i>
                    <span>Customer Directory</span>
                </a>
            </li>

            <li class="menu-category-label">Settings</li>
            <li class="sidebar-item {% if request.endpoint in ['admin_account_settings', 'admin_update_profile', 'admin_change_email', 'admin_change_password'] %}active{% endif %}">
                <a href="{{ url_for('admin_account_settings') }}">
                    <i class="fa-solid fa-user-gear"></i>
                    <span>Admin Account</span>
                </a>
            </li>

            <li class="menu-category-label">Storefront</li>
            <li class="sidebar-item">
                <a href="{{ url_for('home') }}" target="_blank">
                    <i class="fa-solid fa-store"></i>
                    <span>Visit Live Store</span>
                </a>
            </li>
        </ul>

        <div class="sidebar-footer">
            <div class="admin-user-info">
                <div class="admin-avatar">
                    {{ current_user.username[0]|upper if current_user.username else 'A' }}
                </div>
                <div class="admin-user-text">
                    <span class="admin-username">{{ current_user.username }}</span>
                    <span class="admin-role">Super Admin</span>
                </div>
            </div>
            <a href="{{ url_for('admin_logout') }}" class="logout-btn" title="Log Out">
                <i class="fa-solid fa-right-from-bracket"></i>
            </a>
        </div>
    </aside>

    <div class="admin-main">
        <header class="admin-header">
            <div class="header-left">
                <button class="sidebar-toggle-btn" id="sidebarToggle" aria-label="Toggle Navigation">
                    <i class="fa-solid fa-bars"></i>
                </button>
                <h1 class="page-header-title">{% block page_title %}Overview{% endblock %}</h1>
            </div>

            <div class="header-right">
                <span class="live-status-pill">
                    <span class="status-dot"></span>
                    Live Store Online
                </span>
                <a href="{{ url_for('home') }}" class="store-preview-btn" target="_blank">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i>
                    <span>Storefront</span>
                </a>
            </div>
        </header>

        <main class="admin-content">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    <div class="admin-alerts">
                        {% for category, message in messages %}
                            <div class="admin-alert {{ category }}">
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    {% if category == 'success' %}
                                        <i class="fa-solid fa-circle-check"></i>
                                    {% elif category in ['danger', 'error'] %}
                                        <i class="fa-solid fa-circle-exclamation"></i>
                                    {% elif category == 'warning' %}
                                        <i class="fa-solid fa-triangle-exclamation"></i>
                                    {% else %}
                                        <i class="fa-solid fa-circle-info"></i>
                                    {% endif %}
                                    <span>{{ message }}</span>
                                </div>
                                <button class="alert-close" onclick="this.parentElement.remove()">&times;</button>
                            </div>
                        {% endfor %}
                    </div>
                {% endif %}
            {% endwith %}

            {% block content %}{% endblock %}
        </main>
    </div>

    <script>
        const sidebarToggle = document.getElementById('sidebarToggle');
        const adminSidebar = document.getElementById('adminSidebar');
        if (sidebarToggle && adminSidebar) {
            sidebarToggle.addEventListener('click', () => {
                adminSidebar.classList.toggle('show');
            });
        }
    </script>
    {% block extra_scripts %}{% endblock %}
</body>
</html>
"""

# 2. dashboard.html
ADMIN_DASHBOARD = """{% extends "admin/admin_base.html" %}
{% block title %}Dashboard | Admin Portal{% endblock %}
{% block page_title %}Store Command Center{% endblock %}

{% block extra_head %}
<style>
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
        gap: 20px;
        margin-bottom: 28px;
    }

    .metric-card {
        background: var(--admin-card-bg);
        border: 1px solid var(--admin-border);
        border-radius: var(--radius-md);
        padding: 20px;
        display: flex;
        align-items: center;
        gap: 16px;
        box-shadow: var(--shadow-sm);
        transition: transform 0.2s, box-shadow 0.2s;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
    }

    .metric-icon-box {
        width: 52px;
        height: 52px;
        border-radius: var(--radius-sm);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
    }

    .icon-gold { background: #fef3c7; color: #b45309; }
    .icon-blue { background: #e0f2fe; color: #0369a1; }
    .icon-green { background: #dcfce7; color: #15803d; }
    .icon-purple { background: #f3e8ff; color: #7e22ce; }
    .icon-red { background: #fee2e2; color: #b91c1c; }

    .metric-data {
        display: flex;
        flex-direction: column;
    }

    .metric-value {
        font-size: 22px;
        font-weight: 800;
        color: var(--admin-secondary);
        line-height: 1.2;
    }

    .metric-label {
        font-size: 12.5px;
        font-weight: 500;
        color: var(--admin-text-muted);
        margin-top: 2px;
    }

    .dashboard-charts-grid {
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 24px;
        margin-bottom: 28px;
    }

    .quick-actions-bar {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin-bottom: 24px;
    }

    @media (max-width: 1024px) {
        .dashboard-charts-grid {
            grid-template-columns: 1fr;
        }
    }
</style>
{% endblock %}

{% block content %}
<!-- Quick Actions -->
<div class="quick-actions-bar">
    <a href="{{ url_for('admin_add_product') }}" class="btn-admin-accent">
        <i class="fa-solid fa-plus"></i> Add New Product
    </a>
    <a href="{{ url_for('admin_orders') }}" class="btn-admin-primary">
        <i class="fa-solid fa-bag-shopping"></i> View Orders
    </a>
    <a href="{{ url_for('admin_customers') }}" class="btn-admin-outline">
        <i class="fa-solid fa-users"></i> Customer Purchases
    </a>
    <a href="{{ url_for('admin_low_stock') }}" class="btn-admin-outline" style="color: var(--admin-danger); border-color: #fca5a5;">
        <i class="fa-solid fa-triangle-exclamation"></i> Low Stock Alerts ({{ low_stock_count }})
    </a>
</div>

<!-- Metrics Cards -->
<div class="metrics-grid">
    <div class="metric-card">
        <div class="metric-icon-box icon-gold">
            <i class="fa-solid fa-indian-rupee-sign"></i>
        </div>
        <div class="metric-data">
            <span class="metric-value">₹{{ "{:,.2f}".format(total_revenue) }}</span>
            <span class="metric-label">Total Revenue</span>
        </div>
    </div>

    <div class="metric-card">
        <div class="metric-icon-box icon-green">
            <i class="fa-solid fa-sun"></i>
        </div>
        <div class="metric-data">
            <span class="metric-value">₹{{ "{:,.2f}".format(today_revenue) }}</span>
            <span class="metric-label">Today's Sales ({{ orders_today_count }} orders)</span>
        </div>
    </div>

    <div class="metric-card">
        <div class="metric-icon-box icon-blue">
            <i class="fa-solid fa-calendar-days"></i>
        </div>
        <div class="metric-data">
            <span class="metric-value">₹{{ "{:,.2f}".format(month_revenue) }}</span>
            <span class="metric-label">This Month's Sales</span>
        </div>
    </div>

    <div class="metric-card">
        <div class="metric-icon-box icon-purple">
            <i class="fa-solid fa-boxes-stacked"></i>
        </div>
        <div class="metric-data">
            <span class="metric-value">{{ total_orders }}</span>
            <span class="metric-label">Lifetime Orders</span>
        </div>
    </div>

    <div class="metric-card">
        <div class="metric-icon-box icon-blue">
            <i class="fa-solid fa-shirt"></i>
        </div>
        <div class="metric-data">
            <span class="metric-value">{{ total_products }}</span>
            <span class="metric-label">Total Catalog Products</span>
        </div>
    </div>

    <div class="metric-card">
        <div class="metric-icon-box icon-gold">
            <i class="fa-solid fa-users"></i>
        </div>
        <div class="metric-data">
            <span class="metric-value">{{ total_customers }}</span>
            <span class="metric-label">Registered Customers</span>
        </div>
    </div>
</div>

<!-- Analytics Charts -->
<div class="dashboard-charts-grid">
    <div class="admin-card">
        <div class="card-header-flex">
            <div>
                <h3 class="card-title"><i class="fa-solid fa-chart-area" style="color: var(--admin-accent);"></i> Sales Trend (Recent Days)</h3>
                <span class="card-subtitle">Daily revenue trajectory</span>
            </div>
        </div>
        <div style="height: 280px; position: relative;">
            <canvas id="salesTrendChart"></canvas>
        </div>
    </div>

    <div class="admin-card">
        <div class="card-header-flex">
            <div>
                <h3 class="card-title"><i class="fa-solid fa-pie-chart" style="color: var(--admin-accent);"></i> Order Status</h3>
                <span class="card-subtitle">Fulfillment breakdown</span>
            </div>
        </div>
        <div style="height: 280px; position: relative;">
            <canvas id="orderStatusChart"></canvas>
        </div>
    </div>
</div>

<!-- Recent Orders & Inventory Warning -->
<div class="admin-card">
    <div class="card-header-flex">
        <div>
            <h3 class="card-title"><i class="fa-solid fa-receipt" style="color: var(--admin-accent);"></i> Recent Customer Purchases</h3>
            <span class="card-subtitle">Last 10 customer orders with live status</span>
        </div>
        <a href="{{ url_for('admin_orders') }}" class="btn-admin-outline btn-admin-sm">
            View All Orders <i class="fa-solid fa-arrow-right"></i>
        </a>
    </div>

    <div class="table-responsive">
        <table class="admin-table">
            <thead>
                <tr>
                    <th>Order #</th>
                    <th>Date</th>
                    <th>Customer</th>
                    <th>Contact</th>
                    <th>Amount</th>
                    <th>Payment</th>
                    <th>Order Status</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {% for order in recent_orders %}
                <tr>
                    <td><strong>#FW-{{ order.id }}</strong></td>
                    <td>{{ order.date_ordered.strftime('%d %b %Y, %I:%M %p') if order.date_ordered else 'N/A' }}</td>
                    <td>
                        <strong>{{ order.first_name }} {{ order.last_name }}</strong>
                    </td>
                    <td>
                        <div><i class="fa-regular fa-envelope" style="color:#94a3b8;"></i> {{ order.user.email if order.user else 'Guest' }}</div>
                        {% if order.phone or (order.user and order.user.phone) %}
                        <div style="font-size: 12px; color: #64748b;"><i class="fa-solid fa-phone" style="color:#94a3b8;"></i> {{ order.phone or order.user.phone }}</div>
                        {% endif %}
                    </td>
                    <td><strong>₹{{ "{:,.2f}".format(order.total_price) }}</strong></td>
                    <td>
                        <span class="status-badge {{ order.payment_status|lower if order.payment_status else 'pending' }}">
                            {{ order.payment_status or 'Pending' }}
                        </span>
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; margin-top: 2px;">{{ order.payment_method or 'Card/UPI' }}</div>
                    </td>
                    <td>
                        <span class="status-badge {{ order.status|lower }}">
                            {{ order.status }}
                        </span>
                    </td>
                    <td>
                        <a href="{{ url_for('admin_order_detail', order_id=order.id) }}" class="btn-admin-outline btn-admin-sm">
                            Manage <i class="fa-solid fa-chevron-right"></i>
                        </a>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="8" style="text-align: center; padding: 30px; color: #94a3b8;">
                        No orders recorded yet.
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}

{% block extra_scripts %}
<script>
    // Sales Trend Chart
    const salesCtx = document.getElementById('salesTrendChart').getContext('2d');
    const salesData = {{ sales_chart_data|tojson }};
    new Chart(salesCtx, {
        type: 'line',
        data: {
            labels: salesData.labels,
            datasets: [{
                label: 'Revenue (₹)',
                data: salesData.values,
                borderColor: '#c5a880',
                backgroundColor: 'rgba(197, 168, 128, 0.15)',
                borderWidth: 2.5,
                fill: true,
                tension: 0.35,
                pointBackgroundColor: '#c5a880',
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: '#f1f5f9' },
                    ticks: {
                        callback: function(value) { return '₹' + value.toLocaleString(); }
                    }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });

    // Order Status Doughnut
    const statusCtx = document.getElementById('orderStatusChart').getContext('2d');
    const statusData = {{ status_chart_data|tojson }};
    new Chart(statusCtx, {
        type: 'doughnut',
        data: {
            labels: statusData.labels,
            datasets: [{
                data: statusData.values,
                backgroundColor: ['#f59e0b', '#3b82f6', '#8b5cf6', '#10b981', '#ef4444'],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            },
            cutout: '70%'
        }
    });
</script>
{% endblock %}
"""

# 3. products.html
ADMIN_PRODUCTS = """{% extends "admin/admin_base.html" %}
{% block title %}Products Catalog | Admin Portal{% endblock %}
{% block page_title %}Catalog Management{% endblock %}

{% block extra_head %}
<style>
    .filter-bar {
        background: var(--admin-card-bg);
        border: 1px solid var(--admin-border);
        border-radius: var(--radius-md);
        padding: 16px 20px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        flex-wrap: wrap;
    }

    .filter-inputs {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        flex: 1;
    }

    .product-img-thumb {
        width: 48px;
        height: 56px;
        object-fit: cover;
        border-radius: 6px;
        border: 1px solid var(--admin-border);
    }
</style>
{% endblock %}

{% block content %}
<div class="filter-bar">
    <form method="GET" action="{{ url_for('admin_products') }}" class="filter-inputs">
        <input type="text" name="query" class="form-control" style="max-width: 260px;" placeholder="Search by name..." value="{{ query }}">
        
        <select name="category" class="form-control" style="max-width: 180px;">
            <option value="">All Categories</option>
            {% for cat in categories %}
            <option value="{{ cat.name }}" {% if selected_category == cat.name %}selected{% endif %}>{{ cat.name }}</option>
            {% endfor %}
        </select>

        <select name="stock_status" class="form-control" style="max-width: 180px;">
            <option value="">All Stock Levels</option>
            <option value="in_stock" {% if stock_status == 'in_stock' %}selected{% endif %}>In Stock (>5)</option>
            <option value="low_stock" {% if stock_status == 'low_stock' %}selected{% endif %}>Low Stock (1-5)</option>
            <option value="out_of_stock" {% if stock_status == 'out_of_stock' %}selected{% endif %}>Out of Stock (0)</option>
        </select>

        <button type="submit" class="btn-admin-primary btn-admin-sm">
            <i class="fa-solid fa-filter"></i> Apply Filters
        </button>
        {% if query or selected_category or stock_status %}
        <a href="{{ url_for('admin_products') }}" class="btn-admin-outline btn-admin-sm">
            <i class="fa-solid fa-xmark"></i> Clear
        </a>
        {% endif %}
    </form>

    <a href="{{ url_for('admin_add_product') }}" class="btn-admin-accent">
        <i class="fa-solid fa-plus-circle"></i> Add New Product
    </a>
</div>

<div class="admin-card">
    <div class="card-header-flex">
        <div>
            <h3 class="card-title">Products Inventory ({{ pagination.total }})</h3>
            <span class="card-subtitle">Viewing page {{ pagination.page }} of {{ pagination.pages }}</span>
        </div>
    </div>

    <div class="table-responsive">
        <table class="admin-table">
            <thead>
                <tr>
                    <th>Item</th>
                    <th>Product Name</th>
                    <th>Category</th>
                    <th>Price</th>
                    <th>Discount</th>
                    <th>Stock</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for product in products %}
                <tr>
                    <td>
                        <img src="{{ product.image_url }}" alt="{{ product.name }}" class="product-img-thumb" onerror="this.src='/static/images/p1.jpg'">
                    </td>
                    <td>
                        <strong>{{ product.name }}</strong>
                        {% if product.is_featured %}
                        <span style="font-size: 10px; background: #fef3c7; color: #b45309; padding: 2px 6px; border-radius: 4px; font-weight: 700; margin-left: 6px;">FEATURED</span>
                        {% endif %}
                    </td>
                    <td>
                        <span class="status-badge" style="background: #f1f5f9; color: #334155;">{{ product.category }}</span>
                    </td>
                    <td><strong>₹{{ "{:,.2f}".format(product.price) }}</strong></td>
                    <td>
                        {% if product.discount_price %}
                        <span style="color: #15803d; font-weight: 700;">₹{{ "{:,.2f}".format(product.discount_price) }}</span>
                        {% else %}
                        <span style="color: #94a3b8;">-</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if product.stock <= 0 %}
                        <span class="status-badge out-of-stock">Out of Stock (0)</span>
                        {% elif product.stock <= 5 %}
                        <span class="status-badge low-stock">Low: {{ product.stock }}</span>
                        {% else %}
                        <span class="status-badge active">{{ product.stock }} units</span>
                        {% endif %}
                    </td>
                    <td>
                        <form method="POST" action="{{ url_for('admin_toggle_product', product_id=product.id) }}" style="display:inline;">
                            <button type="submit" class="status-badge {% if product.is_active %}active{% else %}inactive{% endif %}" style="border:none; cursor:pointer;" title="Click to toggle visibility">
                                {% if product.is_active %}<i class="fa-solid fa-eye"></i> Active{% else %}<i class="fa-solid fa-eye-slash"></i> Hidden{% endif %}
                            </button>
                        </form>
                    </td>
                    <td>
                        <div style="display: flex; gap: 8px;">
                            <a href="{{ url_for('admin_edit_product', product_id=product.id) }}" class="btn-admin-outline btn-admin-sm" title="Edit Product">
                                <i class="fa-solid fa-pen-to-square"></i>
                            </a>
                            <a href="{{ url_for('product_detail', product_id=product.id) }}" target="_blank" class="btn-admin-outline btn-admin-sm" title="View in Store">
                                <i class="fa-solid fa-arrow-up-right-from-square"></i>
                            </a>
                            <form method="POST" action="{{ url_for('admin_delete_product_action', product_id=product.id) }}" onsubmit="return confirm('Are you sure you want to delete this product?');" style="display: inline;">
                                <button type="submit" class="btn-admin-outline btn-admin-danger btn-admin-sm" title="Delete Product">
                                    <i class="fa-solid fa-trash"></i>
                                </button>
                            </form>
                        </div>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="8" style="text-align: center; padding: 40px; color: #94a3b8;">
                        No products found matching your filter criteria.
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- Pagination -->
    {% if pagination.pages > 1 %}
    <div class="pagination-container">
        <span style="font-size: 13px; color: #64748b;">Showing {{ products|length }} of {{ pagination.total }} items</span>
        <div class="pagination-links">
            {% if pagination.has_prev %}
            <a href="{{ url_for('admin_products', page=pagination.prev_num, query=query, category=selected_category, stock_status=stock_status) }}" class="page-link">&laquo; Prev</a>
            {% endif %}

            {% for p in pagination.iter_pages(left_edge=1, right_edge=1, left_current=2, right_current=2) %}
                {% if p %}
                    {% if p == pagination.page %}
                    <span class="page-link active">{{ p }}</span>
                    {% else %}
                    <a href="{{ url_for('admin_products', page=p, query=query, category=selected_category, stock_status=stock_status) }}" class="page-link">{{ p }}</a>
                    {% endif %}
                {% else %}
                    <span class="page-link disabled">...</span>
                {% endif %}
            {% endfor %}

            {% if pagination.has_next %}
            <a href="{{ url_for('admin_products', page=pagination.next_num, query=query, category=selected_category, stock_status=stock_status) }}" class="page-link">Next &raquo;</a>
            {% endif %}
        </div>
    </div>
    {% endif %}
</div>
{% endblock %}
"""

# 4. product_form.html
ADMIN_PRODUCT_FORM = """{% extends "admin/admin_base.html" %}
{% block title %}{% if is_edit %}Edit Product{% else %}Add Product{% endif %} | Admin Portal{% endblock %}
{% block page_title %}{% if is_edit %}Edit Product: {{ product.name }}{% else %}Add New Catalog Product{% endif %}{% endblock %}

{% block content %}
<div class="admin-card" style="max-width: 900px; margin: 0 auto;">
    <div class="card-header-flex">
        <div>
            <h3 class="card-title">
                <i class="fa-solid fa-{% if is_edit %}pen-to-square{% else %}circle-plus{% endif %}" style="color: var(--admin-accent);"></i>
                {% if is_edit %}Update Product Details{% else %}Create New Product{% endif %}
            </h3>
            <span class="card-subtitle">Fill in complete product specification and pricing</span>
        </div>
        <a href="{{ url_for('admin_products') }}" class="btn-admin-outline btn-admin-sm">
            <i class="fa-solid fa-arrow-left"></i> Back to Catalog
        </a>
    </div>

    <form method="POST" enctype="multipart/form-data" action="{% if is_edit %}{{ url_for('admin_edit_product', product_id=product.id) }}{% else %}{{ url_for('admin_add_product') }}{% endif %}">
        <div class="form-grid">
            <div class="form-group" style="grid-column: 1 / -1;">
                <label for="name">Product Name *</label>
                <input type="text" id="name" name="name" class="form-control" required value="{{ product.name if is_edit else '' }}" placeholder="e.g. Pure Cotton Slim Fit Shirt">
            </div>

            <div class="form-group">
                <label for="category">Category *</label>
                <input type="text" list="category_list" id="category" name="category" class="form-control" required value="{{ product.category if is_edit else '' }}" placeholder="Men, Women, Accessories...">
                <datalist id="category_list">
                    {% for cat in categories %}
                    <option value="{{ cat.name }}">
                    {% endfor %}
                </datalist>
            </div>

            <div class="form-group">
                <label for="stock">Inventory Stock Count *</label>
                <input type="number" id="stock" name="stock" class="form-control" required min="0" value="{{ product.stock if is_edit else '50' }}">
            </div>

            <div class="form-group">
                <label for="price">Standard Price (₹) *</label>
                <input type="number" step="0.01" id="price" name="price" class="form-control" required value="{{ product.price if is_edit else '' }}" placeholder="e.g. 1999.00">
            </div>

            <div class="form-group">
                <label for="discount_price">Discount / Special Price (₹, optional)</label>
                <input type="number" step="0.01" id="discount_price" name="discount_price" class="form-control" value="{{ product.discount_price if is_edit and product.discount_price else '' }}" placeholder="e.g. 1499.00">
            </div>

            <div class="form-group">
                <label for="size">Available Sizes (comma separated)</label>
                <input type="text" id="size" name="size" class="form-control" value="{{ product.size if is_edit and product.size else 'S, M, L, XL, XXL' }}" placeholder="S, M, L, XL">
            </div>

            <div class="form-group">
                <label for="color">Available Colors</label>
                <input type="text" id="color" name="color" class="form-control" value="{{ product.color if is_edit and product.color else 'Jet Black, Cloud White, Navy' }}" placeholder="Black, White, Blue">
            </div>

            <div class="form-group" style="grid-column: 1 / -1;">
                <label for="description">Detailed Description *</label>
                <textarea id="description" name="description" class="form-control" rows="4" required placeholder="Provide details on fabric, fit, styling notes and care instructions...">{{ product.description if is_edit else '' }}</textarea>
            </div>

            <div class="form-group" style="grid-column: 1 / -1;">
                <label>Product Image Source</label>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start;">
                    <div>
                        <label for="image_file" style="font-weight: 500; font-size: 12px; color: #64748b;">Upload Image File</label>
                        <input type="file" id="image_file" name="image_file" class="form-control" accept="image/*">
                    </div>
                    <div>
                        <label for="image_url" style="font-weight: 500; font-size: 12px; color: #64748b;">OR Enter Image URL / Path</label>
                        <input type="text" id="image_url" name="image_url" class="form-control" value="{{ product.image_url if is_edit else '/static/images/p1.jpg' }}" placeholder="/static/images/p1.jpg">
                    </div>
                </div>
                {% if is_edit and product.image_url %}
                <div style="margin-top: 12px;">
                    <span style="font-size: 12px; color: #64748b;">Current Preview:</span><br>
                    <img src="{{ product.image_url }}" alt="Preview" style="height: 80px; border-radius: 6px; border: 1px solid var(--admin-border); margin-top: 4px;" onerror="this.src='/static/images/p1.jpg'">
                </div>
                {% endif %}
            </div>

            <div class="form-group" style="grid-column: 1 / -1; display: flex; gap: 24px; flex-wrap: wrap; padding: 12px 0;">
                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                    <input type="checkbox" name="is_active" {% if not is_edit or product.is_active %}checked{% endif %}>
                    <span>Visible in Store (Active)</span>
                </label>
                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                    <input type="checkbox" name="is_featured" {% if is_edit and product.is_featured %}checked{% endif %}>
                    <span>Feature on Homepage</span>
                </label>
                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                    <input type="checkbox" name="is_new_arrival" {% if is_edit and product.is_new_arrival %}checked{% endif %}>
                    <span>Mark as New Arrival</span>
                </label>
            </div>
        </div>

        <div style="display: flex; gap: 12px; justify-content: flex-end; margin-top: 20px; border-top: 1px solid var(--admin-border); padding-top: 20px;">
            <a href="{{ url_for('admin_products') }}" class="btn-admin-outline">Cancel</a>
            <button type="submit" class="btn-admin-accent">
                <i class="fa-solid fa-check"></i> {% if is_edit %}Save Changes{% else %}Publish Product{% endif %}
            </button>
        </div>
    </form>
</div>
{% endblock %}
"""

# 5. categories.html
ADMIN_CATEGORIES = """{% extends "admin/admin_base.html" %}
{% block title %}Categories | Admin Portal{% endblock %}
{% block page_title %}Product Categories{% endblock %}

{% block content %}
<div style="display: grid; grid-template-columns: 1fr 2fr; gap: 24px;">
    <!-- Add Category Form -->
    <div class="admin-card">
        <h3 class="card-title" style="margin-bottom: 16px;">
            <i class="fa-solid fa-folder-plus" style="color: var(--admin-accent);"></i> Add New Category
        </h3>
        <form method="POST" action="{{ url_for('admin_add_category') }}">
            <div class="form-group">
                <label for="cat_name">Category Name *</label>
                <input type="text" id="cat_name" name="name" class="form-control" required placeholder="e.g. Formal Wear">
            </div>
            <div class="form-group">
                <label for="cat_desc">Description (optional)</label>
                <textarea id="cat_desc" name="description" class="form-control" rows="3" placeholder="Category highlights..."></textarea>
            </div>
            <div class="form-group">
                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                    <input type="checkbox" name="is_active" checked>
                    <span>Active Category</span>
                </label>
            </div>
            <button type="submit" class="btn-admin-accent" style="width: 100%; justify-content: center;">
                <i class="fa-solid fa-plus"></i> Save Category
            </button>
        </form>
    </div>

    <!-- Categories List -->
    <div class="admin-card">
        <div class="card-header-flex">
            <div>
                <h3 class="card-title">Existing Categories ({{ categories|length }})</h3>
                <span class="card-subtitle">Manage store catalog taxonomy</span>
            </div>
        </div>

        <div class="table-responsive">
            <table class="admin-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Category Name</th>
                        <th>Description</th>
                        <th>Products Linked</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for cat in categories %}
                    <tr>
                        <td>#{{ cat.id }}</td>
                        <td><strong>{{ cat.name }}</strong></td>
                        <td>{{ cat.description or '-' }}</td>
                        <td>
                            <a href="{{ url_for('admin_products', category=cat.name) }}" class="status-badge" style="background:#e0f2fe; color:#0369a1; text-decoration:none;">
                                {{ category_counts.get(cat.name, 0) }} items
                            </a>
                        </td>
                        <td>
                            <span class="status-badge {% if cat.is_active %}active{% else %}inactive{% endif %}">
                                {% if cat.is_active %}Active{% else %}Inactive{% endif %}
                            </span>
                        </td>
                        <td>
                            <form method="POST" action="{{ url_for('admin_delete_category', category_id=cat.id) }}" onsubmit="return confirm('Are you sure you want to delete this category?');" style="display:inline;">
                                <button type="submit" class="btn-admin-outline btn-admin-danger btn-admin-sm">
                                    <i class="fa-solid fa-trash"></i>
                                </button>
                            </form>
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="6" style="text-align: center; padding: 30px; color: #94a3b8;">
                            No categories defined yet.
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
"""

# 6. orders.html
ADMIN_ORDERS = """{% extends "admin/admin_base.html" %}
{% block title %}Customer Orders | Admin Portal{% endblock %}
{% block page_title %}Customer Order Management{% endblock %}

{% block extra_head %}
<style>
    .order-status-tabs {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 20px;
    }

    .status-tab {
        padding: 8px 16px;
        border-radius: var(--radius-sm);
        font-size: 13px;
        font-weight: 600;
        text-decoration: none;
        background: var(--admin-card-bg);
        border: 1px solid var(--admin-border);
        color: var(--admin-text-main);
        transition: all 0.2s;
    }

    .status-tab:hover, .status-tab.active {
        background: var(--admin-secondary);
        color: #ffffff;
        border-color: var(--admin-secondary);
    }
</style>
{% endblock %}

{% block content %}
<!-- Filter Bar -->
<div class="admin-card" style="padding: 16px 20px; margin-bottom: 20px;">
    <form method="GET" action="{{ url_for('admin_orders') }}" style="display: flex; gap: 12px; flex-wrap: wrap; align-items: center;">
        <input type="text" name="query" class="form-control" style="max-width: 280px;" placeholder="Search Order ID, Name, Email, Phone..." value="{{ query }}">
        
        <select name="status" class="form-control" style="max-width: 180px;">
            <option value="">All Order Statuses</option>
            <option value="Pending" {% if status_filter == 'Pending' %}selected{% endif %}>Pending</option>
            <option value="Processing" {% if status_filter == 'Processing' %}selected{% endif %}>Processing</option>
            <option value="Shipped" {% if status_filter == 'Shipped' %}selected{% endif %}>Shipped</option>
            <option value="Delivered" {% if status_filter == 'Delivered' %}selected{% endif %}>Delivered</option>
            <option value="Cancelled" {% if status_filter == 'Cancelled' %}selected{% endif %}>Cancelled</option>
        </select>

        <select name="payment_status" class="form-control" style="max-width: 180px;">
            <option value="">All Payment Statuses</option>
            <option value="Paid" {% if payment_filter == 'Paid' %}selected{% endif %}>Paid</option>
            <option value="Pending" {% if payment_filter == 'Pending' %}selected{% endif %}>Pending</option>
            <option value="Failed" {% if payment_filter == 'Failed' %}selected{% endif %}>Failed</option>
            <option value="Refunded" {% if payment_filter == 'Refunded' %}selected{% endif %}>Refunded</option>
        </select>

        <button type="submit" class="btn-admin-primary btn-admin-sm">
            <i class="fa-solid fa-filter"></i> Filter Orders
        </button>

        {% if query or status_filter or payment_filter %}
        <a href="{{ url_for('admin_orders') }}" class="btn-admin-outline btn-admin-sm">
            <i class="fa-solid fa-xmark"></i> Clear
        </a>
        {% endif %}
    </form>
</div>

<div class="admin-card">
    <div class="card-header-flex">
        <div>
            <h3 class="card-title">All Customer Purchases ({{ pagination.total }})</h3>
            <span class="card-subtitle">Real-time order statuses & payment details</span>
        </div>
    </div>

    <div class="table-responsive">
        <table class="admin-table">
            <thead>
                <tr>
                    <th>Order #</th>
                    <th>Date & Time</th>
                    <th>Customer Name</th>
                    <th>Customer Contact</th>
                    <th>Items</th>
                    <th>Total Price</th>
                    <th>Payment Status</th>
                    <th>Order Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for order in orders %}
                <tr>
                    <td><strong>#FW-{{ order.id }}</strong></td>
                    <td>{{ order.date_ordered.strftime('%d %b %Y, %I:%M %p') if order.date_ordered else 'N/A' }}</td>
                    <td>
                        <a href="{{ url_for('admin_customer_detail', customer_id=order.user_id) }}" style="color: var(--admin-secondary); font-weight: 700; text-decoration: none;">
                            {{ order.first_name }} {{ order.last_name }}
                        </a>
                    </td>
                    <td>
                        <div><i class="fa-regular fa-envelope" style="color:#94a3b8;"></i> {{ order.user.email if order.user else 'N/A' }}</div>
                        {% if order.phone or (order.user and order.user.phone) %}
                        <div style="font-size: 12px; color: #64748b;"><i class="fa-solid fa-phone" style="color:#94a3b8;"></i> {{ order.phone or order.user.phone }}</div>
                        {% endif %}
                    </td>
                    <td>
                        <span class="status-badge" style="background:#f1f5f9; color:#334155;">{{ order.items|length }} item(s)</span>
                    </td>
                    <td><strong>₹{{ "{:,.2f}".format(order.total_price) }}</strong></td>
                    <td>
                        <span class="status-badge {{ order.payment_status|lower if order.payment_status else 'pending' }}">
                            {{ order.payment_status or 'Pending' }}
                        </span>
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase; margin-top: 2px;">{{ order.payment_method or 'Card/UPI' }}</div>
                    </td>
                    <td>
                        <span class="status-badge {{ order.status|lower }}">
                            {{ order.status }}
                        </span>
                    </td>
                    <td>
                        <div style="display: flex; gap: 6px;">
                            <a href="{{ url_for('admin_order_detail', order_id=order.id) }}" class="btn-admin-primary btn-admin-sm" title="Manage Order Details">
                                Manage <i class="fa-solid fa-chevron-right"></i>
                            </a>
                            <a href="{{ url_for('invoice', order_id=order.id) }}" target="_blank" class="btn-admin-outline btn-admin-sm" title="View Invoice">
                                <i class="fa-solid fa-file-invoice"></i>
                            </a>
                        </div>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="9" style="text-align: center; padding: 40px; color: #94a3b8;">
                        No orders found matching your search.
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- Pagination -->
    {% if pagination.pages > 1 %}
    <div class="pagination-container">
        <span style="font-size: 13px; color: #64748b;">Showing {{ orders|length }} of {{ pagination.total }} orders</span>
        <div class="pagination-links">
            {% if pagination.has_prev %}
            <a href="{{ url_for('admin_orders', page=pagination.prev_num, query=query, status=status_filter, payment_status=payment_filter) }}" class="page-link">&laquo; Prev</a>
            {% endif %}

            {% for p in pagination.iter_pages(left_edge=1, right_edge=1, left_current=2, right_current=2) %}
                {% if p %}
                    {% if p == pagination.page %}
                    <span class="page-link active">{{ p }}</span>
                    {% else %}
                    <a href="{{ url_for('admin_orders', page=p, query=query, status=status_filter, payment_status=payment_filter) }}" class="page-link">{{ p }}</a>
                    {% endif %}
                {% else %}
                    <span class="page-link disabled">...</span>
                {% endif %}
            {% endfor %}

            {% if pagination.has_next %}
            <a href="{{ url_for('admin_orders', page=pagination.next_num, query=query, status=status_filter, payment_status=payment_filter) }}" class="page-link">Next &raquo;</a>
            {% endif %}
        </div>
    </div>
    {% endif %}
</div>
{% endblock %}
"""

# 7. order_detail.html
ADMIN_ORDER_DETAIL = """{% extends "admin/admin_base.html" %}
{% block title %}Order #FW-{{ order.id }} | Admin Portal{% endblock %}
{% block page_title %}Order Details: #FW-{{ order.id }}{% endblock %}

{% block content %}
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; flex-wrap: wrap; gap: 12px;">
    <a href="{{ url_for('admin_orders') }}" class="btn-admin-outline">
        <i class="fa-solid fa-arrow-left"></i> Back to Orders
    </a>
    <div style="display: flex; gap: 10px;">
        <a href="{{ url_for('invoice', order_id=order.id) }}" target="_blank" class="btn-admin-outline">
            <i class="fa-solid fa-file-invoice"></i> View Invoice
        </a>
        <a href="{{ url_for('track_order', order_id=order.id) }}" target="_blank" class="btn-admin-outline">
            <i class="fa-solid fa-location-dot"></i> Live Tracking
        </a>
    </div>
</div>

<div style="display: grid; grid-template-columns: 2fr 1fr; gap: 24px;">
    <!-- Left Column: Items and Customer Info -->
    <div>
        <!-- Order Items -->
        <div class="admin-card">
            <h3 class="card-title" style="margin-bottom: 16px;">
                <i class="fa-solid fa-box-open" style="color: var(--admin-accent);"></i> Ordered Products ({{ order.items|length }})
            </h3>
            <div class="table-responsive">
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>Item</th>
                            <th>Product Name</th>
                            <th>Unit Price</th>
                            <th>Qty</th>
                            <th>Line Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in order.items %}
                        <tr>
                            <td>
                                <img src="{{ item.product.image_url }}" alt="{{ item.product.name }}" style="width: 44px; height: 52px; object-fit: cover; border-radius: 6px;" onerror="this.src='/static/images/p1.jpg'">
                            </td>
                            <td>
                                <strong>{{ item.product.name }}</strong>
                                <div style="font-size: 12px; color: #64748b;">Category: {{ item.product.category }}</div>
                            </td>
                            <td>₹{{ "{:,.2f}".format(item.price_at_order) }}</td>
                            <td><strong>x{{ item.quantity }}</strong></td>
                            <td><strong>₹{{ "{:,.2f}".format(item.price_at_order * item.quantity) }}</strong></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>

            <!-- Financial Breakdown -->
            <div style="margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--admin-border); display: flex; flex-direction: column; align-items: flex-end; gap: 8px;">
                <div style="display: flex; justify-content: space-between; width: 260px; font-size: 14px;">
                    <span style="color: #64748b;">Subtotal:</span>
                    <span>₹{{ "{:,.2f}".format(order.total_price) }}</span>
                </div>
                <div style="display: flex; justify-content: space-between; width: 260px; font-size: 14px;">
                    <span style="color: #64748b;">Shipping Fee:</span>
                    <span style="color: #15803d; font-weight: 600;">FREE</span>
                </div>
                <div style="display: flex; justify-content: space-between; width: 260px; font-size: 16px; font-weight: 800; border-top: 1px solid var(--admin-border); padding-top: 8px;">
                    <span>Grand Total:</span>
                    <span style="color: var(--admin-secondary);">₹{{ "{:,.2f}".format(order.total_price) }}</span>
                </div>
            </div>
        </div>

        <!-- Customer & Shipping Information -->
        <div class="admin-card">
            <h3 class="card-title" style="margin-bottom: 16px;">
                <i class="fa-solid fa-truck-ramp-box" style="color: var(--admin-accent);"></i> Delivery & Customer Profile
            </h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h4 style="font-size: 13px; color: #64748b; margin-bottom: 6px; text-transform: uppercase;">Customer Details</h4>
                    <p style="font-size: 14px; font-weight: 700;">{{ order.first_name }} {{ order.last_name }}</p>
                    <p style="font-size: 13px; color: #64748b; margin-top: 4px;"><i class="fa-regular fa-envelope"></i> {{ order.user.email if order.user else 'N/A' }}</p>
                    <p style="font-size: 13px; color: #64748b;"><i class="fa-solid fa-phone"></i> {{ order.phone or (order.user.phone if order.user else 'N/A') }}</p>
                    <p style="margin-top: 8px;">
                        <a href="{{ url_for('admin_customer_detail', customer_id=order.user_id) }}" class="btn-admin-outline btn-admin-sm">
                            <i class="fa-solid fa-clock-rotate-left"></i> View Full Customer History
                        </a>
                    </p>
                </div>
                <div>
                    <h4 style="font-size: 13px; color: #64748b; margin-bottom: 6px; text-transform: uppercase;">Shipping Destination</h4>
                    <p style="font-size: 14px; font-weight: 600;">{{ order.address or 'Standard Shipping Address' }}</p>
                    <p style="font-size: 13px; color: #64748b;">{{ order.city }}, {{ order.state }} - {{ order.zip_code }}</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Right Column: Status & Fulfillment Controls -->
    <div>
        <div class="admin-card">
            <h3 class="card-title" style="margin-bottom: 16px;">
                <i class="fa-solid fa-sliders" style="color: var(--admin-accent);"></i> Fulfillment Controls
            </h3>
            
            <form method="POST" action="{{ url_for('admin_update_order_status', order_id=order.id) }}">
                <div class="form-group">
                    <label for="status">Order Fulfillment Status</label>
                    <select name="status" id="status" class="form-control">
                        <option value="Pending" {% if order.status == 'Pending' %}selected{% endif %}>Pending</option>
                        <option value="Processing" {% if order.status == 'Processing' %}selected{% endif %}>Processing</option>
                        <option value="Shipped" {% if order.status == 'Shipped' %}selected{% endif %}>Shipped</option>
                        <option value="Delivered" {% if order.status == 'Delivered' %}selected{% endif %}>Delivered</option>
                        <option value="Cancelled" {% if order.status == 'Cancelled' %}selected{% endif %}>Cancelled</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="payment_status">Payment Status</label>
                    <select name="payment_status" id="payment_status" class="form-control">
                        <option value="Pending" {% if order.payment_status == 'Pending' %}selected{% endif %}>Pending</option>
                        <option value="Paid" {% if order.payment_status == 'Paid' %}selected{% endif %}>Paid</option>
                        <option value="Failed" {% if order.payment_status == 'Failed' %}selected{% endif %}>Failed</option>
                        <option value="Refunded" {% if order.payment_status == 'Refunded' %}selected{% endif %}>Refunded</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="tracking_number">Tracking / Consignment #</label>
                    <input type="text" id="tracking_number" name="tracking_number" class="form-control" value="{{ order.tracking_number or '' }}" placeholder="e.g. BLUEDART-8938210">
                </div>

                <button type="submit" class="btn-admin-accent" style="width: 100%; justify-content: center; margin-top: 10px;">
                    <i class="fa-solid fa-floppy-disk"></i> Update Order & Notify Customer
                </button>
            </form>
        </div>

        <!-- Payment Meta -->
        <div class="admin-card">
            <h3 class="card-title" style="margin-bottom: 16px;">
                <i class="fa-solid fa-credit-card" style="color: var(--admin-accent);"></i> Payment Transaction
            </h3>
            <div style="font-size: 13px; display: flex; flex-direction: column; gap: 8px;">
                <div>
                    <span style="color: #64748b;">Gateway:</span>
                    <strong style="text-transform: uppercase;">{{ order.payment_method or 'Razorpay / Stripe' }}</strong>
                </div>
                <div>
                    <span style="color: #64748b;">Transaction ID:</span>
                    <div style="font-family: monospace; background: #f1f5f9; padding: 4px 8px; border-radius: 4px; word-break: break-all; margin-top: 2px;">
                        {{ order.payment_id or 'TXN_FW_DIRECT' }}
                    </div>
                </div>
                {% if order.payment_signature %}
                <div>
                    <span style="color: #64748b;">Signature:</span>
                    <div style="font-family: monospace; font-size: 11px; background: #f1f5f9; padding: 4px 8px; border-radius: 4px; word-break: break-all; margin-top: 2px;">
                        {{ order.payment_signature }}
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

# 8. customers.html
ADMIN_CUSTOMERS = """{% extends "admin/admin_base.html" %}
{% block title %}Customer Directory | Admin Portal{% endblock %}
{% block page_title %}Customer Directory & Spend Analytics{% endblock %}

{% block content %}
<div class="admin-card" style="padding: 16px 20px; margin-bottom: 20px;">
    <form method="GET" action="{{ url_for('admin_customers') }}" style="display: flex; gap: 12px; flex-wrap: wrap; align-items: center;">
        <input type="text" name="query" class="form-control" style="max-width: 320px;" placeholder="Search by name, email or phone..." value="{{ query }}">
        <button type="submit" class="btn-admin-primary btn-admin-sm">
            <i class="fa-solid fa-magnifying-glass"></i> Search Customers
        </button>
        {% if query %}
        <a href="{{ url_for('admin_customers') }}" class="btn-admin-outline btn-admin-sm">Clear</a>
        {% endif %}
    </form>
</div>

<div class="admin-card">
    <div class="card-header-flex">
        <div>
            <h3 class="card-title">Registered Customer Accounts ({{ pagination.total }})</h3>
            <span class="card-subtitle">Track lifetime orders and purchases by customer</span>
        </div>
    </div>

    <div class="table-responsive">
        <table class="admin-table">
            <thead>
                <tr>
                    <th>Customer</th>
                    <th>Email Address</th>
                    <th>Phone</th>
                    <th>Auth Method</th>
                    <th>Total Orders</th>
                    <th>Lifetime Spent</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {% for customer in customers %}
                <tr>
                    <td>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div class="admin-avatar" style="width: 32px; height: 32px; font-size: 12px;">
                                {{ customer.username[0]|upper }}
                            </div>
                            <div>
                                <strong>{{ customer.first_name ~ ' ' ~ customer.last_name if customer.first_name else customer.username }}</strong>
                                <div style="font-size: 11px; color: #64748b;">@{{ customer.username }}</div>
                            </div>
                        </div>
                    </td>
                    <td>{{ customer.email }}</td>
                    <td>{{ customer.phone or 'N/A' }}</td>
                    <td>
                        <span class="status-badge" style="background:#f1f5f9; color:#334155; text-transform: uppercase;">
                            {{ customer.auth_provider or 'Local' }}
                        </span>
                    </td>
                    <td>
                        <strong>{{ customer_order_counts.get(customer.id, 0) }}</strong> orders
                    </td>
                    <td>
                        <strong style="color: #15803d;">₹{{ "{:,.2f}".format(customer_spend_totals.get(customer.id, 0.0)) }}</strong>
                    </td>
                    <td>
                        <a href="{{ url_for('admin_customer_detail', customer_id=customer.id) }}" class="btn-admin-primary btn-admin-sm">
                            <i class="fa-solid fa-bag-shopping"></i> View Purchases
                        </a>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="7" style="text-align: center; padding: 30px; color: #94a3b8;">
                        No customer accounts found.
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- Pagination -->
    {% if pagination.pages > 1 %}
    <div class="pagination-container">
        <span style="font-size: 13px; color: #64748b;">Showing {{ customers|length }} of {{ pagination.total }} customers</span>
        <div class="pagination-links">
            {% if pagination.has_prev %}
            <a href="{{ url_for('admin_customers', page=pagination.prev_num, query=query) }}" class="page-link">&laquo; Prev</a>
            {% endif %}

            {% for p in pagination.iter_pages(left_edge=1, right_edge=1, left_current=2, right_current=2) %}
                {% if p %}
                    {% if p == pagination.page %}
                    <span class="page-link active">{{ p }}</span>
                    {% else %}
                    <a href="{{ url_for('admin_customers', page=p, query=query) }}" class="page-link">{{ p }}</a>
                    {% endif %}
                {% else %}
                    <span class="page-link disabled">...</span>
                {% endif %}
            {% endfor %}

            {% if pagination.has_next %}
            <a href="{{ url_for('admin_customers', page=pagination.next_num, query=query) }}" class="page-link">Next &raquo;</a>
            {% endif %}
        </div>
    </div>
    {% endif %}
</div>
{% endblock %}
"""

# 9. customer_detail.html
ADMIN_CUSTOMER_DETAIL = """{% extends "admin/admin_base.html" %}
{% block title %}Customer Purchases: {{ customer.username }} | Admin Portal{% endblock %}
{% block page_title %}Customer Purchase History{% endblock %}

{% block content %}
<div style="margin-bottom: 20px;">
    <a href="{{ url_for('admin_customers') }}" class="btn-admin-outline">
        <i class="fa-solid fa-arrow-left"></i> Back to Customer Directory
    </a>
</div>

<!-- Customer Profile Summary -->
<div class="admin-card" style="margin-bottom: 24px;">
    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 20px;">
        <div style="display: flex; align-items: center; gap: 16px;">
            <div class="admin-avatar" style="width: 60px; height: 60px; font-size: 24px;">
                {{ customer.username[0]|upper }}
            </div>
            <div>
                <h2 style="font-size: 20px; font-weight: 800; color: var(--admin-secondary);">
                    {{ customer.first_name ~ ' ' ~ customer.last_name if customer.first_name else customer.username }}
                </h2>
                <div style="font-size: 13px; color: #64748b; margin-top: 4px;">
                    <span><i class="fa-regular fa-envelope"></i> {{ customer.email }}</span>
                    <span style="margin: 0 8px;">•</span>
                    <span><i class="fa-solid fa-phone"></i> {{ customer.phone or 'No phone registered' }}</span>
                    <span style="margin: 0 8px;">•</span>
                    <span>Auth: <strong>{{ customer.auth_provider|upper if customer.auth_provider else 'LOCAL' }}</strong></span>
                </div>
            </div>
        </div>

        <div style="display: flex; gap: 24px;">
            <div style="text-align: right;">
                <span style="font-size: 12px; color: #64748b; text-transform: uppercase; font-weight: 600;">Total Orders</span>
                <div style="font-size: 22px; font-weight: 800; color: var(--admin-secondary);">{{ orders|length }}</div>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 12px; color: #64748b; text-transform: uppercase; font-weight: 600;">Lifetime Spend</span>
                <div style="font-size: 22px; font-weight: 800; color: #15803d;">₹{{ "{:,.2f}".format(total_spent) }}</div>
            </div>
        </div>
    </div>
</div>

<!-- Order History List ("Which customer purchased what") -->
<div class="admin-card">
    <div class="card-header-flex">
        <div>
            <h3 class="card-title"><i class="fa-solid fa-receipt" style="color: var(--admin-accent);"></i> All Purchases Made by {{ customer.username }}</h3>
            <span class="card-subtitle">Chronological list of all items ordered by this customer</span>
        </div>
    </div>

    {% for order in orders %}
    <div style="border: 1px solid var(--admin-border); border-radius: var(--radius-sm); margin-bottom: 20px; overflow: hidden;">
        <!-- Order Header -->
        <div style="background: #f8fafc; padding: 14px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--admin-border); flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; align-items: center; gap: 14px;">
                <strong>Order #FW-{{ order.id }}</strong>
                <span style="font-size: 13px; color: #64748b;">{{ order.date_ordered.strftime('%d %b %Y, %I:%M %p') if order.date_ordered else 'N/A' }}</span>
                <span class="status-badge {{ order.status|lower }}">{{ order.status }}</span>
                <span class="status-badge {{ order.payment_status|lower if order.payment_status else 'pending' }}">{{ order.payment_status or 'Pending' }}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 14px;">
                <span style="font-size: 16px; font-weight: 800; color: var(--admin-secondary);">₹{{ "{:,.2f}".format(order.total_price) }}</span>
                <a href="{{ url_for('admin_order_detail', order_id=order.id) }}" class="btn-admin-outline btn-admin-sm">
                    Manage Order <i class="fa-solid fa-chevron-right"></i>
                </a>
            </div>
        </div>

        <!-- Purchased Line Items -->
        <div style="padding: 16px 20px;">
            <div class="table-responsive">
                <table class="admin-table" style="margin: 0;">
                    <thead>
                        <tr>
                            <th>Item Image</th>
                            <th>Product Name</th>
                            <th>Category</th>
                            <th>Price At Order</th>
                            <th>Quantity</th>
                            <th>Subtotal</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in order.items %}
                        <tr>
                            <td style="width: 60px;">
                                <img src="{{ item.product.image_url }}" alt="{{ item.product.name }}" style="width: 40px; height: 48px; object-fit: cover; border-radius: 4px;" onerror="this.src='/static/images/p1.jpg'">
                            </td>
                            <td>
                                <strong>{{ item.product.name }}</strong>
                            </td>
                            <td>{{ item.product.category }}</td>
                            <td>₹{{ "{:,.2f}".format(item.price_at_order) }}</td>
                            <td><strong>x{{ item.quantity }}</strong></td>
                            <td><strong>₹{{ "{:,.2f}".format(item.price_at_order * item.quantity) }}</strong></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    {% else %}
    <div style="text-align: center; padding: 40px; color: #94a3b8;">
        This customer has not placed any orders yet.
    </div>
    {% endfor %}
</div>
{% endblock %}
"""

# 10. analytics.html
ADMIN_ANALYTICS = """{% extends "admin/admin_base.html" %}
{% block title %}Sales Analytics | Admin Portal{% endblock %}
{% block page_title %}Store Sales & Revenue Analytics{% endblock %}

{% block content %}
<!-- Top KPI Summary Cards -->
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 24px;">
    <div class="admin-card" style="margin: 0; padding: 18px;">
        <span style="font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase;">Total Gross Sales</span>
        <div style="font-size: 22px; font-weight: 800; color: var(--admin-secondary); margin-top: 4px;">₹{{ "{:,.2f}".format(total_sales) }}</div>
    </div>
    <div class="admin-card" style="margin: 0; padding: 18px;">
        <span style="font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase;">Average Order Value</span>
        <div style="font-size: 22px; font-weight: 800; color: #0369a1; margin-top: 4px;">₹{{ "{:,.2f}".format(avg_order_value) }}</div>
    </div>
    <div class="admin-card" style="margin: 0; padding: 18px;">
        <span style="font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase;">Total Units Sold</span>
        <div style="font-size: 22px; font-weight: 800; color: #7e22ce; margin-top: 4px;">{{ total_units_sold }} items</div>
    </div>
    <div class="admin-card" style="margin: 0; padding: 18px;">
        <span style="font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase;">Conversion Rate</span>
        <div style="font-size: 22px; font-weight: 800; color: #15803d; margin-top: 4px;">100% Verified</div>
    </div>
</div>

<!-- Charts Grid -->
<div style="display: grid; grid-template-columns: 2fr 1fr; gap: 24px; margin-bottom: 24px;">
    <div class="admin-card">
        <h3 class="card-title" style="margin-bottom: 16px;">
            <i class="fa-solid fa-chart-line" style="color: var(--admin-accent);"></i> Monthly Revenue Performance
        </h3>
        <div style="height: 300px; position: relative;">
            <canvas id="monthlySalesChart"></canvas>
        </div>
    </div>

    <div class="admin-card">
        <h3 class="card-title" style="margin-bottom: 16px;">
            <i class="fa-solid fa-pie-chart" style="color: var(--admin-accent);"></i> Sales by Category
        </h3>
        <div style="height: 300px; position: relative;">
            <canvas id="categorySalesChart"></canvas>
        </div>
    </div>
</div>

<!-- Top Products and Top Customers -->
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
    <!-- Top Selling Products -->
    <div class="admin-card">
        <h3 class="card-title" style="margin-bottom: 16px;">
            <i class="fa-solid fa-crown" style="color: var(--admin-accent);"></i> Top Selling Products
        </h3>
        <div class="table-responsive">
            <table class="admin-table">
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Units Sold</th>
                        <th>Revenue</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in top_products %}
                    <tr>
                        <td><strong>{{ item.name }}</strong></td>
                        <td><span class="status-badge active">{{ item.units }} sold</span></td>
                        <td><strong>₹{{ "{:,.2f}".format(item.revenue) }}</strong></td>
                    </tr>
                    {% else %}
                    <tr><td colspan="3" style="text-align: center; color: #94a3b8;">No purchase data yet.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Top High-Value Customers -->
    <div class="admin-card">
        <h3 class="card-title" style="margin-bottom: 16px;">
            <i class="fa-solid fa-trophy" style="color: var(--admin-accent);"></i> Top Customers by Spend
        </h3>
        <div class="table-responsive">
            <table class="admin-table">
                <thead>
                    <tr>
                        <th>Customer</th>
                        <th>Orders</th>
                        <th>Total Spent</th>
                    </tr>
                </thead>
                <tbody>
                    {% for cust in top_customers %}
                    <tr>
                        <td>
                            <strong>{{ cust.name }}</strong>
                            <div style="font-size: 11px; color: #64748b;">{{ cust.email }}</div>
                        </td>
                        <td>{{ cust.orders }}</td>
                        <td><strong style="color: #15803d;">₹{{ "{:,.2f}".format(cust.spent) }}</strong></td>
                    </tr>
                    {% else %}
                    <tr><td colspan="3" style="text-align: center; color: #94a3b8;">No customer purchase data yet.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_scripts %}
<script>
    // Monthly Sales Chart
    const monthlyCtx = document.getElementById('monthlySalesChart').getContext('2d');
    const monthlyData = {{ monthly_chart_data|tojson }};
    new Chart(monthlyCtx, {
        type: 'bar',
        data: {
            labels: monthlyData.labels,
            datasets: [{
                label: 'Revenue (₹)',
                data: monthlyData.values,
                backgroundColor: '#1e293b',
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { callback: function(val) { return '₹' + val.toLocaleString(); } }
                }
            }
        }
    });

    // Category Sales Chart
    const catCtx = document.getElementById('categorySalesChart').getContext('2d');
    const catData = {{ category_chart_data|tojson }};
    new Chart(catCtx, {
        type: 'doughnut',
        data: {
            labels: catData.labels,
            datasets: [{
                data: catData.values,
                backgroundColor: ['#c5a880', '#1e293b', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
</script>
{% endblock %}
"""

# 11. low_stock.html
ADMIN_LOW_STOCK = """{% extends "admin/admin_base.html" %}
{% block title %}Stock Alerts | Admin Portal{% endblock %}
{% block page_title %}Low Stock & Inventory Monitoring{% endblock %}

{% block content %}
<div class="admin-card" style="border-left: 4px solid var(--admin-warning);">
    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
        <div>
            <h3 style="font-size: 16px; font-weight: 700; color: #92400e;">
                <i class="fa-solid fa-triangle-exclamation"></i> Critical Inventory Warning
            </h3>
            <p style="font-size: 13px; color: #b45309; margin-top: 4px;">
                The items listed below have low or zero stock. Replenish inventory promptly to prevent missed customer sales.
            </p>
        </div>
        <a href="{{ url_for('admin_products') }}" class="btn-admin-outline btn-admin-sm">
            View All Products
        </a>
    </div>
</div>

<div class="admin-card">
    <div class="card-header-flex">
        <div>
            <h3 class="card-title">Low / Out-of-Stock Items ({{ low_stock_items|length }})</h3>
            <span class="card-subtitle">Items with stock count <= 5</span>
        </div>
    </div>

    <div class="table-responsive">
        <table class="admin-table">
            <thead>
                <tr>
                    <th>Item</th>
                    <th>Product Name</th>
                    <th>Category</th>
                    <th>Price</th>
                    <th>Current Stock</th>
                    <th>Quick Update Stock</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {% for product in low_stock_items %}
                <tr>
                    <td>
                        <img src="{{ product.image_url }}" alt="{{ product.name }}" style="width: 44px; height: 52px; object-fit: cover; border-radius: 6px;" onerror="this.src='/static/images/p1.jpg'">
                    </td>
                    <td><strong>{{ product.name }}</strong></td>
                    <td><span class="status-badge" style="background:#f1f5f9; color:#334155;">{{ product.category }}</span></td>
                    <td>₹{{ "{:,.2f}".format(product.price) }}</td>
                    <td>
                        {% if product.stock <= 0 %}
                        <span class="status-badge out-of-stock">0 (Out of Stock)</span>
                        {% else %}
                        <span class="status-badge low-stock">{{ product.stock }} units left</span>
                        {% endif %}
                    </td>
                    <td>
                        <form method="POST" action="{{ url_for('admin_quick_stock_update', product_id=product.id) }}" style="display: flex; gap: 6px; align-items: center;">
                            <input type="number" name="new_stock" value="{{ product.stock }}" min="0" class="form-control" style="width: 80px; padding: 4px 8px; font-size: 13px;">
                            <button type="submit" class="btn-admin-primary btn-admin-sm">
                                <i class="fa-solid fa-check"></i>
                            </button>
                        </form>
                    </td>
                    <td>
                        <a href="{{ url_for('admin_edit_product', product_id=product.id) }}" class="btn-admin-outline btn-admin-sm">
                            Edit Full Item <i class="fa-solid fa-pen-to-square"></i>
                        </a>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="7" style="text-align: center; padding: 40px; color: #15803d; font-weight: 600;">
                        <i class="fa-solid fa-circle-check" style="font-size: 24px; display: block; margin-bottom: 8px;"></i>
                        All catalog products are healthy with adequate stock levels!
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
"""

# 12. account_settings.html
ADMIN_ACCOUNT_SETTINGS = """{% extends "admin/admin_base.html" %}
{% block title %}Admin Account Settings | Admin Portal{% endblock %}
{% block page_title %}Admin Account & Security Settings{% endblock %}

{% block extra_head %}
<style>
    .settings-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 24px;
        align-items: start;
    }

    .settings-full-width {
        grid-column: 1 / -1;
    }

    .settings-card {
        background: var(--admin-card-bg);
        border: 1px solid var(--admin-border);
        border-radius: var(--radius-md);
        padding: 24px;
        box-shadow: var(--shadow-sm);
    }

    .settings-card-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 20px;
        padding-bottom: 14px;
        border-bottom: 1px solid var(--admin-border);
    }

    .settings-card-icon {
        width: 42px;
        height: 42px;
        border-radius: var(--radius-sm);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
    }

    .icon-profile { background: #e0f2fe; color: #0369a1; }
    .icon-email { background: #fef3c7; color: #b45309; }
    .icon-security { background: #fee2e2; color: #b91c1c; }

    .settings-card-title {
        font-size: 16px;
        font-weight: 700;
        color: var(--admin-secondary);
    }

    .settings-card-desc {
        font-size: 12.5px;
        color: var(--admin-text-muted);
        margin-top: 2px;
    }

    .password-wrapper {
        position: relative;
    }

    .password-wrapper input {
        padding-right: 44px;
    }

    .password-toggle-btn {
        position: absolute;
        right: 12px;
        top: 50%;
        transform: translateY(-50%);
        background: none;
        border: none;
        color: #94a3b8;
        cursor: pointer;
        font-size: 16px;
        padding: 4px;
    }

    .password-toggle-btn:hover {
        color: var(--admin-secondary);
    }

    .info-notice-box {
        background: #f8fafc;
        border-left: 3px solid var(--admin-accent);
        padding: 12px 16px;
        border-radius: 4px;
        font-size: 12.5px;
        color: #475569;
        margin-bottom: 18px;
        display: flex;
        gap: 10px;
        align-items: flex-start;
    }

    .info-notice-box.warning {
        background: #fffbeb;
        border-left-color: var(--admin-warning);
        color: #92400e;
    }

    .badge-super-admin {
        background: #dcfce7;
        color: #15803d;
        font-size: 11px;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 12px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }

    @media (max-width: 1024px) {
        .settings-grid {
            grid-template-columns: 1fr;
        }
    }
</style>
{% endblock %}

{% block content %}
<div class="settings-grid">

    <!-- Section 1: Admin Profile Details -->
    <div class="settings-card settings-full-width">
        <div class="settings-card-header">
            <div class="settings-card-icon icon-profile">
                <i class="fa-solid fa-user-gear"></i>
            </div>
            <div>
                <h3 class="settings-card-title">Administrator Profile</h3>
                <p class="settings-card-desc">Manage administrative identity and contact information</p>
            </div>
            <div style="margin-left: auto;">
                <span class="badge-super-admin">
                    <i class="fa-solid fa-shield-halved"></i> Super Administrator
                </span>
            </div>
        </div>

        <form method="POST" action="{{ url_for('admin_update_profile') }}">
            <div class="form-grid">
                <div class="form-group">
                    <label for="username">Admin Username / Display Name *</label>
                    <input type="text" id="username" name="username" class="form-control" required value="{{ current_user.username }}" placeholder="Admin">
                </div>

                <div class="form-group">
                    <label for="current_email_display">Primary Login Email (Verified)</label>
                    <input type="text" id="current_email_display" class="form-control" value="{{ current_user.email }}" readonly style="background: #f1f5f9; color: #64748b; cursor: not-allowed;">
                </div>

                <div class="form-group">
                    <label for="first_name">First Name</label>
                    <input type="text" id="first_name" name="first_name" class="form-control" value="{{ current_user.first_name or '' }}" placeholder="e.g. John">
                </div>

                <div class="form-group">
                    <label for="last_name">Last Name</label>
                    <input type="text" id="last_name" name="last_name" class="form-control" value="{{ current_user.last_name or '' }}" placeholder="e.g. Doe">
                </div>

                <div class="form-group">
                    <label for="phone">Contact Phone</label>
                    <input type="text" id="phone" name="phone" class="form-control" value="{{ current_user.phone or '' }}" placeholder="e.g. +91 9876543210">
                </div>

                <div class="form-group">
                    <label>Account Registration Date</label>
                    <input type="text" class="form-control" value="{{ current_user.created_at.strftime('%d %B %Y, %I:%M %p') if current_user.created_at else 'Active' }}" readonly style="background: #f1f5f9; color: #64748b; cursor: not-allowed;">
                </div>
            </div>

            <div style="display: flex; justify-content: flex-end; margin-top: 10px;">
                <button type="submit" class="btn-admin-primary">
                    <i class="fa-solid fa-floppy-disk"></i> Save Profile Details
                </button>
            </div>
        </form>
    </div>

    <!-- Section 2: Change Administrator Email -->
    <div class="settings-card">
        <div class="settings-card-header">
            <div class="settings-card-icon icon-email">
                <i class="fa-solid fa-envelope"></i>
            </div>
            <div>
                <h3 class="settings-card-title">Change Admin Email</h3>
                <p class="settings-card-desc">Update your primary administrator login email address</p>
            </div>
        </div>

        <div class="info-notice-box">
            <i class="fa-solid fa-circle-info" style="margin-top: 2px; color: var(--admin-accent);"></i>
            <div>
                Updating your email address changes your primary sign-in credential immediately. Current security password is required.
            </div>
        </div>

        <form method="POST" action="{{ url_for('admin_change_email') }}">
            <div class="form-group">
                <label for="current_email_info">Current Registered Email</label>
                <input type="email" id="current_email_info" class="form-control" value="{{ current_user.email }}" readonly style="background: #f1f5f9; color: #64748b; cursor: not-allowed;">
            </div>

            <div class="form-group">
                <label for="new_email">New Email Address *</label>
                <input type="email" id="new_email" name="new_email" class="form-control" required placeholder="newadmin@fashionworld.pro" autocomplete="email">
            </div>

            <div class="form-group">
                <label for="confirm_new_email">Confirm New Email Address *</label>
                <input type="email" id="confirm_new_email" name="confirm_new_email" class="form-control" required placeholder="Re-enter new email" autocomplete="email">
            </div>

            <div class="form-group">
                <label for="email_current_password">Current Security Password *</label>
                <div class="password-wrapper">
                    <input type="password" id="email_current_password" name="current_password" class="form-control" required placeholder="Enter your current password" autocomplete="current-password">
                    <button type="button" class="password-toggle-btn" onclick="togglePasswordVisibility('email_current_password', this)">
                        <i class="fa-regular fa-eye"></i>
                    </button>
                </div>
            </div>

            <button type="submit" class="btn-admin-accent" style="width: 100%; justify-content: center; margin-top: 10px;">
                <i class="fa-solid fa-circle-check"></i> Update Admin Email
            </button>
        </form>
    </div>

    <!-- Section 3: Change Administrator Password -->
    <div class="settings-card">
        <div class="settings-card-header">
            <div class="settings-card-icon icon-security">
                <i class="fa-solid fa-key"></i>
            </div>
            <div>
                <h3 class="settings-card-title">Change Security Password</h3>
                <p class="settings-card-desc">Update your administrator access password securely</p>
            </div>
        </div>

        <div class="info-notice-box warning">
            <i class="fa-solid fa-triangle-exclamation" style="margin-top: 2px;"></i>
            <div>
                For maximum security, changing your password will invalidate the current session and require you to authenticate again.
            </div>
        </div>

        <form method="POST" action="{{ url_for('admin_change_password') }}">
            <div class="form-group">
                <label for="pwd_current">Current Security Password *</label>
                <div class="password-wrapper">
                    <input type="password" id="pwd_current" name="current_password" class="form-control" required placeholder="Enter current password" autocomplete="current-password">
                    <button type="button" class="password-toggle-btn" onclick="togglePasswordVisibility('pwd_current', this)">
                        <i class="fa-regular fa-eye"></i>
                    </button>
                </div>
            </div>

            <div class="form-group">
                <label for="pwd_new">New Password (Min 6 Characters) *</label>
                <div class="password-wrapper">
                    <input type="password" id="pwd_new" name="new_password" class="form-control" required minlength="6" placeholder="Enter strong new password" autocomplete="new-password">
                    <button type="button" class="password-toggle-btn" onclick="togglePasswordVisibility('pwd_new', this)">
                        <i class="fa-regular fa-eye"></i>
                    </button>
                </div>
            </div>

            <div class="form-group">
                <label for="pwd_confirm">Confirm New Password *</label>
                <div class="password-wrapper">
                    <input type="password" id="pwd_confirm" name="confirm_new_password" class="form-control" required minlength="6" placeholder="Re-type new password" autocomplete="new-password">
                    <button type="button" class="password-toggle-btn" onclick="togglePasswordVisibility('pwd_confirm', this)">
                        <i class="fa-regular fa-eye"></i>
                    </button>
                </div>
            </div>

            <button type="submit" class="btn-admin-primary" style="width: 100%; justify-content: center; margin-top: 10px; background: #0f172a;">
                <i class="fa-solid fa-lock"></i> Change Password & Re-authenticate
            </button>
        </form>
    </div>

</div>
{% endblock %}

{% block extra_scripts %}
<script>
function togglePasswordVisibility(fieldId, btn) {
    const input = document.getElementById(fieldId);
    const icon = btn.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'fa-regular fa-eye-slash';
    } else {
        input.type = 'password';
        icon.className = 'fa-regular fa-eye';
    }
}
</script>
{% endblock %}
"""

# Write all templates
files = {
    'admin_base.html': ADMIN_BASE,
    'dashboard.html': ADMIN_DASHBOARD,
    'products.html': ADMIN_PRODUCTS,
    'product_form.html': ADMIN_PRODUCT_FORM,
    'categories.html': ADMIN_CATEGORIES,
    'orders.html': ADMIN_ORDERS,
    'order_detail.html': ADMIN_ORDER_DETAIL,
    'customers.html': ADMIN_CUSTOMERS,
    'customer_detail.html': ADMIN_CUSTOMER_DETAIL,
    'analytics.html': ADMIN_ANALYTICS,
    'low_stock.html': ADMIN_LOW_STOCK,
    'account_settings.html': ADMIN_ACCOUNT_SETTINGS
}

for filename, html_content in files.items():
    filepath = os.path.join(TEMPLATES_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Successfully generated: {filepath}")

print("All admin templates created successfully!")


