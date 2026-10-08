/**
 * FASHION WORLD PRO — BUILD MY OUTFIT CONTROLLER (build_outfit.js)
 * High-performance, isolated client-side manager for head-to-toe styling suite.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Current Active State
    const state = {
        category: window.ACTIVE_CATEGORY || 'Men',
        mainProductId: window.MAIN_PRODUCT_ID || null,
        activeSlotTarget: null, // slot index for modal
        activeRoleTarget: 'all',
        slots: {
            main: null,
            1: null,
            2: null,
            3: null
        }
    };

    // DOM Elements
    const outfitGridCanvas = document.getElementById('outfitGridCanvas');
    const outfitTotalPrice = document.getElementById('outfitTotalPrice');
    const outfitOriginalPrice = document.getElementById('outfitOriginalPrice');
    const outfitItemCount = document.getElementById('outfitItemCount');
    const btnAddFullLook = document.getElementById('btnAddFullLook');
    const btnBuyFullLook = document.getElementById('btnBuyFullLook');
    const btnScrollToPicker = document.getElementById('btnScrollToPicker');
    
    // Anchor Picker Elements
    const pickerProductsGrid = document.getElementById('pickerProductsGrid');
    const pickerSearchInput = document.getElementById('pickerSearchInput');
    const pickerRolePills = document.getElementById('pickerRolePills');
    
    // Modal Elements
    const modalBackdrop = document.getElementById('outfitModalBackdrop');
    const btnCloseModal = document.getElementById('btnCloseModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalEyebrow = document.getElementById('modalEyebrow');
    const modalSearchInput = document.getElementById('modalSearchInput');
    const modalProductsList = document.getElementById('modalProductsList');

    // =========================================================================
    // 1. INITIALIZATION & STATE PARSING
    // =========================================================================
    function initOutfitState() {
        // Parse current DOM slots
        const mainCard = document.getElementById('slotCardMain');
        if (mainCard && mainCard.dataset.productId) {
            state.slots.main = {
                id: parseInt(mainCard.dataset.productId),
                price: parseFloat(mainCard.dataset.price) || 0
            };
        }

        [1, 2, 3].forEach(idx => {
            const card = document.getElementById(`slotCard${idx}`);
            if (card && card.dataset.productId) {
                state.slots[idx] = {
                    id: parseInt(card.dataset.productId),
                    price: parseFloat(card.dataset.price) || 0
                };
            }
        });

        recalculateTotalPrice();
    }

    function parseCardPrice(card) {
        const finalPriceEl = card.querySelector('.slot-price-final');
        if (!finalPriceEl) return 0;
        const txt = finalPriceEl.innerText.replace(/[^0-9.]/g, '');
        return parseFloat(txt) || 0;
    }

    // =========================================================================
    // 2. TOTAL PRICE CALCULATION
    // =========================================================================
    function recalculateTotalPrice() {
        let total = 0;
        let count = 0;

        Object.keys(state.slots).forEach(key => {
            const item = state.slots[key];
            if (item && item.price) {
                total += item.price;
                count++;
            }
        });

        if (outfitTotalPrice) {
            outfitTotalPrice.innerText = `₹${total.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        }

        if (outfitItemCount) {
            outfitItemCount.innerText = `${count} Item${count !== 1 ? 's' : ''} Selected`;
        }
    }

    // =========================================================================
    // 3. ANCHOR PRODUCT SELECTION
    // =========================================================================
    async function selectAnchorProduct(productId) {
        if (!productId) return;

        showToast('Generating coordinating items...', 'info');

        try {
            const res = await fetch(`/api/outfit/match/${productId}`);
            if (!res.ok) throw new Error('Failed to fetch outfit recommendations');
            const data = await res.json();

            // Update state & UI
            renderCompleteOutfit(data);
            
            // Highlight selected in picker
            document.querySelectorAll('.picker-product-card').forEach(c => {
                if (c.dataset.id === String(productId)) {
                    c.classList.add('selected-anchor');
                    const btnSpan = c.querySelector('.btn-select-anchor span');
                    if (btnSpan) btnSpan.innerText = 'Selected';
                } else {
                    c.classList.remove('selected-anchor');
                    const btnSpan = c.querySelector('.btn-select-anchor span');
                    if (btnSpan) btnSpan.innerText = 'Style With This';
                }
            });

            // Scroll to outfit showcase smoothly
            const showcase = document.getElementById('outfitShowcaseSection');
            if (showcase) {
                showcase.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }

            showToast('Look updated with genuine coordinating items!', 'success');
        } catch (err) {
            console.error('Error matching outfit:', err);
            showToast('Could not load outfit matches. Please try again.', 'error');
        }
    }

    function renderCompleteOutfit(data) {
        const main = data.main_product;
        const slots = data.matching_slots || [];

        // 1. Render Main Slot
        if (main) {
            state.slots.main = {
                id: main.id,
                price: main.effective_price
            };

            const mainCard = document.getElementById('slotCardMain');
            if (mainCard) {
                mainCard.dataset.productId = main.id;
                document.getElementById('slotImgMain').src = main.image_url;
                document.getElementById('slotTitleMain').innerText = main.name;
                document.getElementById('slotStockMain').innerText = (main.stock && main.stock > 0) ? `In Stock (${main.stock})` : 'Available';

                const priceRow = document.getElementById('slotPriceMain');
                if (main.discount_price) {
                    priceRow.innerHTML = `
                        <span class="slot-price-final">₹${main.discount_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                        <span class="slot-price-original">₹${main.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                    `;
                } else {
                    priceRow.innerHTML = `<span class="slot-price-final">₹${main.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>`;
                }
            }
        }

        // 2. Render 3 Matching Slots
        slots.forEach((slot, index) => {
            const slotIdx = index + 1;
            const p = slot.product;
            const card = document.getElementById(`slotCard${slotIdx}`);
            if (!card) return;

            if (p) {
                state.slots[slotIdx] = {
                    id: p.id,
                    price: p.effective_price
                };
                card.dataset.productId = p.id;
                card.dataset.role = slot.role;

                card.querySelector('.slot-media-wrap').innerHTML = `
                    <img src="${p.image_url}" alt="${p.name}" id="slotImg${slotIdx}" class="slot-product-img">
                    <span class="slot-stock-status in-stock" id="slotStock${slotIdx}">
                        ${(p.stock && p.stock > 0) ? `In Stock (${p.stock})` : 'Available'}
                    </span>
                `;

                card.querySelector('.slot-role-name').innerText = slot.slot_name;
                card.querySelector('.slot-product-title').innerText = p.name;

                const priceRow = card.querySelector('.slot-price-row');
                if (p.discount_price) {
                    priceRow.innerHTML = `
                        <span class="slot-price-final">₹${p.discount_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                        <span class="slot-price-original">₹${p.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                    `;
                } else {
                    priceRow.innerHTML = `<span class="slot-price-final">₹${p.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>`;
                }
            } else {
                state.slots[slotIdx] = null;
                card.dataset.productId = '';
                card.querySelector('.slot-media-wrap').innerHTML = `
                    <div class="slot-empty-state">
                        <i class="fa-solid fa-box-open"></i>
                        <span>No matching item available</span>
                    </div>
                `;
                card.querySelector('.slot-product-title').innerText = 'No matching item available';
                card.querySelector('.slot-price-row').innerHTML = `<span class="slot-price-none">—</span>`;
            }
        });

        recalculateTotalPrice();
    }

    // =========================================================================
    // 4. ITEM REPLACEMENT MODAL / DRAWER
    // =========================================================================
    async function openReplacementModal(slotKey, role, currentProductId) {
        state.activeSlotTarget = slotKey;
        state.activeRoleTarget = role || 'all';

        if (modalTitle) {
            modalTitle.innerText = slotKey === 'main' ? 'Select New Anchor Product' : `Select Alternative ${role ? role.toUpperCase() : 'ITEM'}`;
        }
        if (modalEyebrow) {
            modalEyebrow.innerText = `${state.category.toUpperCase()}'S WEAR COLLECTION`;
        }

        if (modalBackdrop) {
            modalBackdrop.style.display = 'flex';
        }

        if (modalSearchInput) {
            modalSearchInput.value = '';
        }

        await fetchAndRenderModalProducts('', role, currentProductId);
    }

    function closeModal() {
        if (modalBackdrop) {
            modalBackdrop.style.display = 'none';
        }
    }

    async function fetchAndRenderModalProducts(search = '', role = 'all', excludeId = '') {
        if (!modalProductsList) return;

        modalProductsList.innerHTML = `
            <div class="modal-loading-state">
                <i class="fa-solid fa-spinner fa-spin"></i>
                <span>Loading available items...</span>
            </div>
        `;

        try {
            // Collect currently used product IDs to exclude duplicates
            const usedIds = Object.keys(state.slots)
                .map(k => state.slots[k] ? state.slots[k].id : null)
                .filter(id => id !== null);

            const params = new URLSearchParams({
                category: state.category,
                role: role,
                search: search,
                exclude: usedIds.join(',')
            });

            const res = await fetch(`/api/outfit/products?${params.toString()}`);
            if (!res.ok) throw new Error('Failed to load products');
            const data = await res.json();

            const products = data.products || [];
            if (products.length === 0) {
                modalProductsList.innerHTML = `
                    <div class="modal-loading-state">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                        <span>No alternative items found matching your criteria.</span>
                    </div>
                `;
                return;
            }

            modalProductsList.innerHTML = products.map(p => `
                <div class="modal-product-item" data-id="${p.id}" data-json='${JSON.stringify(p).replace(/'/g, "&#39;")}'>
                    <img src="${p.image_url}" alt="${p.name}" class="item-img" loading="lazy">
                    <h5 class="item-title">${p.name}</h5>
                    <div class="item-price">₹${p.effective_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                </div>
            `).join('');

            // Attach click handler to items
            modalProductsList.querySelectorAll('.modal-product-item').forEach(item => {
                item.addEventListener('click', () => {
                    const prodData = JSON.parse(item.dataset.json);
                    swapSlotProduct(state.activeSlotTarget, prodData);
                    closeModal();
                });
            });

        } catch (err) {
            console.error('Error fetching modal products:', err);
            modalProductsList.innerHTML = `
                <div class="modal-loading-state">
                    <i class="fa-solid fa-circle-exclamation"></i>
                    <span>Failed to load items. Please try again.</span>
                </div>
            `;
        }
    }

    function swapSlotProduct(slotKey, product) {
        if (!product) return;

        if (slotKey === 'main') {
            // If changing anchor piece, re-generate entire outfit matching
            selectAnchorProduct(product.id);
            return;
        }

        // Update single slot
        state.slots[slotKey] = {
            id: product.id,
            price: product.effective_price
        };

        const card = document.getElementById(`slotCard${slotKey}`);
        if (card) {
            card.dataset.productId = product.id;
            card.querySelector('.slot-media-wrap').innerHTML = `
                <img src="${product.image_url}" alt="${product.name}" id="slotImg${slotKey}" class="slot-product-img">
                <span class="slot-stock-status in-stock" id="slotStock${slotKey}">
                    ${(product.stock && product.stock > 0) ? `In Stock (${product.stock})` : 'Available'}
                </span>
            `;

            card.querySelector('.slot-product-title').innerText = product.name;

            const priceRow = card.querySelector('.slot-price-row');
            if (product.discount_price) {
                priceRow.innerHTML = `
                    <span class="slot-price-final">₹${product.discount_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                    <span class="slot-price-original">₹${product.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                `;
            } else {
                priceRow.innerHTML = `<span class="slot-price-final">₹${product.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>`;
            }
        }

        recalculateTotalPrice();
        showToast(`Replaced item with "${product.name.substring(0, 24)}..."`, 'success');
    }

    // =========================================================================
    // 5. CART & CHECKOUT INTEGRATION
    // =========================================================================
    async function addOutfitToCart(redirectCheckout = false) {
        const productIds = Object.keys(state.slots)
            .map(k => state.slots[k] ? state.slots[k].id : null)
            .filter(id => id !== null);

        if (productIds.length === 0) {
            showToast('Please select at least one item for your outfit.', 'warning');
            return;
        }

        const btn = redirectCheckout ? btnBuyFullLook : btnAddFullLook;
        const originalText = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing...`;
        }

        try {
            const res = await fetch('/api/outfit/add-to-cart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ product_ids: productIds })
            });

            if (!res.ok) throw new Error('Failed to add items to cart');
            const data = await res.json();

            // Update Cart count badge in storefront header if present
            const cartCountBadge = document.getElementById('cartCountBadge');
            if (cartCountBadge && data.count !== undefined) {
                cartCountBadge.innerText = data.count;
                cartCountBadge.style.display = 'inline-flex';
            }

            showToast(data.message || 'Complete outfit added to your cart!', 'success');

            if (redirectCheckout) {
                setTimeout(() => {
                    window.location.href = '/checkout';
                }, 400);
            }

        } catch (err) {
            console.error('Error adding full look to cart:', err);
            showToast('Could not add outfit to cart. Please try again.', 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        }
    }

    // =========================================================================
    // 6. EVENT LISTENERS
    // =========================================================================
    
    // Change Button on any slot card
    document.addEventListener('click', (e) => {
        const changeBtn = e.target.closest('.btn-change-slot');
        if (changeBtn) {
            const slotKey = changeBtn.dataset.slot;
            const role = changeBtn.dataset.role;
            const currentCard = changeBtn.closest('.outfit-slot-card');
            const currentId = currentCard ? currentCard.dataset.productId : '';
            openReplacementModal(slotKey, role, currentId);
        }

        // Anchor select button in bottom picker
        const selectAnchorBtn = e.target.closest('.btn-select-anchor');
        if (selectAnchorBtn) {
            const prodId = selectAnchorBtn.dataset.id;
            selectAnchorProduct(prodId);
        }
    });

    // Close Modal Button & Backdrop click
    if (btnCloseModal) {
        btnCloseModal.addEventListener('click', closeModal);
    }
    if (modalBackdrop) {
        modalBackdrop.addEventListener('click', (e) => {
            if (e.target === modalBackdrop) closeModal();
        });
    }

    // Modal Search Filter with debounce
    if (modalSearchInput) {
        let debounceTimer;
        modalSearchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                fetchAndRenderModalProducts(e.target.value.trim(), state.activeRoleTarget);
            }, 250);
        });
    }

    // Anchor Picker Search with client-side filtering
    if (pickerSearchInput) {
        pickerSearchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            const cards = pickerProductsGrid ? pickerProductsGrid.querySelectorAll('.picker-product-card') : [];
            cards.forEach(card => {
                const name = (card.dataset.name || '').toLowerCase();
                if (!query || name.includes(query)) {
                    card.style.display = 'flex';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }

    // Role Pills in Picker
    if (pickerRolePills) {
        pickerRolePills.addEventListener('click', (e) => {
            const pill = e.target.closest('.role-pill-btn');
            if (!pill) return;
            pickerRolePills.querySelectorAll('.role-pill-btn').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            const role = pill.dataset.role;
            const cards = pickerProductsGrid ? pickerProductsGrid.querySelectorAll('.picker-product-card') : [];
            
            cards.forEach(card => {
                const name = (card.dataset.name || '').toLowerCase();
                let matchesRole = true;
                if (role === 'top') {
                    matchesRole = ['shirt', 't-shirt', 'tee', 'top', 'blouse', 'kurti', 'polo', 'hoodie', 'sweatshirt', 'sweater', 'jacket', 'coat'].some(k => name.includes(k));
                } else if (role === 'bottom') {
                    matchesRole = ['jean', 'trouser', 'pant', 'skirt', 'short', 'jogger', 'legging'].some(k => name.includes(k));
                } else if (role === 'footwear') {
                    matchesRole = ['shoe', 'footwear', 'sneaker', 'boot', 'sandal', 'loafer', 'sock', 'flat', 'heel'].some(k => name.includes(k));
                } else if (role === 'accessory') {
                    matchesRole = ['bag', 'clutch', 'watch', 'sunglass', 'belt', 'wallet', 'hat', 'cap', 'scarf', 'jewelry'].some(k => name.includes(k));
                }

                card.style.display = matchesRole ? 'flex' : 'none';
            });
        });
    }

    // Cart and Buy Now buttons
    if (btnAddFullLook) {
        btnAddFullLook.addEventListener('click', () => addOutfitToCart(false));
    }
    if (btnBuyFullLook) {
        btnBuyFullLook.addEventListener('click', () => addOutfitToCart(true));
    }

    // Scroll to picker button
    if (btnScrollToPicker) {
        btnScrollToPicker.addEventListener('click', () => {
            const picker = document.getElementById('anchorPickerSection');
            if (picker) picker.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }

    // Toast Notification Helper
    function showToast(message, type = 'info') {
        const container = document.getElementById('outfitToastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `outfit-toast ${type}`;
        
        let icon = 'fa-info-circle';
        if (type === 'success') icon = 'fa-circle-check';
        if (type === 'warning') icon = 'fa-triangle-exclamation';
        if (type === 'error') icon = 'fa-circle-exclamation';

        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3200);
    }

    // Initialize state
    initOutfitState();
});
