document.addEventListener('DOMContentLoaded', () => {
    console.log('Inventory app JavaScript initialized');
    
    // Constants
    const LOW_STOCK_THRESHOLD = 5;
    const CRITICAL_STOCK_THRESHOLD = 2;
    
    // DOM Elements
    const productTable = document.querySelector('.product-table');
    const deleteButtons = document.querySelectorAll('.btn-delete');
    const filterForms = document.querySelectorAll('.filter-form');
    const stockAlerts = document.querySelectorAll('.stock-alert');
    const barcodeInputs = document.querySelectorAll('.barcode-input');
    const quickAddForms = document.querySelectorAll('.quick-add-form');
    
    // 1. Stock Level Highlighting
    const highlightStockLevels = () => {
        if (!productTable) return;
        
        productTable.querySelectorAll('tbody tr').forEach(row => {
            const stockCell = row.querySelector('.stock-quantity');
            const reorderCell = row.querySelector('.reorder-level');
            
            if (stockCell && reorderCell) {
                const quantity = parseInt(stockCell.textContent);
                const reorderLevel = parseInt(reorderCell.textContent) || LOW_STOCK_THRESHOLD;
                
                row.classList.remove('low-stock-row', 'critical-stock-row');
                
                if (quantity <= CRITICAL_STOCK_THRESHOLD) {
                    row.classList.add('critical-stock-row');
                    const alertIcon = document.createElement('span');
                    alertIcon.className = 'stock-alert-icon tw-ml-2';
                    alertIcon.innerHTML = '⚠️';
                    stockCell.appendChild(alertIcon);
                } else if (quantity <= reorderLevel) {
                    row.classList.add('low-stock-row');
                }
            }
        });
    };
    
    // 2. Delete Confirmation with SweetAlert (if available)
    const setupDeleteConfirmations = () => {
        deleteButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const productName = btn.dataset.productName || 'this item';
                
                if (window.Swal) {
                    Swal.fire({
                        title: 'Confirm Deletion',
                        text: `Are you sure you want to delete ${productName}?`,
                        icon: 'warning',
                        showCancelButton: true,
                        confirmButtonColor: '#ef4444',
                        confirmButtonText: 'Delete',
                        cancelButtonText: 'Cancel'
                    }).then((result) => {
                        if (result.isConfirmed) {
                            window.location = btn.href;
                        }
                    });
                } else if (!confirm(`Are you sure you want to delete ${productName}?`)) {
                    e.preventDefault();
                }
            });
        });
    };
    
    // 3. Auto-submit Filters with debounce
    const setupFilterForms = () => {
        filterForms.forEach(form => {
            const inputs = form.querySelectorAll('select, input');
            
            inputs.forEach(input => {
                // Debounce for text inputs
                if (input.type === 'text') {
                    let timeout;
                    input.addEventListener('input', () => {
                        clearTimeout(timeout);
                        timeout = setTimeout(() => form.submit(), 500);
                    });
                } else {
                    // Immediate submit for selects/checkboxes
                    input.addEventListener('change', () => form.submit());
                }
            });
        });
    };
    
    // 4. Clickable Rows with proper delegation
    const setupClickableRows = () => {
        if (productTable) {
            productTable.addEventListener('click', (e) => {
                const row = e.target.closest('tr[data-url]');
                if (!row) return;
                
                // Ignore if clicking on interactive elements
                if (e.target.closest('a, button, .no-row-click')) {
                    return;
                }
                
                window.location.href = row.dataset.url;
            });
        }
    };
    
    // 5. Stock Alert Notifications
    const checkStockAlerts = () => {
        stockAlerts.forEach(alert => {
            const remaining = parseInt(alert.dataset.remaining) || 0;
            const threshold = parseInt(alert.dataset.threshold) || LOW_STOCK_THRESHOLD;
            
            if (remaining <= threshold) {
                alert.classList.add('active');
                
                // Only show browser notification once per page load
                if (!alert.dataset.notified && window.Notification && Notification.permission === 'granted') {
                    new Notification('Low Stock Alert', {
                        body: `${alert.dataset.productName} is low on stock (${remaining} remaining)`
                    });
                    alert.dataset.notified = 'true';
                }
            }
        });
    };
    
    // 6. Barcode Scanner Enhancement
    const setupBarcodeInputs = () => {
        barcodeInputs.forEach(input => {
            let lastScan = 0;
            
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    const now = Date.now();
                    // Detect rapid entry (likely barcode scanner)
                    if (now - lastScan < 100) {
                        input.dispatchEvent(new Event('barcode-scanned'));
                    }
                    lastScan = now;
                }
            });
            
            input.addEventListener('barcode-scanned', () => {
                const form = input.closest('form');
                if (form) form.submit();
            });
        });
    };
    
    // 7. Quick Add Forms
    const setupQuickAddForms = () => {
        quickAddForms.forEach(form => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const submitBtn = form.querySelector('[type="submit"]');
                const originalText = submitBtn.value;
                
                try {
                    submitBtn.disabled = true;
                    submitBtn.value = 'Processing...';
                    
                    const response = await fetch(form.action, {
                        method: 'POST',
                        body: new FormData(form),
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });
                    
                    if (response.ok) {
                        const result = await response.json();
                        if (result.success) {
                            window.location.reload();
                        } else {
                            alert(result.message || 'Error adding item');
                        }
                    } else {
                        throw new Error('Network response was not ok');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    alert('There was an error processing your request');
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.value = originalText;
                }
            });
        });
    };
    
    // 8. Keyboard Shortcuts
    const setupKeyboardShortcuts = () => {
        document.addEventListener('keydown', (e) => {
            // Ctrl+Alt+N for new product (when not in input)
            if (e.ctrlKey && e.altKey && e.key === 'n' && !['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
                const newBtn = document.querySelector('.btn-add');
                if (newBtn) newBtn.click();
            }
        });
    };
    
    // Initialize all functionality
    highlightStockLevels();
    setupDeleteConfirmations();
    setupFilterForms();
    setupClickableRows();
    checkStockAlerts();
    setupBarcodeInputs();
    setupQuickAddForms();
    setupKeyboardShortcuts();
    
    // Expose functions for Turbolinks/etc. if needed
    window.InventoryApp = {
        refresh: highlightStockLevels
    };
});