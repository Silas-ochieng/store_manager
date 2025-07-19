document.addEventListener('DOMContentLoaded', function() {
    console.log('Orders app JavaScript loaded');

    // Navigate to order detail when clicking a row, except on links/buttons
    document.querySelectorAll('.order-table tr').forEach(row => {
        row.addEventListener('click', function(e) {
            const tag = e.target.tagName;
            if (tag === 'A' || tag === 'BUTTON' || tag === 'INPUT' || tag === 'SELECT') {
                // Prevent navigation if interacting with actionable elements
                return;
            }

            const viewLink = this.querySelector('a.btn-view');
            if (viewLink) {
                window.location = viewLink.href;
            }
        });
    });

    // Submit the status filter form on change
    const statusFilter = document.querySelector('select[name="status"]');
    if (statusFilter) {
        statusFilter.addEventListener('change', function() {
            if(this.form) {
                this.form.submit();
            }
        });
    }

    // Image preview for Customer image upload inputs
    const imageInputs = document.querySelectorAll('input[type="file"][name="image"]');
    imageInputs.forEach(input => {
        input.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                const previewId = input.getAttribute('data-preview-id');
                const previewImg = document.getElementById(previewId);
                if (previewImg) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        previewImg.src = e.target.result;
                        previewImg.style.display = 'block';
                    };
                    reader.readAsDataURL(file);
                }
            }
        });
    });
});
