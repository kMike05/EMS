/**
 * Dashboard JavaScript functionality
 * Handles chart initialization and dynamic data loading
 */

// Initialize financial chart for dashboard
function initializeFinancialChart() {
    fetch('/api/dashboard-data')
        .then(response => response.json())
        .then(data => {
            const ctx = document.getElementById('financialChart');
            if (!ctx) return;
            
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.map(week => week.week),
                    datasets: [
                        {
                            label: 'Revenue',
                            data: data.map(week => week.revenue),
                            backgroundColor: 'rgba(25, 135, 84, 0.8)',
                            borderColor: 'rgb(25, 135, 84)',
                            borderWidth: 1
                        },
                        {
                            label: 'Employee Payments',
                            data: data.map(week => week.payments),
                            backgroundColor: 'rgba(255, 193, 7, 0.8)',
                            borderColor: 'rgb(255, 193, 7)',
                            borderWidth: 1
                        },
                        {
                            label: 'Expenses',
                            data: data.map(week => week.expenses),
                            backgroundColor: 'rgba(220, 53, 69, 0.8)',
                            borderColor: 'rgb(220, 53, 69)',
                            borderWidth: 1
                        },
                        {
                            label: 'Net Profit',
                            data: data.map(week => week.profit),
                            backgroundColor: 'rgba(13, 202, 240, 0.8)',
                            borderColor: 'rgb(13, 202, 240)',
                            borderWidth: 2,
                            type: 'line'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Weekly Financial Overview (Last 4 Weeks)'
                        },
                        legend: {
                            position: 'top'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return value.toLocaleString() + ' KSH';
                                }
                            }
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error loading dashboard data:', error);
        });
}

// Format currency values
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-KE', {
        style: 'currency',
        currency: 'KES',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

// Update live metrics (could be called periodically)
function updateLiveMetrics() {
    // This function could fetch updated metrics via AJAX
    // For now, it's a placeholder for future enhancements
    console.log('Live metrics update - placeholder');
}

// Initialize tooltips for Bootstrap components
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips if any exist
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize Bootstrap popovers if any exist
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// Auto-refresh functionality (optional)
let autoRefreshInterval;

function startAutoRefresh(intervalMinutes = 5) {
    autoRefreshInterval = setInterval(() => {
        updateLiveMetrics();
    }, intervalMinutes * 60 * 1000);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// Utility functions for form validation
function validatePositiveNumber(value) {
    return !isNaN(value) && parseFloat(value) > 0;
}

function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Export functions for use in other scripts
window.dashboardUtils = {
    initializeFinancialChart,
    formatCurrency,
    updateLiveMetrics,
    startAutoRefresh,
    stopAutoRefresh,
    validatePositiveNumber,
    validateEmail
};
