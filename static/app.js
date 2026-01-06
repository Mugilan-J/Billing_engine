const API = "http://localhost:8090";

// --- AUTH STATE ---
function init() {
    // Check if user is logged in (session cookie handled by browser)
    // We try to fetch credits. If 401, show login.
    fetch(`${API}/dashboard/credits`)
        .then(res => {
            if (res.status === 401) showScreen('auth');
            else {
                res.json().then(data => {
                    // Save user info purely for display
                    document.getElementById('user-email').innerText = "session.User"; 
                    showScreen('dashboard');
                    loadDashboard();
                });
            }
        })
        .catch(() => showScreen('auth'));

    document.getElementById('current-date').innerText = new Date().toLocaleDateString();
}

// --- ACTIONS ---

async function handleLogin() {
    const email = document.getElementById('l-email').value;
    const password = document.getElementById('l-pass').value;
    
    authRequest('/api/login', { email, password });
}

async function handleSignup() {
    const email = document.getElementById('s-email').value;
    const password = document.getElementById('s-pass').value;
    const tier = document.getElementById('s-tier').value;

    authRequest('/api/signup', { email, password, tier });
}

async function authRequest(endpoint, payload) {
    const errBox = document.getElementById('auth-error');
    errBox.innerText = "sending_request...";
    
    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            location.reload(); // Reload to trigger init() and show dashboard
        } else {
            const txt = await res.text();
            errBox.innerText = `Error: ${txt}`;
        }
    } catch (e) {
        errBox.innerText = `Connection Refused: ${e}`;
    }
}

function handleLogout() {
    fetch('/api/logout').then(() => location.reload());
}

// --- DASHBOARD DATA ---

async function loadDashboard() {
    // 1. Credits
    const cRes = await fetch(`${API}/dashboard/credits`);
    const cData = await cRes.json();
    document.getElementById('val-credits').innerText = cData.remaining_credits.toFixed(4);
    document.getElementById('val-tier').innerText = `"${cData.tier}"`;

    // 2. Usage
    const month = new Date().toISOString().slice(0, 7);
    const uRes = await fetch(`${API}/dashboard/usage?month=${month}`);
    const uData = await uRes.json();
    document.getElementById('val-usage').innerText = uData.total_cost.toFixed(4);

    // 3. Breakdown
    const bRes = await fetch(`${API}/dashboard/usage/breakdown?month=${month}`);
    const bData = await bRes.json();
    const bTable = document.getElementById('breakdown-table');
    bTable.innerHTML = bData.map(r => `
        <tr>
            <td>"${r.provider}"</td>
            <td>"${r.model}"</td>
            <td>${r.tokens}</td>
            <td>${r.cost.toFixed(4)}</td>
        </tr>
    `).join('');
    
    // 4. Keys
    const kRes = await fetch(`${API}/dashboard/api-keys`);
    const kData = await kRes.json();
    document.getElementById('keys-table').innerHTML = kData.map(k => `
        <tr>
            <td>${k.key_id}</td>
            <td><span style="color:${k.status==='active'?'var(--accent)':'red'}">${k.status}</span></td>
            <td>${k.created_at.slice(0,10)}</td>
        </tr>
    `).join('');
    
    // 5. Billing
    const billRes = await fetch(`${API}/dashboard/billing`);
    const billData = await billRes.json();
    document.getElementById('billing-table').innerHTML = billData.map(b => `
        <tr>
            <td>${b.month.slice(0,10)}</td>
            <td>${b.total_cost.toFixed(2)}</td>
            <td>${b.credits_used.toFixed(2)}</td>
            <td>${b.status}</td>
        </tr>
    `).join('');
}

// --- UI HELPERS ---

function showScreen(name) {
    document.getElementById('auth-screen').style.display = name === 'auth' ? 'flex' : 'none';
    document.getElementById('dashboard-screen').style.display = name === 'dashboard' ? 'flex' : 'none';
}

function toggleAuth(mode) {
    document.getElementById('login-form').style.display = mode === 'login' ? 'block' : 'none';
    document.getElementById('signup-form').style.display = mode === 'signup' ? 'block' : 'none';
    document.getElementById('auth-error').innerText = "";
}

function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
    document.getElementById(`tab-${tabId}`).style.display = 'block';
    
    document.querySelectorAll('aside nav a').forEach(el => el.classList.remove('active'));
    event.target.classList.add('active');
}

// Start
init();