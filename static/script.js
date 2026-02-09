// Main application script
document.addEventListener('DOMContentLoaded', function() {
    console.log('Main app script loaded, current URL:', window.location.href);
    initializeApp();
});

async function initializeApp() {
    // Check if we're on the right page
    if (window.location.pathname !== '/app') {
        console.log('Not on /app page, redirecting to login');
        window.location.replace('/');
        return;
    }
    
    // Check authentication first and wait for it
    const isAuthenticated = await checkAuthentication();
    
    // Only proceed if authentication is successful
    if (!isAuthenticated) {
        return;
    }
    
    console.log('Initializing authenticated app...');
    
    // Initialize forms
    const storeForm = document.getElementById('storeForm');
    const retrieveForm = document.getElementById('retrieveForm');
    const deleteForm = document.getElementById('deleteForm');
    const analyzeBtn = document.getElementById('analyzeBtn');
    
    if (storeForm) {
        storeForm.addEventListener('submit', handleStore);
    }
    
    if (retrieveForm) {
        retrieveForm.addEventListener('submit', handleRetrieve);
    }
    
    if (deleteForm) {
        deleteForm.addEventListener('submit', handleDelete);
    }
    
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', handleAnalyze);
    }
    
    // Initialize tab navigation
    initializeTabs();
    
    // Load initial data only after authentication is verified
    loadUserInfo();
    loadKeys();
    loadBackendInfo();
}

// Authentication functions
async function checkAuthentication() {
    const token = localStorage.getItem('session_token');
    if (!token) {
        console.log('No session token found, redirecting to login');
        window.location.replace('/');
        return false;
    }
    
    try {
        const response = await fetch('http://localhost:8000/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Authentication failed');
        }
        
        const result = await response.json();
        localStorage.setItem('user_info', JSON.stringify(result.user));
        console.log('Authentication successful for user:', result.user.username);
        return true;
        
    } catch (error) {
        console.log('Authentication failed:', error);
        localStorage.removeItem('session_token');
        localStorage.removeItem('user_info');
        window.location.replace('/');
        return false;
    }
}

async function loadUserInfo() {
    const userInfo = localStorage.getItem('user_info');
    if (userInfo) {
        const user = JSON.parse(userInfo);
        const usernameDisplay = document.getElementById('username-display');
        const userRole = document.getElementById('user-role');
        
        if (usernameDisplay) {
            usernameDisplay.textContent = user.username;
        }
        
        if (userRole) {
            userRole.textContent = user.role.charAt(0).toUpperCase() + user.role.slice(1);
            userRole.className = `user-role role-${user.role}`;
        }
    }
}

async function logout() {
    try {
        const token = localStorage.getItem('session_token');
        if (token) {
            await fetch('http://localhost:8000/logout', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
        }
    } catch (error) {
        console.log('Logout error:', error);
    } finally {
        localStorage.removeItem('session_token');
        localStorage.removeItem('user_info');
        window.location.href = '/';
    }
}

// Helper function to get auth headers
function getAuthHeaders() {
    const token = localStorage.getItem('session_token');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

// Tab Management
function initializeTabs() {
    const menuItems = document.querySelectorAll('.menu-item');
    menuItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const tabName = this.getAttribute('data-tab');
            switchTab(tabName);
        });
    });
}

function navigateToOperation(operation) {
    console.log('navigateToOperation called with:', operation);
    
    // Switch to operations tab first
    switchTab('operations');
    
    // Scroll to the specific operation section after a brief delay
    setTimeout(() => {
        const operationIds = {
            'store': 'storeForm',
            'retrieve': 'retrieveForm', 
            'delete': 'deleteForm'
        };
        
        const targetId = operationIds[operation];
        if (targetId) {
            const element = document.getElementById(targetId);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                // Add a visual highlight effect
                element.style.border = '2px solid #007bff';
                setTimeout(() => {
                    element.style.border = '';
                }, 2000);
                console.log('Navigated to operation:', operation);
            } else {
                console.log('Operation element not found:', targetId);
            }
        } else {
            console.log('Unknown operation:', operation);
        }
    }, 100);
}

function switchTab(tabName) {
    console.log('switchTab called with:', tabName);
    
    // Update active menu item
    document.querySelectorAll('.menu-item').forEach(item => {
        item.classList.remove('active');
    });
    const menuItem = document.querySelector(`[data-tab="${tabName}"]`);
    if (menuItem) {
        menuItem.classList.add('active');
        console.log('Activated menu item for:', tabName);
    } else {
        console.log('Menu item not found for:', tabName);
    }
    
    // Update active tab content
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    const tabContent = document.getElementById(tabName);
    if (tabContent) {
        tabContent.classList.add('active');
        console.log('Activated tab content for:', tabName);
    } else {
        console.log('Tab content not found for:', tabName);
    }
    
    // Update page title and description
    const titles = {
        'operations': { title: 'Operations', desc: 'Store, retrieve, and manage your encrypted key-value data', icon: 'fas fa-database' },
        'keys': { title: 'Keys', desc: 'Browse and manage all your stored keys', icon: 'fas fa-key' },
        'analytics': { title: 'Analytics', desc: 'View usage patterns and performance metrics', icon: 'fas fa-chart-line' },
        'settings': { title: 'Settings', desc: 'Configure your key-value store', icon: 'fas fa-cog' }
    };
    
    const pageInfo = titles[tabName];
    document.getElementById('page-title').innerHTML = `<i class="${pageInfo.icon}"></i> ${pageInfo.title}`;
    document.getElementById('page-description').textContent = pageInfo.desc;
    
    // Load data for specific tabs
    if (tabName === 'keys') {
        loadKeys();
    } else if (tabName === 'analytics') {
        loadStats();
    }
}

// Key Management
async function loadKeys() {
    const keysList = document.getElementById('keysList');
    const keysLoading = document.getElementById('keysLoading');
    
    if (!keysList || !keysLoading) return;
    
    // Check if we have a valid session token
    const token = localStorage.getItem('session_token');
    if (!token) return;
    
    keysList.classList.add('hidden');
    keysLoading.classList.remove('hidden');
    
    try {
        const response = await fetch('http://localhost:8000/keys', {
            headers: getAuthHeaders()
        });
        const result = await response.json();
        
        if (response.ok) {
            displayKeys(result.keys || []);
        } else {
            throw new Error('Failed to load keys');
        }
    } catch (error) {
        keysList.innerHTML = `
            <div class="error">
                <i class="fas fa-exclamation-circle"></i>
                <p>Error loading keys: ${error.message}</p>
            </div>
        `;
    } finally {
        keysLoading.classList.add('hidden');
        keysList.classList.remove('hidden');
    }
}

function displayKeys(keys) {
    const keysList = document.getElementById('keysList');
    
    if (keys.length === 0) {
        keysList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-key"></i>
                <h3>No Keys Found</h3>
                <p>Start by storing some data to see your keys here.</p>
            </div>
        `;
        return;
    }
    
    keysList.innerHTML = keys.map(key => `
        <div class="key-item" onclick="retrieveKey('${key}')">
            <h3><i class="fas fa-key"></i> ${key}</h3>
            <p>Click to retrieve data</p>
        </div>
    `).join('');
}

async function retrieveKey(key) {
    document.getElementById('retrieveKey').value = key;
    switchTab('operations');
    
    // Auto-trigger retrieval
    setTimeout(() => {
        const retrieveForm = document.getElementById('retrieveForm');
        if (retrieveForm) {
            retrieveForm.dispatchEvent(new Event('submit'));
        }
    }, 100);
}

// System Information
async function loadBackendInfo() {
    // Check if we have a valid session token
    const token = localStorage.getItem('session_token');
    if (!token) return;
    
    try {
        const response = await fetch('http://localhost:8000/stats', {
            headers: getAuthHeaders()
        });
        const result = await response.json();
        
        if (response.ok) {
            const backendInfo = document.getElementById('backend-info');
            if (backendInfo) {
                backendInfo.textContent = `SQLite (${result.total_keys || 0} keys) or Redis (cloud)`;
            }
        }
    } catch (error) {
        console.log('Could not load backend info:', error);
    }
}

async function loadStats() {
    console.log('loadStats() called');
    const statsResult = document.getElementById('statsResult');
    if (!statsResult) {
        console.log('statsResult element not found');
        return;
    }
    
    // Check if we have a valid session token
    const token = localStorage.getItem('session_token');
    if (!token) {
        console.log('No session token found');
        return;
    }
    
    console.log('Loading stats with token:', token.substring(0, 10) + '...');
    
    try {
        const response = await fetch('http://localhost:8000/stats', {
            headers: getAuthHeaders()
        });
        const result = await response.json();
        
        if (response.ok) {
            statsResult.innerHTML = `
                <div class="analysis">
                    <h3><i class="fas fa-info-circle"></i> System Statistics</h3>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <h4>Total Keys</h4>
                            <p class="stat-number">${result.total_keys || 0}</p>
                        </div>
                        <div class="stat-card">
                            <h4>Total Size</h4>
                            <p class="stat-number">${formatBytes(result.total_size_bytes || 0)}</p>
                        </div>
                        <div class="stat-card">
                            <h4>Encrypted</h4>
                            <p class="stat-number">${result.encrypted_keys || 0}</p>
                        </div>
                        <div class="stat-card">
                            <h4>Compressed</h4>
                            <p class="stat-number">${result.compressed_keys || 0}</p>
                        </div>
                    </div>
                    ${result.top_accessed_keys && result.top_accessed_keys.length > 0 ? `
                        <div class="analysis-section">
                            <h4>Most Accessed Keys</h4>
                            <ul class="key-list">
                                ${result.top_accessed_keys.map(key => 
                                    `<li><span class="key-name">${key.key}</span> <span class="access-count">${key.access_count} accesses</span></li>`
                                ).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
            `;
        } else {
            throw new Error('Failed to load stats');
        }
    } catch (error) {
        statsResult.innerHTML = `
            <div class="error">
                <i class="fas fa-exclamation-circle"></i>
                <p>Error loading stats: ${error.message}</p>
            </div>
        `;
    }
}

// Utility Functions
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function clearForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
        // Clear result area
        const resultId = formId.replace('Form', 'Result');
        const result = document.getElementById(resultId);
        if (result) {
            result.innerHTML = '';
        }
    }
}

async function handleStore(e) {
    e.preventDefault();
    
    const key = document.getElementById('key').value;
    const valueText = document.getElementById('value').value;
    const encrypt = document.getElementById('encrypt').checked;
    const compress = document.getElementById('compress').checked;
    
    try {
        // Parse JSON value
        let value;
        try {
            value = JSON.parse(valueText);
        } catch (e) {
            // If not valid JSON, treat as string
            value = valueText;
        }
        
        showLoading('storeResult');
        
        const response = await fetch('http://localhost:8000/store', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                key: key,
                value: value,
                encrypt: encrypt,
                compress: compress
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showResult('storeResult', {
                success: true,
                message: 'Data stored successfully!',
                data: result
            });
        } else {
            throw new Error(result.detail || 'Failed to store data');
        }
    } catch (error) {
        showResult('storeResult', {
            success: false,
            message: 'Error storing data: ' + error.message
        });
    }
}

async function handleRetrieve(e) {
    e.preventDefault();
    
    const key = document.getElementById('retrieveKey').value;
    
    try {
        showLoading('retrieveResult');
        
        const response = await fetch(`http://localhost:8000/retrieve/${encodeURIComponent(key)}`, {
            headers: getAuthHeaders()
        });
        const result = await response.json();
        
        if (response.ok) {
            showResult('retrieveResult', {
                success: true,
                message: 'Data retrieved successfully!',
                data: result
            });
        } else {
            throw new Error(result.detail || 'Failed to retrieve data');
        }
    } catch (error) {
        showResult('retrieveResult', {
            success: false,
            message: 'Error retrieving data: ' + error.message
        });
    }
}

async function handleDelete(e) {
    e.preventDefault();
    
    const key = document.getElementById('deleteKey').value;
    
    if (!confirm(`Are you sure you want to delete key "${key}"?`)) {
        return;
    }
    
    try {
        showLoading('deleteResult');
        
        const response = await fetch(`http://localhost:8000/delete/${encodeURIComponent(key)}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showResult('deleteResult', {
                success: true,
                message: result.message || 'Key deleted successfully!'
            });
        } else {
            throw new Error(result.detail || 'Failed to delete data');
        }
    } catch (error) {
        showResult('deleteResult', {
            success: false,
            message: 'Error deleting data: ' + error.message
        });
    }
}

// Store chart instances to destroy when re-rendering
let analysisCharts = [];

function destroyAnalysisCharts() {
    analysisCharts.forEach(chart => { if (chart) chart.destroy(); });
    analysisCharts = [];
}

function renderAnalysisCharts(patterns) {
    if (typeof Chart === 'undefined') return;
    destroyAnalysisCharts();

    const chartColors = {
        read: 'rgba(0, 123, 255, 0.8)',
        write: 'rgba(40, 167, 69, 0.8)',
        delete: 'rgba(220, 53, 69, 0.8)',
        bar: ['#007bff', '#17a2b8', '#20c997', '#28a745', '#ffc107', '#fd7e14', '#e83e8c', '#6f42c1']
    };

    // 1. Operation Distribution - Doughnut
    const opDistCtx = document.getElementById('chartOperationDist');
    if (opDistCtx) {
        const opData = patterns.operation_distribution || {};
        const opLabels = Object.keys(opData).map(k => k.charAt(0).toUpperCase() + k.slice(1));
        const opValues = Object.values(opData);
        const opColors = opLabels.map(l => chartColors[l.toLowerCase()] || chartColors.bar[0]);
        if (opValues.length > 0 && opValues.some(v => v > 0)) {
            analysisCharts.push(new Chart(opDistCtx, {
                type: 'doughnut',
                data: { labels: opLabels, datasets: [{ data: opValues, backgroundColor: opColors, borderWidth: 2 }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
            }));
        } else {
            opDistCtx.parentElement.innerHTML = '<p class="chart-no-data">No operation data yet</p>';
        }
    }

    // 2. Daily Access Patterns - Bar
    const dailyCtx = document.getElementById('chartDailyAccess');
    if (dailyCtx) {
        const dailyData = patterns.daily_access_patterns || {};
        const dailyLabels = Object.keys(dailyData).sort().slice(-14);
        const dailyValues = dailyLabels.map(d => dailyData[d] || 0);
        if (dailyLabels.length > 0) {
            analysisCharts.push(new Chart(dailyCtx, {
                type: 'bar',
                data: {
                    labels: dailyLabels,
                    datasets: [{ label: 'Accesses', data: dailyValues, backgroundColor: chartColors.bar[0], borderRadius: 6 }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
                }
            }));
        } else {
            dailyCtx.parentElement.innerHTML = '<p class="chart-no-data">No daily data (SQLite only)</p>';
        }
    }

    // 3. Top Accessed Keys - Bar
    const topKeysCtx = document.getElementById('chartTopKeys');
    if (topKeysCtx) {
        const topKeys = patterns.top_accessed_keys || [];
        const keyLabels = topKeys.map(k => k.key);
        const keyValues = topKeys.map(k => k.access_count);
        if (keyLabels.length > 0) {
            analysisCharts.push(new Chart(topKeysCtx, {
                type: 'bar',
                data: {
                    labels: keyLabels,
                    datasets: [{ label: 'Access Count', data: keyValues, backgroundColor: chartColors.bar[2], borderRadius: 6 }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } }
                }
            }));
        } else {
            topKeysCtx.parentElement.innerHTML = '<p class="chart-no-data">No key access data yet</p>';
        }
    }

    // 4. Response Time Stats - Bar (always show)
    const rtCtx = document.getElementById('chartResponseTime');
    if (rtCtx) {
        const rt = patterns.response_time_stats || { avg_ms: 0, min_ms: 0, max_ms: 0 };
        const rtLabels = ['Min (ms)', 'Avg (ms)', 'Max (ms)'];
        const rtValues = [rt.min_ms || 0, rt.avg_ms || 0, rt.max_ms || 0];
        analysisCharts.push(new Chart(rtCtx, {
            type: 'bar',
            data: {
                labels: rtLabels,
                datasets: [{ label: 'Response Time (ms)', data: rtValues, backgroundColor: [chartColors.bar[4], chartColors.bar[0], chartColors.bar[5]], borderRadius: 6 }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } }
            }
        }));
    }
}

async function showPatternLogs() {
    console.log('showPatternLogs() called');
    try {
        showLoading('analysisResult');
        
        const response = await fetch('http://localhost:8000/analysis', {
            headers: getAuthHeaders()
        });
        const result = await response.json();
        
        if (response.ok) {
            const analysisResult = document.getElementById('analysisResult');
            const patterns = result.access_patterns;
            
            analysisResult.innerHTML = `
                <div class="analysis">
                    <h3><i class="fas fa-chart-line"></i> Pattern Analysis with Graphs</h3>
                    <p class="data-timestamp"><i class="fas fa-clock"></i> Data updated: ${new Date().toLocaleString()}</p>
                    
                    <div class="charts-grid">
                        <div class="chart-card">
                            <h4><i class="fas fa-chart-pie"></i> 1. Operation Distribution</h4>
                            <div class="chart-container"><canvas id="chartOperationDist"></canvas></div>
                        </div>
                        <div class="chart-card">
                            <h4><i class="fas fa-calendar-day"></i> 2. Daily Access Patterns</h4>
                            <div class="chart-container"><canvas id="chartDailyAccess"></canvas></div>
                        </div>
                        <div class="chart-card">
                            <h4><i class="fas fa-key"></i> 3. Top Accessed Keys</h4>
                            <div class="chart-container"><canvas id="chartTopKeys"></canvas></div>
                        </div>
                        <div class="chart-card">
                            <h4><i class="fas fa-tachometer-alt"></i> 4. Response Time (ms)</h4>
                            <div class="chart-container"><canvas id="chartResponseTime"></canvas></div>
                        </div>
                    </div>
                    
                    <div class="pattern-logs">
                        <h4><i class="fas fa-tachometer-alt"></i> Performance Stats</h4>
                        <div class="performance-stats">
                            <div class="stat-item"><span class="stat-label">Total Accesses:</span> <span class="stat-value">${patterns.total_accesses || 0}</span></div>
                            <div class="stat-item"><span class="stat-label">Unique Keys:</span> <span class="stat-value">${patterns.unique_keys_accessed || 0}</span></div>
                            <div class="stat-item"><span class="stat-label">Avg Response Time:</span> <span class="stat-value">${Math.round(patterns.response_time_stats?.avg_ms || 0)}ms</span></div>
                        </div>

                        <h4><i class="fas fa-history"></i> Recent Access History</h4>
                        <div class="recent-access-history">
                            ${patterns.recent_access_history && patterns.recent_access_history.length > 0 ? 
                                patterns.recent_access_history.map(entry => `
                                    <div class="access-entry">
                                        <div class="access-main">
                                            <span class="access-key">${entry.key}</span>
                                            <span class="access-operation ${entry.operation}">${entry.operation.toUpperCase()}</span>
                                            <span class="access-datetime"><i class="fas fa-calendar"></i> ${entry.date} <i class="fas fa-clock"></i> ${entry.time}</span>
                                        </div>
                                        <div class="access-details">
                                            <span class="access-duration"><i class="fas fa-tachometer-alt"></i> ${entry.response_time_ms}ms</span>
                                            <span class="access-size"><i class="fas fa-weight"></i> ${entry.data_size ? entry.data_size + ' bytes' : 'N/A'}</span>
                                        </div>
                                    </div>
                                `).join('') : '<p>No recent access history available</p>'}
                        </div>
                    </div>
                </div>
            `;
            
            setTimeout(() => renderAnalysisCharts(patterns), 50);
        } else {
            showResult('analysisResult', { success: false, message: 'Failed to load pattern logs: ' + result.message });
        }
    } catch (error) {
        console.error('Error loading pattern logs:', error);
        showResult('analysisResult', { success: false, message: 'Error loading pattern logs: ' + error.message });
    }
}

async function handleAnalyze() {
    console.log('handleAnalyze() called');
    await showPatternLogs();
}

function showLoading(elementId) {
    const element = document.getElementById(elementId);
    element.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Processing...</div>';
}

function showResult(elementId, result) {
    const element = document.getElementById(elementId);
    
    if (result.success) {
        const metrics = result.data ? `
            <div class="metrics">
                ${result.data.size_bytes !== undefined ? `<div><strong>Size:</strong> ${result.data.size_bytes} bytes</div>` : ''}
                ${result.data.duration_ms !== undefined ? `<div><strong>Duration:</strong> ${result.data.duration_ms.toFixed(2)} ms</div>` : ''}
            </div>
        ` : '';
        element.innerHTML = `
            <div class="success">
                <i class="fas fa-check-circle"></i>
                <p>${result.message}</p>
                ${metrics}
                ${result.data ? `<pre>${JSON.stringify(result.data, null, 2)}</pre>` : ''}
            </div>
        `;
    } else {
        element.innerHTML = `
            <div class="error">
                <i class="fas fa-exclamation-circle"></i>
                <p>${result.message}</p>
            </div>
        `;
    }
}

function showAnalysisResult(elementId, analysis) {
    const element = document.getElementById(elementId);
    
    element.innerHTML = `
        <div class="analysis">
            <h3><i class="fas fa-chart-line"></i> Pattern Analysis Results</h3>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h4>Total Keys</h4>
                    <p class="stat-number">${analysis.total_keys}</p>
                </div>
                <div class="stat-card">
                    <h4>Total Accesses</h4>
                    <p class="stat-number">${analysis.access_patterns.total_accesses}</p>
                </div>
                <div class="stat-card">
                    <h4>Encrypted Keys</h4>
                    <p class="stat-number">${analysis.encryption_stats.encrypted_keys}</p>
                </div>
                <div class="stat-card">
                    <h4>Compressed Keys</h4>
                    <p class="stat-number">${analysis.compression_stats.compressed_keys}</p>
                </div>
            </div>
            
            <div class="analysis-section">
                <h4>Top Accessed Keys</h4>
                <ul class="key-list">
                    ${analysis.access_patterns.top_accessed_keys.map(key => 
                        `<li><span class="key-name">${key.key}</span> <span class="access-count">${key.access_count} accesses</span></li>`
                    ).join('')}
                </ul>
            </div>
            
            <div class="analysis-section">
                <h4>Recommendations</h4>
                <ul class="recommendations">
                    ${analysis.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                </ul>
            </div>
        </div>
    `;
}
