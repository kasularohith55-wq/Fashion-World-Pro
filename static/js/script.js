// Smooth Scroll for Navigation
document.addEventListener('DOMContentLoaded', () => {
    const legacyNav = document.querySelector('nav.legacy-nav');
    
    // Legacy Navbar scroll effect (only if legacy nav is on page)
    if (legacyNav) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                legacyNav.style.padding = '15px 8%';
                legacyNav.style.background = 'rgba(255, 255, 255, 0.95)';
                legacyNav.style.boxShadow = '0 5px 20px rgba(0,0,0,0.05)';
            } else {
                legacyNav.style.padding = '20px 8%';
                legacyNav.style.background = 'rgba(255, 255, 255, 0.85)';
                legacyNav.style.boxShadow = 'none';
            }
        });
    }

    // Simple fade-in animation using Intersection Observer
    const observerOptions = {
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    document.querySelectorAll('.product-card').forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'all 0.6s ease-out';
        observer.observe(card);
    });

    // --- REAL-TIME FEATURES (Socket.io) ---
    if (typeof io !== 'undefined') {
        const socket = io();

        socket.on('connect', () => {
            console.log('Connected to Fashion World Pro Real-time Engine');
            if (CURRENT_USER_ID) {
                socket.emit('join', { user_id: CURRENT_USER_ID });
                socket.emit('request_cart_sync', { user_id: CURRENT_USER_ID });
            }
        });

        // Real-time Cart Sync
        socket.on('cart_updated', (data) => {
            const cartBadges = document.querySelectorAll('#cartCountBadge, .cart-badge, .cart-count-pill');
            cartBadges.forEach(badge => {
                badge.textContent = data.count;
                badge.style.animation = 'none';
                void badge.offsetWidth; // trigger reflow
                badge.style.animation = 'pop 0.3s ease';
            });
            
            const cartLink = document.querySelector('nav .nav-links a[href*="/cart"]');
            if (cartLink && !document.getElementById('cartCountBadge')) {
                cartLink.innerHTML = `Cart <i class="fa fa-shopping-bag"></i> <span class="cart-badge">${data.count}</span>`;
            }
            
            if (data.action === 'add') {
                showToast(`${data.product_name || 'Item'} added to cart!`);
            }
        });

        // Live Order Status Updates
        socket.on('order_status_updated', (data) => {
            showToast(`🔔 ${data.message}`);
            
            // If user is on the tracking page, update the UI live
            const stepTitle = document.querySelector(`.progress-step[data-status="${data.status}"]`);
            if (stepTitle) {
                document.querySelectorAll('.progress-step').forEach(s => s.classList.remove('active'));
                stepTitle.classList.add('active');
                
                const statusText = document.querySelector('.current-status-badge');
                if (statusText) {
                    statusText.innerText = data.status;
                }
            }
        });

        // Live Delivery Update (for map)
        socket.on('delivery_update', (data) => {
             // This will be handled in live_tracking.html primarily, 
             // but we can log it here.
             window.dispatchEvent(new CustomEvent('delivery_move', { detail: data }));
        });
    }
});

// AJAX Add to Cart / Wishlist
document.addEventListener('click', async (e) => {
    if (e.target.closest('.ajax-add')) {
        e.preventDefault();
        const link = e.target.closest('.ajax-add');
        const url = link.href;
        
        try {
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            
            // For now, since we're using flash messages and redirects, 
            // we'll just show a toast if the response is ok.
            // A more advanced version would return JSON.
            if (response.ok) {
                showToast("Action successful!");
                // Update cart count if needed
            }
        } catch (err) {
            console.error(err);
        }
    }
});

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.innerHTML = `
        <div style="background: #121212; color: #fff; padding: 15px 30px; border-radius: 5px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); font-size: 0.8rem; letter-spacing: 1px; text-transform: uppercase;">
            ${message}
        </div>
    `;
    toast.style.position = 'fixed';
    toast.style.bottom = '30px';
    toast.style.right = '30px';
    toast.style.zIndex = '9999';
    toast.style.animation = 'fadeInUp 0.5s ease forwards';
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'fadeOutDown 0.5s ease forwards';
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

// Flash message auto-hide
setTimeout(() => {
    const alert = document.querySelector('.alert');
    if (alert) {
        alert.style.transition = '0.5s';
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 500);
    }
}, 3000);

// Add fadeOutDown animation
const style = document.createElement('style');
style.innerHTML = `
    @keyframes fadeOutDown {
        from { opacity: 1; transform: translateY(0); }
        to { opacity: 0; transform: translateY(20px); }
    }
`;
document.head.appendChild(style);
