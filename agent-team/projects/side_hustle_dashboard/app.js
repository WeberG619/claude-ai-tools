// Side Hustle Dashboard - Application Logic

// Category configuration with icons
const CATEGORIES = {
    // Income categories
    'freelance': { icon: '💻', label: 'Freelance', type: 'income' },
    'sales': { icon: '🛍️', label: 'Sales', type: 'income' },
    'affiliate': { icon: '🔗', label: 'Affiliate', type: 'income' },
    'tips': { icon: '💵', label: 'Tips', type: 'income' },
    'other-income': { icon: '💰', label: 'Other Income', type: 'income' },
    // Expense categories
    'software': { icon: '🖥️', label: 'Software & Tools', type: 'expense' },
    'supplies': { icon: '📦', label: 'Supplies', type: 'expense' },
    'marketing': { icon: '📣', label: 'Marketing', type: 'expense' },
    'fees': { icon: '💳', label: 'Fees & Commissions', type: 'expense' },
    'other-expense': { icon: '📝', label: 'Other Expense', type: 'expense' }
};

// Storage key
const STORAGE_KEY = 'side_hustle_data';

// State
let transactions = [];
let currentFilter = 'all';

// Initialize
function init() {
    loadTransactions();
    setupEventListeners();
    setDefaultDate();
    updateUI();
}

// Load transactions from localStorage
function loadTransactions() {
    try {
        const data = localStorage.getItem(STORAGE_KEY);
        transactions = data ? JSON.parse(data) : [];
    } catch (e) {
        console.error('Error loading data:', e);
        transactions = [];
    }
}

// Save transactions to localStorage
function saveTransactions() {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(transactions));
    } catch (e) {
        console.error('Error saving data:', e);
    }
}

// Set default date to today
function setDefaultDate() {
    const dateInput = document.getElementById('date');
    dateInput.value = new Date().toISOString().split('T')[0];
}

// Setup event listeners
function setupEventListeners() {
    // Form submission
    document.getElementById('transactionForm').addEventListener('submit', handleSubmit);

    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            renderTransactions();
        });
    });

    // Type change - update category options
    document.getElementById('type').addEventListener('change', updateCategoryOptions);
}

// Update category dropdown based on type
function updateCategoryOptions() {
    const type = document.getElementById('type').value;
    const categorySelect = document.getElementById('category');
    const optgroups = categorySelect.querySelectorAll('optgroup');

    optgroups.forEach(group => {
        const isIncome = group.label === 'Income';
        group.style.display = (type === 'income' && isIncome) || (type === 'expense' && !isIncome) ? '' : 'none';

        // Select first visible option
        if ((type === 'income' && isIncome) || (type === 'expense' && !isIncome)) {
            categorySelect.value = group.querySelector('option').value;
        }
    });
}

// Handle form submission
function handleSubmit(e) {
    e.preventDefault();

    const type = document.getElementById('type').value;
    const amount = parseFloat(document.getElementById('amount').value);
    const category = document.getElementById('category').value;
    const date = document.getElementById('date').value;
    const description = document.getElementById('description').value.trim();

    if (!amount || amount <= 0) {
        alert('Please enter a valid amount');
        return;
    }

    const transaction = {
        id: Date.now(),
        type,
        amount,
        category,
        date,
        description,
        createdAt: new Date().toISOString()
    };

    transactions.unshift(transaction);
    saveTransactions();
    updateUI();

    // Reset form
    e.target.reset();
    setDefaultDate();
    updateCategoryOptions();
}

// Delete transaction
function deleteTransaction(id) {
    if (confirm('Delete this transaction?')) {
        transactions = transactions.filter(t => t.id !== id);
        saveTransactions();
        updateUI();
    }
}

// Calculate totals
function calculateTotals() {
    const income = transactions
        .filter(t => t.type === 'income')
        .reduce((sum, t) => sum + t.amount, 0);

    const expenses = transactions
        .filter(t => t.type === 'expense')
        .reduce((sum, t) => sum + t.amount, 0);

    const profit = income - expenses;

    return { income, expenses, profit };
}

// Generate insights
function generateInsights() {
    if (transactions.length === 0) return [];

    const insights = [];
    const totals = calculateTotals();

    // Profit margin
    if (totals.income > 0) {
        const margin = ((totals.profit / totals.income) * 100).toFixed(0);
        insights.push({
            icon: '📊',
            text: `Profit margin: <strong>${margin}%</strong>`
        });
    }

    // Best income category
    const incomeByCategory = {};
    transactions.filter(t => t.type === 'income').forEach(t => {
        incomeByCategory[t.category] = (incomeByCategory[t.category] || 0) + t.amount;
    });

    const bestCategory = Object.entries(incomeByCategory)
        .sort((a, b) => b[1] - a[1])[0];

    if (bestCategory) {
        const cat = CATEGORIES[bestCategory[0]];
        insights.push({
            icon: '🏆',
            text: `Top earner: <strong>${cat.label}</strong> ($${bestCategory[1].toFixed(2)})`
        });
    }

    // Transaction count
    const incomeCount = transactions.filter(t => t.type === 'income').length;
    const expenseCount = transactions.filter(t => t.type === 'expense').length;
    insights.push({
        icon: '📝',
        text: `${incomeCount} income, ${expenseCount} expense transactions`
    });

    // Average transaction
    if (transactions.length > 0) {
        const avgIncome = totals.income / Math.max(incomeCount, 1);
        insights.push({
            icon: '💵',
            text: `Avg income: <strong>$${avgIncome.toFixed(2)}</strong>`
        });
    }

    return insights;
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// Format date
function formatDate(dateStr) {
    const date = new Date(dateStr + 'T00:00:00');
    const now = new Date();
    const diff = Math.floor((now - date) / (1000 * 60 * 60 * 24));

    if (diff === 0) return 'Today';
    if (diff === 1) return 'Yesterday';
    if (diff < 7) return date.toLocaleDateString('en-US', { weekday: 'long' });
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Update all UI elements
function updateUI() {
    updateStats();
    updateInsights();
    renderTransactions();
}

// Update dashboard stats
function updateStats() {
    const totals = calculateTotals();

    document.getElementById('totalIncome').textContent = formatCurrency(totals.income);
    document.getElementById('totalExpenses').textContent = formatCurrency(totals.expenses);

    const profitEl = document.getElementById('netProfit');
    profitEl.textContent = formatCurrency(totals.profit);
    profitEl.style.color = totals.profit >= 0 ? 'var(--accent-gold)' : 'var(--accent-red)';
}

// Update insights section
function updateInsights() {
    const insights = generateInsights();
    const container = document.getElementById('insightCards');

    if (insights.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary);">Add transactions to see insights</p>';
        return;
    }

    container.innerHTML = insights.map(insight => `
        <div class="insight-card">
            <span class="insight-icon">${insight.icon}</span>
            <span class="insight-text">${insight.text}</span>
        </div>
    `).join('');
}

// Render transactions list
function renderTransactions() {
    const container = document.getElementById('transactionList');

    let filtered = transactions;
    if (currentFilter === 'income') {
        filtered = transactions.filter(t => t.type === 'income');
    } else if (currentFilter === 'expense') {
        filtered = transactions.filter(t => t.type === 'expense');
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <p>No transactions yet. Add your first one above!</p>
            </div>
        `;
        return;
    }

    container.innerHTML = filtered.map(t => {
        const cat = CATEGORIES[t.category] || { icon: '📋', label: t.category };
        const amountClass = t.type === 'income' ? 'income' : 'expense';
        const prefix = t.type === 'income' ? '+' : '-';

        return `
            <div class="transaction-item" data-id="${t.id}">
                <div class="transaction-icon">${cat.icon}</div>
                <div class="transaction-details">
                    <div class="transaction-category">${cat.label}</div>
                    <div class="transaction-description">${t.description || 'No description'}</div>
                </div>
                <div class="transaction-meta">
                    <div class="transaction-amount ${amountClass}">${prefix}${formatCurrency(t.amount)}</div>
                    <div class="transaction-date">${formatDate(t.date)}</div>
                </div>
                <button class="transaction-delete" onclick="deleteTransaction(${t.id})" title="Delete">
                    🗑️
                </button>
            </div>
        `;
    }).join('');
}

// Initialize app
init();
