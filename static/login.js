// Login page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    console.log('Login page loaded');
    initializeLogin();
});

function initializeLogin() {
    console.log('Initializing login page...');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
    
    // Check if already logged in
    checkAuthStatus();
}

async function checkAuthStatus() {
    const token = localStorage.getItem('session_token');
    if (token) {
        try {
            const response = await fetch('http://localhost:8000/me', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
        if (response.ok) {
            // Already logged in, redirect to main app
            window.location.href = '/app';
            return;
        }
        } catch (error) {
            // Invalid token, remove it
            localStorage.removeItem('session_token');
        }
    }
}

async function handleLogin(e) {
    e.preventDefault();
    console.log('Login form submitted');
    
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    
    console.log('Login attempt for user:', username);
    
    try {
        showLoading('loginResult');
        
        const response = await fetch('http://localhost:8000/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Store session token
            localStorage.setItem('session_token', result.session_token);
            localStorage.setItem('user_info', JSON.stringify(result.user));
            
            showResult('loginResult', {
                success: true,
                message: `Welcome back, ${result.user.username}!`
            });
            
            // Redirect to main app after a short delay
            setTimeout(() => {
                window.location.href = '/app';
            }, 1000);
        } else {
            throw new Error(result.message || 'Login failed');
        }
    } catch (error) {
        showResult('loginResult', {
            success: false,
            message: 'Login failed: ' + error.message
        });
    }
}

async function handleRegister(e) {
    e.preventDefault();
    console.log('Register form submitted');
    
    const username = document.getElementById('regUsername').value;
    const email = document.getElementById('regEmail').value;
    const password = document.getElementById('regPassword').value;
    
    console.log('Register attempt for user:', username, 'email:', email);
    
    try {
        showLoading('loginResult');
        
        const response = await fetch('http://localhost:8000/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                email: email,
                password: password
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showResult('loginResult', {
                success: true,
                message: 'Registration successful! Please login with your credentials.'
            });
            
            // Switch to login form
            setTimeout(() => {
                showLogin();
                document.getElementById('loginUsername').value = username;
                document.getElementById('loginPassword').value = '';
                document.getElementById('loginPassword').focus();
            }, 1500);
        } else {
            throw new Error(result.message || 'Registration failed');
        }
    } catch (error) {
        showResult('loginResult', {
            success: false,
            message: 'Registration failed: ' + error.message
        });
    }
}

function showLogin() {
    document.getElementById('loginForm').classList.remove('hidden');
    document.getElementById('registerForm').classList.add('hidden');
    document.getElementById('loginResult').innerHTML = '';
}

function showRegister() {
    document.getElementById('loginForm').classList.add('hidden');
    document.getElementById('registerForm').classList.remove('hidden');
    document.getElementById('loginResult').innerHTML = '';
}

function showLoading(elementId) {
    const element = document.getElementById(elementId);
    element.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Processing...</div>';
}

function showResult(elementId, result) {
    const element = document.getElementById(elementId);
    
    if (result.success) {
        element.innerHTML = `
            <div class="success">
                <i class="fas fa-check-circle"></i>
                <p>${result.message}</p>
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
