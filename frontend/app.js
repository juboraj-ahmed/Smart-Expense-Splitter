const API_BASE = 'http://127.0.0.1:8000/api/v1';

// State
let authToken = localStorage.getItem('access_token');
let currentUser = null;
let currentGroup = null;

// Multi-currency Support
let currentCurrency = localStorage.getItem('preferred_currency') || 'USD';
const EXCHANGE_RATE_USD_TO_BDT = 120.0;

// DOM Elements
const appLayout = document.getElementById('app-layout');
const authView = document.getElementById('auth-view');

// Toasts
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-circle-exclamation';
    if (type === 'warning') icon = 'fa-triangle-exclamation';
    
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);
    
    setTimeout(() => {
        if(toast.parentElement) toast.remove();
    }, 5000);
}

function getCurrencySymbol() {
    return currentCurrency === 'BDT' ? '৳' : '$';
}

// Currency Formatter
function formatCurrency(amount) {
    let value = parseFloat(amount);
    if (currentCurrency === 'BDT') {
        value = value * EXCHANGE_RATE_USD_TO_BDT;
        return `৳${value.toFixed(2)}`;
    }
    return `$${value.toFixed(2)}`;
}

// Update UI Labels
function updateCurrencyLabels() {
    const symbol = getCurrencySymbol();
    const expLabel = document.getElementById('expense-amount-label');
    const setLabel = document.getElementById('settle-amount-label');
    if (expLabel) expLabel.innerText = `Amount (${symbol})`;
    if (setLabel) setLabel.innerText = `Amount (${symbol})`;
}

// API Helper
async function apiCall(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...(authToken && { 'Authorization': `Bearer ${authToken}` }),
        ...options.headers
    };
    
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
        const data = await response.json().catch(() => ({}));
        
        if (response.status === 401) {
            // Need to implement refresh token logic, for now logout
            logout();
            throw new Error('Unauthorized');
        }
        
        if (!response.ok) {
            const errorMsg = data.error || data.detail || (data.errors && Object.values(data.errors).flat()[0]) || 'An error occurred';
            throw new Error(errorMsg);
        }
        
        return data;
    } catch (error) {
        throw error;
    }
}

// Initialization
async function init() {
    setupEventListeners();
    if (authToken) {
        try {
            // Validate token by fetching user profile
            const users = await apiCall('/users/'); // We just need our own details. The API design says /users/me, but urls.py registers UserViewSet at /users/. 
            // In UserViewSet list, it probably returns all users. Wait, if there's no /users/me, let's just decode token or get the first user if it matches. 
            // Actually, we can fetch /users/ and find ourselves, or we saved user ID. Let's just trust token for now and load groups.
            // Let's assume we decode token or just proceed to dashboard.
            // A quick fix is to decode JWT manually:
            const tokenParts = authToken.split('.');
            if(tokenParts.length === 3) {
                const payload = JSON.parse(atob(tokenParts[1]));
                currentUser = { id: payload.user_id, username: 'User' }; // Basic info
            }
            
            showApp();
            
            // Set initial currency dropdown value
            const currencySelect = document.getElementById('currency-select');
            if (currencySelect) currencySelect.value = currentCurrency;
            updateCurrencyLabels();
            
            await loadDashboard();
            loadNotifications();
        } catch (err) {
            console.error('Init error:', err);
            showAuth();
        }
    } else {
        showAuth();
    }
}

// UI Navigation
function showAuth() {
    authView.style.display = 'block';
    authView.classList.add('active');
    appLayout.style.display = 'none';
}

function showApp() {
    authView.style.display = 'none';
    appLayout.style.display = 'flex';
    if(currentUser) {
        document.getElementById('sidebar-username').innerText = currentUser.username || 'User';
        document.getElementById('sidebar-avatar').innerText = (currentUser.username || 'U')[0].toUpperCase();
    }
}

function switchSection(sectionId) {
    document.querySelectorAll('.content-section').forEach(sec => sec.style.display = 'none');
    document.getElementById(sectionId).style.display = 'block';
    
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    const activeNav = document.querySelector(`.nav-item[data-target="${sectionId.replace('-section', '')}"]`);
    if(activeNav) activeNav.classList.add('active');
}

// Event Listeners Setup
function setupEventListeners() {
    // Auth Toggles
    document.getElementById('show-register').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('login-form').style.display = 'none';
        document.getElementById('register-form').style.display = 'block';
        document.getElementById('auth-subtitle').innerText = 'Create a new account.';
    });
    
    document.getElementById('show-login').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('register-form').style.display = 'none';
        document.getElementById('login-form').style.display = 'block';
        document.getElementById('auth-subtitle').innerText = 'Welcome back! Please enter your details.';
    });

    // Auth Forms
    document.getElementById('login-form').addEventListener('submit', handleLogin);
    document.getElementById('register-form').addEventListener('submit', handleRegister);
    document.getElementById('logout-btn').addEventListener('click', (e) => { e.preventDefault(); logout(); });

    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', async (e) => {
            e.preventDefault();
            const target = item.dataset.target;
            if (target === 'dashboard') {
                switchSection('dashboard-section');
                document.getElementById('page-title').innerText = 'Overview';
                document.getElementById('page-subtitle').innerText = 'Welcome back, here\'s your summary.';
                await loadDashboard();
            } else if (target === 'groups') {
                switchSection('groups-section');
                document.getElementById('page-title').innerText = 'Your Groups';
                document.getElementById('page-subtitle').innerText = 'Manage your expense splits';
                await loadGroups();
            }
        });
    });

    document.getElementById('back-to-groups').addEventListener('click', () => {
        switchSection('groups-section');
        document.getElementById('page-title').innerText = 'Your Groups';
        document.getElementById('page-subtitle').innerText = 'Manage your expense splits';
    });

    // Currency Switcher
    const currencySelect = document.getElementById('currency-select');
    if (currencySelect) {
        currencySelect.addEventListener('change', (e) => {
            currentCurrency = e.target.value;
            localStorage.setItem('preferred_currency', currentCurrency);
            updateCurrencyLabels();
            // Refresh views
            if (document.getElementById('dashboard-section').style.display !== 'none') loadDashboard();
            if (document.getElementById('groups-section').style.display !== 'none') loadGroups();
            if (currentGroup && document.getElementById('group-detail-section').style.display !== 'none') loadGroupDetail(currentGroup.id);
        });
    }

    // Notifications Toggle
    const notifBtn = document.getElementById('notification-btn');
    const notifDropdown = document.getElementById('notifications-dropdown');
    if (notifBtn && notifDropdown) {
        notifBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            notifDropdown.classList.toggle('active');
        });
        document.addEventListener('click', (e) => {
            if (!notifDropdown.contains(e.target) && e.target !== notifBtn) {
                notifDropdown.classList.remove('active');
            }
        });
    }

    const markReadBtn = document.getElementById('mark-all-read');
    if (markReadBtn) {
        markReadBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            document.querySelectorAll('.notification-item').forEach(item => item.classList.remove('unread'));
            document.getElementById('notification-badge').classList.remove('show');
            showToast('All notifications marked as read', 'success');
        });
    }

    // Modals
    setupModals();
}

function setupModals() {
    const modals = {
        'dashboard-add-group': 'modal-create-group',
        'new-group-btn': 'modal-create-group',
        'empty-create-group-btn': 'modal-create-group',
        'add-member-btn': 'modal-add-member',
        'add-expense-btn': 'modal-add-expense'
    };

    for (const [btnId, modalId] of Object.entries(modals)) {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                openModal(modalId);
            });
        }
    }

    document.querySelectorAll('.close-modal, .close-modal-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.target.closest('.modal-overlay').classList.remove('active');
        });
    });

    // Form Submissions
    document.getElementById('form-create-group').addEventListener('submit', handleCreateGroup);
    document.getElementById('form-add-member').addEventListener('submit', handleAddMember);
    document.getElementById('form-add-expense').addEventListener('submit', handleAddExpense);
    document.getElementById('form-settle-up').addEventListener('submit', handleSettleUp);
}

function openModal(modalId) {
    if(modalId === 'modal-add-expense' && currentGroup) {
        populateExpenseMembers(currentGroup.members);
    }
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
    // Reset forms inside
    const form = document.querySelector(`#${modalId} form`);
    if(form) form.reset();
}

// Auth Handlers
async function handleLogin(e) {
    e.preventDefault();
    const btn = document.getElementById('login-submit-btn');
    const ogText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    btn.disabled = true;

    try {
        const email = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        const data = await apiCall('/auth/login/', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        
        authToken = data.access || data.access_token;
        localStorage.setItem('access_token', authToken);
        if(data.refresh) localStorage.setItem('refresh_token', data.refresh);
        
        if (data.user) currentUser = data.user;
        else {
             const tokenParts = authToken.split('.');
             if(tokenParts.length === 3) {
                 const payload = JSON.parse(atob(tokenParts[1]));
                 currentUser = { id: payload.user_id, username: 'User' }; 
             }
        }
        
        showApp();
        showToast('Successfully logged in');
        await loadDashboard();
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        btn.innerHTML = ogText;
        btn.disabled = false;
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const btn = document.getElementById('register-submit-btn');
    const ogText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    btn.disabled = true;

    try {
        const username = document.getElementById('reg-username').value;
        const email = document.getElementById('reg-email').value;
        const password = document.getElementById('reg-password').value;
        
        await apiCall('/auth/register/', {
            method: 'POST',
            body: JSON.stringify({ username, email, password, password_confirm: password })
        });
        
        showToast('Registration successful! Please login.');
        document.getElementById('show-login').click();
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        btn.innerHTML = ogText;
        btn.disabled = false;
    }
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    authToken = null;
    currentUser = null;
    showAuth();
}

// Data Loaders
async function loadDashboard() {
    try {
        if(currentUser && currentUser.id) {
            // Load Trust Score
            try {
                const tsData = await apiCall(`/users/${currentUser.id}/trust-score/`);
                updateTrustScore(tsData.current_score || 100);
            } catch (e) {
                updateTrustScore(100); // Default if endpoint fails
            }
        }

        // Load Groups for dashboard
        const data = await apiCall('/groups/');
        const groups = data.results || [];
        
        const listEl = document.getElementById('dashboard-groups-list');
        listEl.innerHTML = '';
        
        let totalOwedToYou = 0;
        let totalYouOwe = 0;

        if (groups.length === 0) {
            listEl.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-ghost"></i>
                    <p>No groups yet.</p>
                </div>
            `;
        } else {
            groups.slice(0, 3).forEach(group => {
                const balance = parseFloat(group.your_balance || 0);
                if (balance > 0) totalOwedToYou += balance;
                else if (balance < 0) totalYouOwe += Math.abs(balance);
                
                const balClass = balance > 0 ? 'positive' : (balance < 0 ? 'negative' : 'neutral');
                const formattedBal = formatCurrency(Math.abs(balance));
                const balText = balance > 0 ? `+ ${formattedBal}` : (balance < 0 ? `- ${formattedBal}` : 'Settled');

                const el = document.createElement('div');
                el.className = 'list-item';
                el.onclick = () => loadGroupDetail(group.id);
                el.innerHTML = `
                    <div class="item-left">
                        <div class="item-icon"><i class="fa-solid fa-users"></i></div>
                        <div class="item-info">
                            <h4>${group.name}</h4>
                            <p>${group.members_count || 1} members</p>
                        </div>
                    </div>
                    <div class="item-right">
                        <div class="item-amount ${balClass}">${balText}</div>
                    </div>
                `;
                listEl.appendChild(el);
            });
        }

        document.getElementById('total-owed-to-you').innerText = formatCurrency(totalOwedToYou);
        document.getElementById('total-you-owe').innerText = formatCurrency(totalYouOwe);

    } catch (err) {
        showToast('Failed to load dashboard: ' + err.message, 'error');
    }
}

function updateTrustScore(score) {
    document.getElementById('topbar-trust-score').innerText = score;
    document.getElementById('trust-score-val').innerText = score;
    
    let status = "Excellent Standing";
    let color = "var(--success)";
    if(score < 50) { status = "Poor Standing"; color = "var(--danger)"; }
    else if(score < 70) { status = "Fair Standing"; color = "var(--warning)"; }
    else if(score < 90) { status = "Good Standing"; color = "var(--primary)"; }
    
    document.querySelector('.trust-status').innerText = status;
    document.querySelector('.trust-status').style.background = `linear-gradient(135deg, ${color}, ${color})`;
    document.querySelector('.trust-status').style.webkitBackgroundClip = 'text';
    
    // Update circle SVG
    const circle = document.getElementById('trust-circle');
    const percentage = score / 100;
    const dashoffset = 440 - (440 * percentage);
    circle.style.strokeDashoffset = dashoffset;
}

async function loadGroups() {
    try {
        const data = await apiCall('/groups/');
        const groups = data.results || [];
        const grid = document.getElementById('groups-grid');
        grid.innerHTML = '';
        
        if (groups.length === 0) {
            grid.innerHTML = `
                <div class="empty-state full-width">
                    <div class="empty-icon"><i class="fa-solid fa-users-slash"></i></div>
                    <h3>No groups found</h3>
                    <p>Create a group to start splitting expenses.</p>
                    <button class="btn secondary-btn mt-3" onclick="openModal('modal-create-group')">Create Group</button>
                </div>
            `;
            return;
        }

        groups.forEach(group => {
            const balance = parseFloat(group.your_balance || 0);
            const balClass = balance > 0 ? 'positive' : (balance < 0 ? 'negative' : 'neutral');
            const formattedBal = formatCurrency(Math.abs(balance));
            const balText = balance > 0 ? `You are owed ${formattedBal}` : (balance < 0 ? `You owe ${formattedBal}` : 'You are settled up');
            
            const card = document.createElement('div');
            card.className = 'bento-card';
            card.style.cursor = 'pointer';
            card.onclick = () => loadGroupDetail(group.id);
            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
                    <div class="group-avatar" style="width: 48px; height: 48px; font-size: 1.5rem;">${group.name.charAt(0).toUpperCase()}</div>
                    <span class="text-muted text-sm"><i class="fa-solid fa-users"></i> ${group.members_count || 1}</span>
                </div>
                <h3 style="color: var(--text-primary); font-size: 1.25rem; margin-bottom: 0.5rem;">${group.name}</h3>
                <p class="text-sm item-amount ${balClass}">${balText}</p>
            `;
            grid.appendChild(card);
        });

    } catch (err) {
        showToast('Failed to load groups: ' + err.message, 'error');
    }
}

async function loadGroupDetail(groupId) {
    try {
        currentGroup = await apiCall(`/groups/${groupId}/`);
        
        switchSection('group-detail-section');
        document.getElementById('page-title').innerText = currentGroup.name;
        document.getElementById('page-subtitle').innerText = 'Group Details & Expenses';
        
        document.getElementById('detail-group-name').innerText = currentGroup.name;
        document.getElementById('detail-group-desc').innerText = currentGroup.description || `${currentGroup.members.length} Members`;
        document.getElementById('detail-group-avatar').innerText = currentGroup.name.charAt(0).toUpperCase();

        // Load Balances
        const balData = await apiCall(`/groups/${groupId}/balances/`);
        const balList = document.getElementById('group-balances-list');
        balList.innerHTML = '';
        
        if (balData.balances && balData.balances.length > 0) {
            balData.balances.forEach(b => {
                const isMe = currentUser && b.user.id === currentUser.id;
                const username = isMe ? `${b.user.username} (You)` : b.user.username;
                const net = parseFloat(b.net_balance);
                
                let balHtml = '';
                const formattedNet = formatCurrency(Math.abs(net));
                if(net > 0) {
                    balHtml = `<span class="item-amount positive">gets back ${formattedNet}</span>`;
                    if (!isMe) {
                         balHtml += ` <button class="btn primary-btn settle-btn-sm ml-2" onclick="openSettleUpModal(${b.user.id}, '${b.user.username}')">Pay</button>`;
                    }
                }
                else if(net < 0) {
                    balHtml = `<span class="item-amount negative">owes ${formattedNet}</span>`;
                }
                else balHtml = `<span class="text-muted text-sm">Settled</span>`;

                const el = document.createElement('div');
                el.className = 'list-item mb-2';
                el.innerHTML = `
                    <div class="item-left">
                        <div class="item-info"><h4>${username}</h4></div>
                    </div>
                    <div class="item-right">${balHtml}</div>
                `;
                balList.appendChild(el);
            });
        } else {
            balList.innerHTML = '<p class="text-muted text-sm text-center">No balances yet.</p>';
        }

        // Load Expenses and Settlements for Timeline
        const expData = await apiCall(`/groups/${groupId}/expenses/`);
        const setData = await apiCall(`/groups/${groupId}/settlements/`);
        
        const expList = document.getElementById('group-expenses-list');
        expList.innerHTML = '';
        
        const expenses = expData.results || expData || [];
        let settlements = setData.results || setData || [];
        if (!Array.isArray(settlements)) settlements = [];
        
        const timeline = [];
        expenses.forEach(e => timeline.push({ ...e, type: 'expense' }));
        settlements.forEach(s => timeline.push({ ...s, type: 'settlement' }));
        
        timeline.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        
        if (timeline.length > 0) {
            timeline.forEach(item => {
                const el = document.createElement('div');
                el.className = 'list-item mb-2';
                
                if (item.type === 'expense') {
                    el.innerHTML = `
                        <div class="item-left">
                            <div class="item-icon"><i class="fa-solid fa-receipt"></i></div>
                            <div class="item-info">
                                <h4>${item.description}</h4>
                                <p>Paid by ${item.paid_by.username}</p>
                            </div>
                        </div>
                        <div class="item-right">
                            <div class="item-amount">${formatCurrency(parseFloat(item.amount))}</div>
                            <div class="item-date">${new Date(item.created_at).toLocaleDateString()}</div>
                        </div>
                    `;
                } else {
                    let statusBadge = '';
                    if (item.status === 'pending') statusBadge = '<span style="font-size:0.7rem; color:var(--warning); border:1px solid var(--warning); padding:1px 4px; border-radius:4px; margin-left:6px;">Pending</span>';
                    else if (item.status === 'accepted') statusBadge = '<span style="font-size:0.7rem; color:var(--success); border:1px solid var(--success); padding:1px 4px; border-radius:4px; margin-left:6px;">Settled</span>';
                    
                    el.innerHTML = `
                        <div class="item-left">
                            <div class="item-icon" style="background: rgba(16, 185, 129, 0.1); color: var(--success);"><i class="fa-solid fa-money-bill-transfer"></i></div>
                            <div class="item-info">
                                <h4>Payment ${statusBadge}</h4>
                                <p>${item.from_user.username} paid ${item.to_user.username}</p>
                            </div>
                        </div>
                        <div class="item-right">
                            <div class="item-amount positive">${formatCurrency(parseFloat(item.amount))}</div>
                            <div class="item-date">${new Date(item.created_at).toLocaleDateString()}</div>
                        </div>
                    `;
                }
                expList.appendChild(el);
            });
        } else {
            expList.innerHTML = '<div class="empty-state"><p>No activity recorded yet.</p></div>';
        }

    } catch (err) {
        showToast('Failed to load group details: ' + err.message, 'error');
    }
}

// Handlers
async function handleCreateGroup(e) {
    e.preventDefault();
    const name = document.getElementById('new-group-name').value;
    const desc = document.getElementById('new-group-desc').value;
    
    try {
        await apiCall('/groups/', {
            method: 'POST',
            body: JSON.stringify({ name, description: desc })
        });
        showToast('Group created!');
        closeModal('modal-create-group');
        loadGroups();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function handleAddMember(e) {
    e.preventDefault();
    if(!currentGroup) return;
    
    const userId = document.getElementById('new-member-id').value;
    try {
        await apiCall(`/groups/${currentGroup.id}/add_member/`, {
            method: 'POST',
            body: JSON.stringify({ user_id: parseInt(userId) })
        });
        showToast('Member added!');
        closeModal('modal-add-member');
        loadGroupDetail(currentGroup.id);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function populateExpenseMembers(members) {
    const list = document.getElementById('expense-members-checkboxes');
    list.innerHTML = '';
    members.forEach(m => {
        list.innerHTML += `
            <label class="checkbox-label">
                <input type="checkbox" value="${m.id}" checked>
                <span>${m.username}</span>
            </label>
        `;
    });
}

async function handleAddExpense(e) {
    e.preventDefault();
    if(!currentGroup) return;

    const desc = document.getElementById('expense-desc').value;
    let amount = parseFloat(document.getElementById('expense-amount').value);
    const category = document.getElementById('expense-category').value;
    
    // Convert to base currency (USD) if user entered BDT
    if (currentCurrency === 'BDT') {
        amount = amount / EXCHANGE_RATE_USD_TO_BDT;
    }
    
    // Get selected participants
    const checkboxes = document.querySelectorAll('#expense-members-checkboxes input[type="checkbox"]:checked');
    const participant_ids = Array.from(checkboxes).map(cb => parseInt(cb.value));

    if (participant_ids.length === 0) {
        showToast('Select at least one member to split with.', 'error');
        return;
    }

    try {
        // Use equal split endpoint for simplicity
        await apiCall('/expenses/create_equal_split/', {
            method: 'POST',
            body: JSON.stringify({
                group_id: currentGroup.id,
                amount: amount.toFixed(2),
                description: desc,
                category: category,
                participant_ids: participant_ids
            })
        });
        showToast('Expense added!');
        closeModal('modal-add-expense');
        loadGroupDetail(currentGroup.id);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function openSettleUpModal(targetId, targetName) {
    document.getElementById('settle-target-id').value = targetId;
    document.getElementById('settle-target-name').innerText = targetName;
    openModal('modal-settle-up');
}

async function handleSettleUp(e) {
    e.preventDefault();
    if(!currentGroup) return;

    const targetId = document.getElementById('settle-target-id').value;
    let amount = parseFloat(document.getElementById('settle-amount').value);
    const desc = document.getElementById('settle-desc').value;

    // Convert to base currency (USD) if user entered BDT
    if (currentCurrency === 'BDT') {
        amount = amount / EXCHANGE_RATE_USD_TO_BDT;
    }

    try {
        await apiCall('/settlements/', {
            method: 'POST',
            body: JSON.stringify({
                group_id: currentGroup.id,
                to_user_id: parseInt(targetId),
                amount: parseFloat(amount).toFixed(2),
                description: desc
            })
        });
        showToast('Payment recorded successfully!');
        closeModal('modal-settle-up');
        loadGroupDetail(currentGroup.id);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Notifications
async function loadNotifications() {
    const notifList = document.getElementById('notifications-list');
    const badge = document.getElementById('notification-badge');
    
    if (!notifList || !badge || !currentUser) return;
    
    try {
        const data = await apiCall('/settlements/');
        const settlements = data.results || data; // handle pagination or flat list
        const results = Array.isArray(settlements) ? settlements : [];
        
        // Sort newest first
        results.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        
        notifList.innerHTML = '';
        let unreadCount = 0;
        let displayedCount = 0;
        
        results.forEach(s => {
            const isSender = s.from_user.id === currentUser.id;
            const isRecipient = s.to_user.id === currentUser.id;
            
            if (!isSender && !isRecipient) return;
            displayedCount++;
            
            const formattedAmount = formatCurrency(parseFloat(s.amount));
            const el = document.createElement('div');
            
            let content = '';
            let isUnread = false;
            
            if (isRecipient) {
                if (s.status === 'pending') {
                    isUnread = true;
                    content = `<p><strong>${s.from_user.username}</strong> paid you ${formattedAmount}.</p>
                               <div style="margin-top: 5px;">
                                   <button class="btn primary-btn settle-btn-sm" onclick="confirmSettlement(${s.id})">Confirm</button>
                               </div>`;
                } else if (s.status === 'accepted') {
                    content = `<p>You received ${formattedAmount} from <strong>${s.from_user.username}</strong>.</p>`;
                } else {
                    content = `<p>You rejected ${formattedAmount} from <strong>${s.from_user.username}</strong>.</p>`;
                }
            } else if (isSender) {
                if (s.status === 'pending') {
                    content = `<p>You sent ${formattedAmount} to <strong>${s.to_user.username}</strong> (Pending).</p>`;
                } else if (s.status === 'accepted') {
                    content = `<p><strong>${s.to_user.username}</strong> confirmed your payment of ${formattedAmount}!</p>`;
                } else {
                    content = `<p><strong>${s.to_user.username}</strong> rejected your payment of ${formattedAmount}.</p>`;
                }
            }
            
            el.className = `notification-item ${isUnread ? 'unread' : ''}`;
            el.innerHTML = `
                <div class="notification-icon"><i class="fa-solid fa-money-bill-transfer"></i></div>
                <div class="notification-content" style="flex:1">
                    ${content}
                    <span class="notification-time">${new Date(s.created_at).toLocaleString()}</span>
                </div>
            `;
            notifList.appendChild(el);
            if (isUnread) unreadCount++;
        });
        
        if (displayedCount === 0) {
            notifList.innerHTML = '<p class="text-muted text-center text-sm py-3">No notifications.</p>';
        }
        
        if (unreadCount > 0) {
            badge.innerText = unreadCount;
            badge.classList.add('show');
        } else {
            badge.classList.remove('show');
        }
    } catch(err) {
        console.error("Error loading notifications:", err);
    }
}

async function confirmSettlement(paymentId) {
    try {
        await apiCall(`/settlements/${paymentId}/confirm/`, { method: 'POST' });
        showToast('Payment confirmed!', 'success');
        
        // Hide dropdown
        const notifDropdown = document.getElementById('notifications-dropdown');
        if (notifDropdown) notifDropdown.classList.remove('active');
        
        loadNotifications();
        
        if (document.getElementById('group-detail-section').style.display !== 'none' && currentGroup) {
            loadGroupDetail(currentGroup.id);
        }
        if (document.getElementById('dashboard-section').style.display !== 'none') {
            loadDashboard();
        }
    } catch(err) {
        showToast(err.message, 'error');
    }
}

// Start
init();
