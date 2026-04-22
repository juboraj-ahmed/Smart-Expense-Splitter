const API_BASE = 'http://127.0.0.1:8000/api/v1';

// DOM Elements
const authView = document.getElementById('auth-view');
const dashboardView = document.getElementById('dashboard-view');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const showRegisterBtn = document.getElementById('show-register');
const showLoginBtn = document.getElementById('show-login');
const logoutBtn = document.getElementById('logout-btn');
const userDisplayName = document.getElementById('user-display-name');

// State
let authToken = localStorage.getItem('access_token');
let currentUser = null;

// Initialization
async function init() {
    if (authToken) {
        // Might need a mechanism to fetch 'me', or just decode the token 
        // We will fetch users to grab our details, but for now just show dashboard
        showView('dashboard');
        // A real app would fetch user details here using the token
        userDisplayName.innerText = 'Admin'; // Mock for now until we build the logic
    } else {
        showView('auth');
    }
}

// UI Functions
function showView(viewName) {
    authView.style.display = viewName === 'auth' ? 'flex' : 'none';
    dashboardView.style.display = viewName === 'dashboard' ? 'grid' : 'none';
}

showRegisterBtn.addEventListener('click', (e) => {
    e.preventDefault();
    loginForm.style.display = 'none';
    registerForm.style.display = 'block';
});

showLoginBtn.addEventListener('click', (e) => {
    e.preventDefault();
    registerForm.style.display = 'none';
    loginForm.style.display = 'block';
});

// Authentication
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch(`${API_BASE}/auth/login/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email, password})
        });

        const data = await response.json();
        
        if (response.ok) {
            authToken = data.access;
            localStorage.setItem('access_token', authToken);
            if(data.refresh) localStorage.setItem('refresh_token', data.refresh);
            userDisplayName.innerText = username;
            showView('dashboard');
        } else {
            alert('Login failed: ' + JSON.stringify(data));
        }
    } catch (err) {
        console.error('Error:', err);
        alert('Network error during login');
    }
});

registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('reg-username').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const password_confirm = password;

    try {
        const response = await fetch(`${API_BASE}/auth/register/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, email, password, password_confirm})
        });

        if (response.ok) {
            alert('Registration successful! Please sign in.');
            showLoginBtn.click();
        } else {
            const data = await response.json();
            alert('Registration failed: ' + JSON.stringify(data));
        }
    } catch (err) {
        console.error('Error:', err);
    }
});

logoutBtn.addEventListener('click', (e) => {
    e.preventDefault();
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    authToken = null;
    showView('auth');
});

// Init App
init();
