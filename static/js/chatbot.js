/* ==========================================================================
   FASHION WORLD PRO — FASHION ASSISTANT JAVASCRIPT CONTROLLER
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    const launcher = document.getElementById('fwChatbotLauncher');
    const chatWindow = document.getElementById('fwChatbotWindow');
    const closeBtn = document.getElementById('fwChatCloseBtn');
    const clearBtn = document.getElementById('fwChatClearBtn');
    const chatBody = document.getElementById('fwChatBody');
    const chatForm = document.getElementById('fwChatForm');
    const chatInput = document.getElementById('fwChatInput');
    const typingRow = document.getElementById('fwChatTypingRow');

    if (!launcher || !chatWindow || !chatForm || !chatInput || !chatBody) {
        return;
    }

    let isOpen = false;
    let isProcessing = false;

    // Helper: Scroll to bottom
    function scrollToBottom() {
        requestAnimationFrame(() => {
            chatBody.scrollTop = chatBody.scrollHeight;
        });
    }

    // Toggle Chat
    function toggleChat(openState) {
        isOpen = (openState !== undefined) ? openState : !isOpen;
        if (isOpen) {
            chatWindow.classList.add('open');
            chatInput.focus();
            scrollToBottom();
        } else {
            chatWindow.classList.remove('open');
        }
    }

    launcher.addEventListener('click', (e) => {
        e.preventDefault();
        toggleChat();
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            toggleChat(false);
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && isOpen) {
            toggleChat(false);
        }
    });

    // Helper: Show/Hide Typing Indicator
    function showTyping(show) {
        if (typingRow) {
            typingRow.style.display = show ? 'flex' : 'none';
            if (show) scrollToBottom();
        }
    }

    // Helper: Escape HTML
    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // Append User Message
    function appendUserMessage(text) {
        const row = document.createElement('div');
        row.className = 'fw-chat-msg-row user-row';
        row.innerHTML = `<div class="fw-chat-bubble">${escapeHtml(text)}</div>`;
        chatBody.appendChild(row);
        scrollToBottom();
    }

    // Render Size Recommendation Widget inside chat
    function createSizeWidget() {
        const widget = document.createElement('div');
        widget.className = 'fw-chat-size-widget';
        widget.innerHTML = `
            <div id="chatSizeForm">
                <div class="fw-chat-size-row">
                    <div>
                        <label>Height (cm)</label>
                        <input type="number" class="fw-chat-size-input chat-h-input" placeholder="e.g. 175" min="100" max="240">
                    </div>
                    <div>
                        <label>Weight (kg)</label>
                        <input type="number" class="fw-chat-size-input chat-w-input" placeholder="e.g. 70" min="30" max="200">
                    </div>
                </div>
                <label>Fit Preference</label>
                <div class="fw-chat-fit-group">
                    <button type="button" class="fw-chat-fit-btn" data-fit="slim">Slim</button>
                    <button type="button" class="fw-chat-fit-btn active" data-fit="regular">Regular</button>
                    <button type="button" class="fw-chat-fit-btn" data-fit="relaxed">Relaxed</button>
                </div>
                <div class="chat-size-alert" style="display: none; color: #c0392b; font-size: 0.75rem; font-weight: 600; margin-bottom: 8px;">
                    Please enter realistic height (100-240cm) and weight (30-200kg).
                </div>
                <button type="button" class="fw-chat-calc-btn">Calculate Recommended Size</button>
            </div>
            <div class="fw-chat-size-result-card">
                <span style="font-size: 0.72rem; font-weight: 700; letter-spacing: 1px; color: #a47c36; text-transform: uppercase;">Your Recommended Size</span>
                <div>
                    <span class="fw-chat-size-badge chat-result-badge">M</span>
                </div>
                <p style="font-size: 0.76rem; color: #64748b; margin: 0 0 10px;">Based on your height, weight & fit preference.</p>
                <div style="display: flex; gap: 6px; justify-content: center; flex-wrap: wrap;">
                    <button type="button" class="fw-chat-chip chat-use-size-btn" style="background:#111827; color:#fff; border-color:#111827;">Explore Size Products</button>
                    <button type="button" class="fw-chat-chip chat-recalc-btn">Recalculate</button>
                </div>
            </div>
        `;

        let selectedFit = 'regular';
        const fitBtns = widget.querySelectorAll('.fw-chat-fit-btn');
        fitBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                fitBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                selectedFit = btn.getAttribute('data-fit');
            });
        });

        const calcBtn = widget.querySelector('.fw-chat-calc-btn');
        const hInput = widget.querySelector('.chat-h-input');
        const wInput = widget.querySelector('.chat-w-input');
        const formView = widget.querySelector('#chatSizeForm');
        const resultView = widget.querySelector('.fw-chat-size-result-card');
        const badge = widget.querySelector('.chat-result-badge');
        const alertBox = widget.querySelector('.chat-size-alert');
        const useSizeBtn = widget.querySelector('.chat-use-size-btn');
        const recalcBtn = widget.querySelector('.chat-recalc-btn');

        calcBtn.addEventListener('click', () => {
            const h = parseFloat(hInput.value.trim());
            const w = parseFloat(wInput.value.trim());

            if (isNaN(h) || isNaN(w) || h < 100 || h > 240 || w < 30 || w > 200) {
                alertBox.style.display = 'block';
                return;
            }
            alertBox.style.display = 'none';

            // Central Rule-based BMI Sizing Formula
            const heightM = h / 100.0;
            const bmi = w / (heightM * heightM);
            let baseSize = 'M';

            if (bmi < 19.5) {
                baseSize = (h > 180) ? 'M' : 'S';
            } else if (bmi < 23.5) {
                if (h < 165) baseSize = 'S';
                else if (h <= 178) baseSize = 'M';
                else baseSize = 'L';
            } else if (bmi < 27.0) {
                if (h < 170) baseSize = 'M';
                else if (h <= 182) baseSize = 'L';
                else baseSize = 'XL';
            } else if (bmi < 31.0) {
                if (h < 175) baseSize = 'L';
                else if (h <= 185) baseSize = 'XL';
                else baseSize = 'XXL';
            } else {
                baseSize = 'XXL';
            }

            const sizeLadder = ['S', 'M', 'L', 'XL', 'XXL'];
            let idx = sizeLadder.indexOf(baseSize);
            if (idx === -1) idx = 1;

            if (selectedFit === 'slim') idx = Math.max(0, idx - 1);
            else if (selectedFit === 'relaxed') idx = Math.min(sizeLadder.length - 1, idx + 1);

            const finalSize = sizeLadder[idx];
            badge.textContent = `${finalSize} ✓`;
            formView.style.display = 'none';
            resultView.style.display = 'block';
            scrollToBottom();

            useSizeBtn.onclick = () => {
                // If on product page, apply size
                const sizeBtns = document.querySelectorAll('.size-btn');
                let foundBtn = null;
                sizeBtns.forEach(btn => {
                    if (btn.getAttribute('data-size') === finalSize) foundBtn = btn;
                });
                if (foundBtn) {
                    foundBtn.click();
                    if (typeof showToast === 'function') {
                        showToast(`Selected Size ${finalSize} on page!`);
                    }
                } else {
                    sendMessage(`Show ${finalSize} size products`);
                }
            };
        });

        recalcBtn.addEventListener('click', () => {
            resultView.style.display = 'none';
            formView.style.display = 'block';
            scrollToBottom();
        });

        return widget;
    }

    // Append Bot Response
    function appendBotResponse(data) {
        const row = document.createElement('div');
        row.className = 'fw-chat-msg-row bot-row';

        const avatar = document.createElement('div');
        avatar.className = 'fw-chat-msg-avatar';
        avatar.innerHTML = '<i class="fa-solid fa-gem"></i>';
        row.appendChild(avatar);

        const bubble = document.createElement('div');
        bubble.className = 'fw-chat-bubble';

        // 1. Text Message
        let bubbleHtml = `<p style="margin: 0 0 ${data.products || data.orders || data.cart_items || data.type === 'size_finder' ? '8px' : '0'};">${escapeHtml(data.message)}</p>`;

        // 2. Login Required Action
        if (data.type === 'login_required') {
            bubbleHtml += `
                <div style="margin-top: 10px;">
                    <a href="${data.login_url}" class="fw-chat-chip" style="background: #111827; color: #ffffff; border-color: #111827; font-weight: 700; padding: 8px 14px;">
                        <i class="fa-solid fa-arrow-right-to-bracket"></i> ${escapeHtml(data.action_label || 'Log In')}
                    </a>
                </div>
            `;
        }

        // 3. Customer Support Actions
        if (data.type === 'support') {
            bubbleHtml += `
                <div style="display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap;">
                    <a href="${data.support_url}" class="fw-chat-chip" style="background: #c8a355; color: #ffffff; border-color: #c8a355; font-weight: 700;">
                        <i class="fa-solid fa-headset"></i> Contact Support
                    </a>
                    ${data.orders_url ? `<a href="${data.orders_url}" class="fw-chat-chip"><i class="fa-solid fa-box-open"></i> My Orders</a>` : ''}
                </div>
            `;
        }

        // 4. Products Grid / Cards
        if (data.products && data.products.length > 0) {
            bubbleHtml += `<div class="fw-chat-products-grid">`;
            data.products.forEach(p => {
                const stockLabel = p.in_stock ? '<span style="color:#059669;font-size:0.68rem;font-weight:600;"><i class="fa-solid fa-check"></i> In Stock</span>' : '<span style="color:#dc2626;font-size:0.68rem;font-weight:600;">Out of Stock</span>';
                bubbleHtml += `
                    <div class="fw-chat-product-card" data-product-id="${p.id}">
                        <img src="${p.image_url}" alt="${escapeHtml(p.name)}" class="fw-chat-prod-thumb" onerror="this.src='/static/images/p1.png'">
                        <div class="fw-chat-prod-details">
                            <h5 class="fw-chat-prod-title" title="${escapeHtml(p.name)}">${escapeHtml(p.name)}</h5>
                            <div class="fw-chat-prod-category">${escapeHtml(p.category || 'Fashion')} • ${stockLabel}</div>
                            <div class="fw-chat-prod-price-row">
                                <span class="fw-chat-prod-price">${p.price_formatted}</span>
                                ${p.original_price_formatted ? `<span class="fw-chat-prod-oldprice">${p.original_price_formatted}</span>` : ''}
                            </div>
                            <div class="fw-chat-prod-actions">
                                <a href="${p.url}" class="fw-chat-btn-view" target="_self">View</a>
                                <button type="button" class="fw-chat-btn-cart chat-action-cart" data-id="${p.id}" ${!p.in_stock ? 'disabled style="opacity:0.5;cursor:not-allowed;"' : ''}>
                                    <i class="fa-solid fa-bag-shopping"></i> Add
                                </button>
                                <button type="button" class="fw-chat-btn-wish chat-action-wish ${p.in_wishlist ? 'active' : ''}" data-id="${p.id}" title="${p.in_wishlist ? 'Remove from Wishlist' : 'Add to Wishlist'}">
                                    <i class="${p.in_wishlist ? 'fa-solid fa-heart' : 'fa-regular fa-heart'}"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            });
            bubbleHtml += `</div>`;

            if (data.view_all_url) {
                bubbleHtml += `
                    <div style="margin-top: 10px; text-align: center;">
                        <a href="${data.view_all_url}" class="fw-chat-chip" style="background:#faf7f2; border-color:#dcd4c7; width:100%; justify-content:center;">
                            View Full Collection <i class="fa-solid fa-arrow-right"></i>
                        </a>
                    </div>
                `;
            }
        }

        // 5. Orders List
        if (data.orders && data.orders.length > 0) {
            bubbleHtml += `<div style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px;">`;
            data.orders.forEach(o => {
                const isPending = (o.status || '').toLowerCase() !== 'delivered';
                bubbleHtml += `
                    <div class="fw-chat-order-card">
                        <div class="fw-chat-order-header">
                            <span class="fw-chat-order-num">${o.order_number}</span>
                            <span class="fw-chat-order-status ${isPending ? 'pending' : ''}">${escapeHtml(o.status)}</span>
                        </div>
                        <div style="font-size: 0.74rem; color: #64748b; margin-bottom: 4px;">Placed on: ${o.date}</div>
                        <div class="fw-chat-order-footer">
                            <strong style="font-size: 0.82rem; color: #111827;">${o.total_formatted}</strong>
                            <a href="${o.track_url}" class="fw-chat-btn-view" style="font-size: 0.72rem; padding: 4px 8px;">Track Order</a>
                        </div>
                    </div>
                `;
            });
            bubbleHtml += `</div>`;
            if (data.dashboard_url) {
                bubbleHtml += `
                    <div style="margin-top: 10px; text-align: center;">
                        <a href="${data.dashboard_url}" class="fw-chat-chip" style="width:100%; justify-content:center;">
                            <i class="fa-solid fa-clipboard-list"></i> View All Orders
                        </a>
                    </div>
                `;
            }
        }

        // 6. Cart Items Summary
        if (data.cart_items && data.cart_items.length > 0) {
            bubbleHtml += `<div style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px;">`;
            data.cart_items.forEach(c => {
                bubbleHtml += `
                    <div style="display: flex; gap: 10px; align-items: center; background: #fff; padding: 8px; border: 1px solid #ebd9c2; border-radius: 6px;">
                        <img src="${c.image_url}" style="width: 40px; height: 48px; object-fit: cover; border-radius: 4px;" onerror="this.src='/static/images/p1.png'">
                        <div style="flex: 1; min-width: 0;">
                            <div style="font-size: 0.78rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(c.name)}</div>
                            <div style="font-size: 0.7rem; color: #64748b;">Qty: ${c.quantity} • Size: ${c.size || 'M'}</div>
                        </div>
                        <strong style="font-size: 0.8rem; color: #111827;">${c.price_formatted}</strong>
                    </div>
                `;
            });
            bubbleHtml += `</div>`;
            bubbleHtml += `
                <div style="display: flex; gap: 6px; margin-top: 10px;">
                    <a href="${data.cart_url || '/cart'}" class="fw-chat-chip" style="flex: 1; justify-content: center;"><i class="fa-solid fa-cart-shopping"></i> View Bag</a>
                    <a href="${data.checkout_url || '/checkout'}" class="fw-chat-chip" style="flex: 1; justify-content: center; background: #c8a355; color: #fff; border-color: #c8a355; font-weight: 700;"><i class="fa-solid fa-credit-card"></i> Checkout</a>
                </div>
            `;
        }

        bubble.innerHTML = bubbleHtml;

        // Size Recommendation Form Attachment
        if (data.type === 'size_finder') {
            bubble.appendChild(createSizeWidget());
        }

        // Quick Reply Chips
        if (data.quick_replies && data.quick_replies.length > 0) {
            const chipsDiv = document.createElement('div');
            chipsDiv.className = 'fw-chat-chips-container';
            data.quick_replies.forEach(chipText => {
                const chipBtn = document.createElement('button');
                chipBtn.type = 'button';
                chipBtn.className = 'fw-chat-chip';
                chipBtn.textContent = chipText;
                chipBtn.addEventListener('click', () => {
                    const cleanQuery = chipText.replace(/^[^\w\s]+/, '').trim();
                    sendMessage(cleanQuery);
                });
                chipsDiv.appendChild(chipBtn);
            });
            bubble.appendChild(chipsDiv);
        }

        row.appendChild(bubble);
        chatBody.appendChild(row);
        scrollToBottom();

        // Hook up Card Action Listeners
        attachCardListeners(row);
    }

    // Attach AJAX Cart & Wishlist Listeners to Product Cards
    function attachCardListeners(container) {
        // Add to Cart
        container.querySelectorAll('.chat-action-cart').forEach(btn => {
            btn.addEventListener('click', async function(e) {
                e.preventDefault();
                const prodId = this.getAttribute('data-id');
                if (!prodId) return;

                const origHtml = this.innerHTML;
                this.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

                try {
                    const res = await fetch(`/add_to_cart/${prodId}?size=M`, {
                        method: 'POST',
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest',
                            'Content-Type': 'application/json'
                        }
                    });
                    const data = await res.json().catch(() => ({}));

                    if (data.success) {
                        this.classList.add('added');
                        this.innerHTML = '<i class="fa-solid fa-check"></i> Added';

                        // Update header cart badge
                        const badges = document.querySelectorAll('#cartCountBadge, .cart-count-pill');
                        if (data.count !== undefined) {
                            badges.forEach(b => b.textContent = data.count);
                        }

                        if (typeof showToast === 'function') {
                            showToast(data.message || 'Added to cart!');
                        }
                    } else {
                        this.innerHTML = origHtml;
                    }
                } catch (err) {
                    console.error('Chatbot Add to Cart error:', err);
                    this.innerHTML = origHtml;
                }
            });
        });

        // Wishlist Toggle
        container.querySelectorAll('.chat-action-wish').forEach(btn => {
            btn.addEventListener('click', async function(e) {
                e.preventDefault();
                const prodId = this.getAttribute('data-id');
                if (!prodId) return;

                const icon = this.querySelector('i');

                try {
                    const res = await fetch(`/toggle_wishlist/${prodId}`, {
                        method: 'POST',
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest',
                            'Content-Type': 'application/json'
                        }
                    });

                    if (res.status === 401) {
                        const data = await res.json().catch(() => ({}));
                        window.location.href = data.redirect || '/login';
                        return;
                    }

                    const data = await res.json().catch(() => ({}));
                    if (data.success) {
                        if (data.in_wishlist) {
                            this.classList.add('active');
                            if (icon) icon.className = 'fa-solid fa-heart';
                            this.setAttribute('title', 'Remove from Wishlist');
                        } else {
                            this.classList.remove('active');
                            if (icon) icon.className = 'fa-regular fa-heart';
                            this.setAttribute('title', 'Add to Wishlist');
                        }

                        // Update header wishlist badge
                        const wishBadges = document.querySelectorAll('#wishlistCountBadge, .wishlist-count-pill');
                        if (data.count !== undefined) {
                            wishBadges.forEach(b => {
                                b.textContent = data.count;
                                b.style.display = data.count > 0 ? '' : 'none';
                            });
                        }

                        if (typeof showToast === 'function') {
                            showToast(data.message || (data.in_wishlist ? 'Added to wishlist!' : 'Removed from wishlist!'));
                        }
                    }
                } catch (err) {
                    console.error('Chatbot Wishlist error:', err);
                }
            });
        });
    }

    // Send Message to /api/chatbot
    async function sendMessage(msgText) {
        const text = (msgText || chatInput.value || '').trim();
        if (!text || isProcessing) return;

        chatInput.value = '';
        appendUserMessage(text);
        isProcessing = true;
        showTyping(true);

        try {
            const response = await fetch('/api/chatbot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ message: text })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            showTyping(false);
            appendBotResponse(data);
        } catch (err) {
            console.error('Chatbot request error:', err);
            showTyping(false);
            appendBotResponse({
                type: 'text',
                message: "I'm having trouble connecting right now. Please try again or reach out to Customer Support.",
                quick_replies: ["🎧 Contact Support", "🛍️ My Cart", "🔥 Flash Sale"]
            });
        } finally {
            isProcessing = false;
        }
    }

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        sendMessage();
    });

    // Clear chat listener
    if (clearBtn) {
        clearBtn.addEventListener('click', (e) => {
            e.preventDefault();
            // Preserve initial greeting
            const initialCard = chatBody.querySelector('.fw-chat-initial-card');
            chatBody.innerHTML = '';
            if (initialCard) {
                chatBody.appendChild(initialCard);
                // Re-bind initial chips
                bindInitialChips();
            }
            scrollToBottom();
        });
    }

    // Bind Initial Quick Chips in HTML
    function bindInitialChips() {
        document.querySelectorAll('.fw-initial-chip').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const query = this.getAttribute('data-query') || this.textContent.trim().replace(/^[^\w\s]+/, '').trim();
                sendMessage(query);
            });
        });
    }

    bindInitialChips();
});
