/**
 * Fashion World Pro - Virtual Try-On Studio (UI Foundation)
 * Handles client-side photo validation, product selection, UI state management, and honest preview generation state.
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- Elements ---
    const photoFileInput = document.getElementById('tryonPhotoInput');
    const photoUploadDropzone = document.getElementById('photoUploadDropzone');
    const photoUploadPrompt = document.getElementById('photoUploadPrompt');
    const photoPreviewContainer = document.getElementById('photoPreviewContainer');
    const userPhotoPreviewImg = document.getElementById('userPhotoPreviewImg');
    const photoFileName = document.getElementById('photoFileName');
    const photoFileSize = document.getElementById('photoFileSize');
    const changePhotoBtn = document.getElementById('changePhotoBtn');
    const photoUploadError = document.getElementById('photoUploadError');

    // Product Elements
    const productSearchInput = document.getElementById('productSearchInput');
    const categoryTabs = document.querySelectorAll('.tryon-cat-tab-btn');
    const productCards = document.querySelectorAll('.tryon-product-card');
    const selectedGarmentBanner = document.getElementById('selectedGarmentBanner');
    const selectedGarmentImg = document.getElementById('selectedGarmentImg');
    const selectedGarmentName = document.getElementById('selectedGarmentName');
    const selectedGarmentPrice = document.getElementById('selectedGarmentPrice');

    // Steps & Action Elements
    const stepPhotoIndicator = document.getElementById('stepPhotoIndicator');
    const stepProductIndicator = document.getElementById('stepProductIndicator');
    const generateTryonBtn = document.getElementById('generateTryonBtn');
    const generateStatusMsg = document.getElementById('generateStatusMsg');

    // Preview Result Elements
    const previewDefaultPlaceholder = document.getElementById('previewDefaultPlaceholder');
    const previewPreparingState = document.getElementById('previewPreparingState');
    const tryonHonestAlertCard = document.getElementById('tryonHonestAlertCard');
    const honestPhotoReady = document.getElementById('honestPhotoReady');
    const honestProductReady = document.getElementById('honestProductReady');

    // State Variables
    let selectedPhotoFile = null;
    let selectedPhotoUrl = null;
    let selectedProduct = null;

    const MAX_FILE_SIZE_BYTES = 16 * 1024 * 1024; // 16 MB
    const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    const ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp'];

    // --- Photo Validation & Handling ---
    function validateFile(file) {
        if (!file) return { valid: false, error: 'No file selected.' };

        const ext = '.' + file.name.split('.').pop().toLowerCase();
        const mimeValid = ALLOWED_MIME_TYPES.includes(file.type.toLowerCase()) || ALLOWED_EXTENSIONS.includes(ext);

        if (!mimeValid) {
            return {
                valid: false,
                error: `Invalid file format (${file.type || ext}). Please upload JPG, JPEG, PNG, or WEBP.`
            };
        }

        if (file.size > MAX_FILE_SIZE_BYTES) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
            return {
                valid: false,
                error: `File is too large (${sizeMB} MB). Maximum allowed size is 16 MB.`
            };
        }

        return { valid: true };
    }

    function formatBytes(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    function handlePhotoSelection(file) {
        if (photoUploadError) photoUploadError.style.display = 'none';

        const validation = validateFile(file);
        if (!validation.valid) {
            if (photoUploadError) {
                photoUploadError.textContent = validation.error;
                photoUploadError.style.display = 'block';
            }
            if (typeof showToast === 'function') {
                showToast(validation.error);
            } else {
                console.warn(validation.error);
            }
            return;
        }

        selectedPhotoFile = file;

        // Revoke any previous object URL to avoid memory leaks
        if (selectedPhotoUrl) {
            URL.revokeObjectURL(selectedPhotoUrl);
        }

        selectedPhotoUrl = URL.createObjectURL(file);
        userPhotoPreviewImg.src = selectedPhotoUrl;
        photoFileName.textContent = file.name;
        photoFileSize.textContent = formatBytes(file.size);

        photoUploadPrompt.style.display = 'none';
        photoPreviewContainer.style.display = 'flex';

        // Update Step 1 Status
        stepPhotoIndicator.classList.add('completed');
        stepPhotoIndicator.querySelector('.tryon-step-circle').innerHTML = '✓';

        updateGenerateButtonState();
    }

    // Dropzone Event Listeners
    if (photoUploadDropzone && photoFileInput) {
        photoUploadDropzone.addEventListener('click', (e) => {
            // Don't trigger if clicked on change photo btn
            if (e.target.closest('#changePhotoBtn')) return;
            photoFileInput.click();
        });

        photoFileInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                handlePhotoSelection(this.files[0]);
            }
        });

        // Drag & Drop
        ['dragenter', 'dragover'].forEach(eventName => {
            photoUploadDropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                photoUploadDropzone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            photoUploadDropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                photoUploadDropzone.classList.remove('dragover');
            }, false);
        });

        photoUploadDropzone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            if (dt && dt.files && dt.files[0]) {
                handlePhotoSelection(dt.files[0]);
            }
        }, false);
    }

    if (changePhotoBtn && photoFileInput) {
        changePhotoBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            photoFileInput.value = '';
            photoFileInput.click();
        });
    }

    // --- Product Selection Handling ---
    function selectProduct(cardOrData) {
        if (!cardOrData) return;

        let pId, pName, pPrice, pImg;

        if (cardOrData instanceof HTMLElement) {
            const card = cardOrData;
            productCards.forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');

            pId = card.getAttribute('data-product-id');
            pName = card.getAttribute('data-product-name');
            pPrice = card.getAttribute('data-product-price');
            pImg = card.getAttribute('data-product-img');
        } else {
            pId = cardOrData.id;
            pName = cardOrData.name;
            pPrice = cardOrData.price;
            pImg = cardOrData.image || cardOrData.image_url;

            productCards.forEach(c => {
                if (c.getAttribute('data-product-id') == pId) {
                    c.classList.add('selected');
                } else {
                    c.classList.remove('selected');
                }
            });
        }

        if (!pId) return;

        selectedProduct = {
            id: pId,
            name: pName,
            price: pPrice,
            image: pImg
        };

        // Update Selected Garment Highlight Bar
        if (selectedGarmentBanner) {
            selectedGarmentBanner.classList.add('active');
            selectedGarmentBanner.setAttribute('data-product-id', pId);
            selectedGarmentBanner.setAttribute('data-product-name', pName || '');
            selectedGarmentBanner.setAttribute('data-product-price', pPrice || '');
            selectedGarmentBanner.setAttribute('data-product-img', pImg || '');
            if (selectedGarmentImg && pImg) selectedGarmentImg.src = pImg;
            if (selectedGarmentName && pName) selectedGarmentName.textContent = pName;
            if (selectedGarmentPrice && pPrice) selectedGarmentPrice.textContent = pPrice;
        }

        // Update Step 2 Status
        if (stepProductIndicator) {
            stepProductIndicator.classList.add('completed');
            const stepCircle = stepProductIndicator.querySelector('.tryon-step-circle');
            if (stepCircle) stepCircle.innerHTML = '✓';
        }

        updateGenerateButtonState();
    }

    // Attach click handlers to product cards
    productCards.forEach(card => {
        card.addEventListener('click', function(e) {
            e.preventDefault();
            selectProduct(this);
        });
    });

    // Auto-select if a product was pre-selected (via server template or query param `product_id`)
    if (selectedGarmentBanner && selectedGarmentBanner.hasAttribute('data-product-id')) {
        selectProduct({
            id: selectedGarmentBanner.getAttribute('data-product-id'),
            name: selectedGarmentBanner.getAttribute('data-product-name'),
            price: selectedGarmentBanner.getAttribute('data-product-price'),
            image: selectedGarmentBanner.getAttribute('data-product-img')
        });
    } else {
        const initialSelectedCard = document.querySelector('.tryon-product-card.selected');
        if (initialSelectedCard) {
            selectProduct(initialSelectedCard);
        }
    }

    // --- Product Category Filtering & Search ---
    let currentCategory = 'all';
    let currentSearchQuery = '';

    function filterProducts() {
        productCards.forEach(card => {
            const cat = (card.getAttribute('data-product-category') || '').toLowerCase();
            const name = (card.getAttribute('data-product-name') || '').toLowerCase();

            const categoryMatch = (currentCategory === 'all' || cat === currentCategory);
            const searchMatch = (!currentSearchQuery || name.includes(currentSearchQuery));

            if (categoryMatch && searchMatch) {
                card.style.display = 'flex';
            } else {
                card.style.display = 'none';
            }
        });
    }

    categoryTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            categoryTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            currentCategory = (this.getAttribute('data-category') || 'all').toLowerCase();
            filterProducts();
        });
    });

    if (productSearchInput) {
        productSearchInput.addEventListener('input', function() {
            currentSearchQuery = this.value.trim().toLowerCase();
            filterProducts();
        });
    }

    // --- Generate Button & Readiness State ---
    function updateGenerateButtonState() {
        const hasPhoto = !!selectedPhotoFile;
        const hasProduct = !!selectedProduct;

        if (hasPhoto && hasProduct) {
            generateTryonBtn.removeAttribute('disabled');
            generateStatusMsg.innerHTML = '<span style="color: #198754; font-weight: 600;">✓ Ready to preview! Click above to test your outfit.</span>';
        } else {
            generateTryonBtn.setAttribute('disabled', 'disabled');
            if (!hasPhoto && !hasProduct) {
                generateStatusMsg.textContent = 'Please upload a photo and select a garment to enable try-on.';
            } else if (!hasPhoto) {
                generateStatusMsg.textContent = 'Please upload your photo to enable try-on.';
            } else {
                generateStatusMsg.textContent = 'Please select a garment to enable try-on.';
            }
        }
    }

    // Result View & Action Elements
    const tryonRealResultView = document.getElementById('tryonRealResultView');
    const tryonResultImage = document.getElementById('tryonResultImage');
    const tryonResultGarmentLabel = document.getElementById('tryonResultGarmentLabel');
    const honestAlertHeading = document.getElementById('honestAlertHeading');
    const honestAlertDesc = document.getElementById('honestAlertDesc');

    const resultAddToWishlistBtn = document.getElementById('resultAddToWishlistBtn');
    const resultAddToCartBtn = document.getElementById('resultAddToCartBtn');
    const resultTryAnotherBtn = document.getElementById('resultTryAnotherBtn');
    const resultSavePreviewBtn = document.getElementById('resultSavePreviewBtn');

    let currentGeneratedResultUrl = null;
    let currentGeneratedProductId = null;

    function enableResultActions(productId, productName, resultUrl) {
        currentGeneratedResultUrl = resultUrl;
        currentGeneratedProductId = productId;

        [resultAddToWishlistBtn, resultAddToCartBtn, resultTryAnotherBtn, resultSavePreviewBtn].forEach(btn => {
            if (btn) {
                btn.removeAttribute('disabled');
                btn.classList.remove('disabled');
            }
        });
    }

    function disableResultActions() {
        [resultAddToWishlistBtn, resultAddToCartBtn, resultTryAnotherBtn, resultSavePreviewBtn].forEach(btn => {
            if (btn) {
                btn.setAttribute('disabled', 'disabled');
                btn.classList.add('disabled');
            }
        });
    }

    // --- Generate Try-On Click Event ---
    if (generateTryonBtn) {
        generateTryonBtn.addEventListener('click', async () => {
            if (!selectedPhotoFile || !selectedProduct) return;

            // Scroll down smoothly to Result Area
            const resultSection = document.getElementById('tryonResultSection');
            if (resultSection) {
                resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }

            const preparingTitle = document.getElementById('preparingStateTitle');
            const preparingSubtitle = document.getElementById('preparingStateSubtitle');
            const previewErrorState = document.getElementById('previewErrorState');
            const previewErrorTitle = document.getElementById('previewErrorTitle');
            const previewErrorMsg = document.getElementById('previewErrorMsg');

            // 1. Show "Uploading photo..." state
            previewDefaultPlaceholder.style.display = 'none';
            tryonHonestAlertCard.style.display = 'none';
            if (tryonRealResultView) tryonRealResultView.style.display = 'none';
            if (previewErrorState) previewErrorState.style.display = 'none';
            previewPreparingState.style.display = 'flex';
            disableResultActions();
            
            if (preparingTitle) preparingTitle.textContent = 'Uploading photo...';
            if (preparingSubtitle) preparingSubtitle.textContent = 'Securing temporary photo upload for fitting session...';

            // 2. Perform backend upload
            const formData = new FormData();
            formData.append('photo', selectedPhotoFile);
            if (selectedProduct && selectedProduct.id) {
                formData.append('product_id', selectedProduct.id);
            }

            let uploadId = null;

            try {
                const uploadRes = await fetch('/api/virtual-tryon/upload', {
                    method: 'POST',
                    body: formData
                });

                const uploadData = await uploadRes.json().catch(() => ({}));

                if (!uploadRes.ok || !uploadData.success) {
                    throw new Error(uploadData.message || 'Unable to upload your photo. Please try again.');
                }

                uploadId = uploadData.upload_id;

                // Update state: "Creating your virtual try-on..."
                if (preparingTitle) preparingTitle.textContent = 'Creating your virtual try-on...';
                if (preparingSubtitle) preparingSubtitle.textContent = 'AI is fitting the selected garment to your photo...';

                // 3. Call Real Replicate IDM-VTON Generation Endpoint
                const genRes = await fetch('/api/virtual-tryon/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({
                        upload_id: uploadId,
                        product_id: parseInt(selectedProduct.id, 10)
                    })
                });

                const genData = await genRes.json().catch(() => ({}));

                if (genRes.ok && genData.success && genData.result_url) {
                    // REAL AI Generation Succeeded!
                    previewPreparingState.style.display = 'none';
                    if (tryonRealResultView && tryonResultImage) {
                        tryonResultImage.src = genData.result_url;
                        if (tryonResultGarmentLabel) {
                            tryonResultGarmentLabel.textContent = `✨ ${genData.product_name || selectedProduct.name} Fitted`;
                        }
                        tryonRealResultView.style.display = 'flex';
                    }

                    enableResultActions(genData.product_id || selectedProduct.id, genData.product_name || selectedProduct.name, genData.result_url);

                    if (typeof showToast === 'function') {
                        showToast(`✨ Virtual Try-On generated for ${selectedProduct.name}!`);
                    }
                } else if (genData.configured === false) {
                    // API Token not configured in .env - Display clean honest configuration state
                    previewPreparingState.style.display = 'none';
                    tryonHonestAlertCard.style.display = 'block';
                    if (honestAlertHeading) honestAlertHeading.textContent = 'Virtual Try-On AI is not connected yet.';
                    if (honestAlertDesc) honestAlertDesc.textContent = genData.message || 'Your photo and selected product are ready. Set REPLICATE_API_TOKEN in .env for real AI generation.';
                    if (honestPhotoReady) honestPhotoReady.textContent = `✓ Photo Ready (Uploaded): ${selectedPhotoFile.name}`;
                    if (honestProductReady) honestProductReady.textContent = `✓ Garment Selected: ${selectedProduct.name}`;
                } else {
                    // Generation failed on server
                    throw new Error(genData.message || 'Virtual try-on could not be generated right now. Please try again.');
                }
            } catch (err) {
                console.error('Virtual Try-On Generation Error:', err);
                previewPreparingState.style.display = 'none';
                if (previewErrorState) {
                    previewErrorState.style.display = 'flex';
                    if (previewErrorTitle) previewErrorTitle.textContent = 'Virtual try-on could not be generated right now.';
                    if (previewErrorMsg) previewErrorMsg.textContent = err.message || 'Please check your connection and try again.';
                } else {
                    previewDefaultPlaceholder.style.display = 'block';
                }
                if (typeof showToast === 'function') {
                    showToast(err.message || 'Virtual try-on could not be generated right now.');
                }
            }
        });
    }

    // --- Action Buttons Suite ---
    // 1. Add to Cart Button
    if (resultAddToCartBtn) {
        resultAddToCartBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            if (!currentGeneratedProductId) return;

            const url = `/add_to_cart/${currentGeneratedProductId}`;
            try {
                const res = await fetch(url, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                });
                if (res.ok) {
                    const data = await res.json().catch(() => ({}));
                    if (typeof showToast === 'function') {
                        showToast(data.message || 'Item added to your shopping bag!');
                    }
                    const cartBadges = document.querySelectorAll('#cartCountBadge, .cart-badge, .cart-count-pill');
                    if (data.count !== undefined) {
                        cartBadges.forEach(badge => badge.textContent = data.count);
                    }
                } else {
                    window.location.href = url;
                }
            } catch (err) {
                window.location.href = url;
            }
        });
    }

    // 2. Add to Wishlist Button
    if (resultAddToWishlistBtn) {
        resultAddToWishlistBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            if (!currentGeneratedProductId) return;

            const toggleUrl = `/toggle_wishlist/${currentGeneratedProductId}`;
            try {
                const res = await fetch(toggleUrl, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Content-Type': 'application/json'
                    }
                });

                if (res.status === 401) {
                    const data = await res.json().catch(() => ({}));
                    window.location.href = data.redirect || `/login?next=${encodeURIComponent(window.location.pathname)}`;
                    return;
                }

                if (res.ok) {
                    const data = await res.json().catch(() => ({}));
                    if (typeof showToast === 'function') {
                        showToast(data.message || (data.in_wishlist ? 'Added to wishlist!' : 'Removed from wishlist!'));
                    }
                    const wishlistBadges = document.querySelectorAll('#wishlistCountBadge, .wishlist-count-pill');
                    if (data.count !== undefined) {
                        wishlistBadges.forEach(badge => {
                            badge.textContent = data.count;
                            badge.style.display = data.count > 0 ? '' : 'none';
                        });
                    }
                }
            } catch (err) {
                window.location.href = toggleUrl;
            }
        });
    }

    // 3. Try Another Garment Button
    if (resultTryAnotherBtn) {
        resultTryAnotherBtn.addEventListener('click', (e) => {
            e.preventDefault();
            // Reset result view to readiness state while preserving uploaded photo
            if (tryonRealResultView) tryonRealResultView.style.display = 'none';
            if (previewDefaultPlaceholder) previewDefaultPlaceholder.style.display = 'block';
            disableResultActions();

            // Scroll smoothly up to the catalog selection grid
            const catalogGrid = document.getElementById('tryonProductScrollGrid');
            if (catalogGrid) {
                catalogGrid.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            if (typeof showToast === 'function') {
                showToast('Choose another garment from the catalog to try on.');
            }
        });
    }

    // 4. Save Preview Button
    if (resultSavePreviewBtn) {
        resultSavePreviewBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (!currentGeneratedResultUrl) return;

            // Trigger direct safe browser image download
            const link = document.createElement('a');
            link.href = currentGeneratedResultUrl;
            link.download = `fashion_world_tryon_${Date.now()}.jpg`;
            link.target = '_blank';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            if (typeof showToast === 'function') {
                showToast('Saving try-on preview...');
            }
        });
    }

    // Initial State Sync
    updateGenerateButtonState();
});
