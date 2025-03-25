/**
 * Main JavaScript for McSM - Minecraft Server Manager
 */

// Format file size for display
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Format date for display
function formatDate(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
}

// Format elapsed time
function formatElapsedTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    let result = '';
    if (hours > 0) {
        result += hours + 'h ';
    }
    if (minutes > 0 || hours > 0) {
        result += minutes + 'm ';
    }
    result += secs + 's';
    
    return result;
}

// Add a toast notification
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.classList.add('toast-container', 'position-fixed', 'bottom-0', 'end-0', 'p-3');
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.classList.add('toast', 'align-items-center', 'border-0');
    toast.classList.add(type === 'error' ? 'bg-danger' : type === 'success' ? 'bg-success' : 'bg-primary');
    toast.classList.add('text-white');
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    // Create toast content
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // Add to container
    toastContainer.appendChild(toast);
    
    // Initialize and show toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove after hiding
    toast.addEventListener('hidden.bs.toast', function () {
        toast.remove();
    });
}

// Check if a string contains HTML
function containsHTML(str) {
    const doc = new DOMParser().parseFromString(str, 'text/html');
    return Array.from(doc.body.childNodes).some(node => node.nodeType === 1);
}

// Escape HTML
function escapeHTML(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Create a confirmation dialog
function confirmDialog(message, callback) {
    // Check if modal container exists
    let modalContainer = document.getElementById('confirm-modal-container');
    if (!modalContainer) {
        modalContainer = document.createElement('div');
        modalContainer.id = 'confirm-modal-container';
        document.body.appendChild(modalContainer);
    }
    
    // Create modal HTML
    const modalId = 'confirm-modal-' + Date.now();
    modalContainer.innerHTML = `
        <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}-label" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="${modalId}-label">Confirmation</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        ${escapeHTML(message)}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="${modalId}-confirm">Confirm</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Get modal element
    const modalElement = document.getElementById(modalId);
    
    // Initialize modal
    const modal = new bootstrap.Modal(modalElement);
    
    // Add event listener to confirm button
    document.getElementById(`${modalId}-confirm`).addEventListener('click', function() {
        callback(true);
        modal.hide();
    });
    
    // Add event listener to modal hidden event
    modalElement.addEventListener('hidden.bs.modal', function() {
        modalElement.remove();
    });
    
    // Show modal
    modal.show();
}

// Document ready event
document.addEventListener('DOMContentLoaded', function() {
    // Enable tooltips everywhere
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Enable popovers everywhere
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});