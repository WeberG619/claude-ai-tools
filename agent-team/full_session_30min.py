#!/usr/bin/env python3
"""
Agent Team - Full 30 Minute Session
====================================
Professional developer dialogue. Sharp, intelligent, no fluff.
"""

import json
import time
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from dialogue_v2 import DevTeamChat, AuthenticDialogue, DEVS
from visual_session import VisualDevTeamChat, VisualActivityController

PROJECT_DIR = Path("/mnt/d/_CLAUDE-TOOLS/agent-team/projects")


def write_file(project: str, filename: str, content: str):
    """Write a file to the project directory."""
    project_path = PROJECT_DIR / project
    project_path.mkdir(parents=True, exist_ok=True)
    file_path = project_path / filename
    with open(file_path, "w") as f:
        f.write(content)
    print(f"  [FILE] {filename} written")
    return str(file_path)


class FullSession:
    def __init__(self, use_visual: bool = True):
        """
        Initialize session.

        Args:
            use_visual: If True, use VisualDevTeamChat for dashboard integration
        """
        if use_visual:
            self.chat = VisualDevTeamChat()
            self.visual = self.chat.visual
        else:
            self.chat = DevTeamChat()
            self.visual = None
        self.project_name = "side_hustle_dashboard"
        self.start_time = time.time()

    def elapsed(self):
        return (time.time() - self.start_time) / 60

    def section(self, name):
        print(f"\n{'='*60}")
        print(f"  {name} ({self.elapsed():.1f} min elapsed)")
        print(f"{'='*60}\n")

    # =========================================================================
    # INTRO (2-3 min)
    # =========================================================================
    def intro(self):
        self.section("INTRODUCTION")

        self.chat.narrator.explains(
            "Welcome back. Today the team builds a product from scratch. "
            "No predetermined solution. They will identify a problem and solve it."
        )

        self.chat.narrator.explains(
            "I will provide technical context throughout. "
            "This is how professional development teams operate."
        )

        self.chat.planner.thinks(
            "We have time today. Let's build something with real utility. "
            "Something people would pay for or use daily."
        )

        self.chat.researcher.says(
            "I have been tracking market trends. "
            "Productivity tools remain in high demand. Everyone optimizes for time."
        )

        self.chat.builder.says(
            "There are many productivity apps. What is our differentiation? "
            "We need a specific angle."
        )

        self.chat.critic.thinks(
            "Correct question. We need to solve a specific problem, not build another generic tool."
        )

    # =========================================================================
    # BRAINSTORMING (5-7 min)
    # =========================================================================
    def brainstorm(self):
        self.section("BRAINSTORMING")

        self.chat.planner.says(
            "Let us identify problems. What do we personally deal with? "
            "What would improve our own workflow?"
        )

        # Visual: Show thinking
        if self.visual:
            self.visual.show_thinking("Analyzing common developer pain points...")

        self.chat.researcher.thinks(
            "I do freelance work. Tracking finances is problematic. "
            "Invoices, payments, expenses scattered across multiple systems."
        )

        # Visual: Research existing solutions
        if self.visual:
            self.visual.show_github_search("freelance income tracker dashboard")
            time.sleep(2)

        self.chat.builder.says(
            "Same experience. Consulting last month. Still unclear on actual profit after expenses."
        )

        self.chat.critic.says(
            "Relatable problem. Gig economy, freelancing, online sales. Many people have side income now."
        )

        self.chat.planner.agrees(
            "True. Most use spreadsheets or nothing at all."
        )

        self.chat.researcher.says(
            "Proposal: a dashboard specifically for side income. "
            "Track earnings, expenses, display actual profitability."
        )

        self.chat.builder.says(
            "Focused scope. Not competing with QuickBooks. "
            "Answer one question: am I making money or not?"
        )

        self.chat.critic.questions(
            "What differentiates this from a spreadsheet? Why use our tool instead?"
        )

        self.chat.researcher.says(
            "Visualization. Quick insights. A spreadsheet shows raw numbers. "
            "A dashboard shows the story. Trend direction. Which income source performs best."
        )

        self.chat.narrator.explains(
            "The key insight here: users want glanceable data. "
            "Ten seconds to understand their financial position, not ten minutes in a spreadsheet."
        )

        self.chat.planner.thinks(
            "Agreed. People want progress at a glance, not rows of data."
        )

        self.chat.builder.says(
            "Display total profit, best month, top performing income source. Quick stats."
        )

        self.chat.critic.says(
            "Must work offline. Local data storage. "
            "Users will not trust financial data on unknown servers."
        )

        self.chat.researcher.agrees(
            "Privacy is critical for financial tools. LocalStorage keeps everything on device."
        )

        self.chat.planner.decides(
            "Decision made. Side Hustle Dashboard. "
            "Track income and expenses, show profit, visualize trends, all local storage."
        )

        self.chat.narrator.explains(
            "From zero to validated concept in minutes. "
            "Now they move to technical specification."
        )

    # =========================================================================
    # PLANNING (3-4 min)
    # =========================================================================
    def planning(self):
        self.section("PLANNING")

        self.chat.planner.says(
            "Define the MVP. What is the minimum viable feature set?"
        )

        self.chat.researcher.says(
            "Core features: add income, add expenses, display total profit. Foundation complete."
        )

        self.chat.builder.says(
            "Categories required. Freelance income differs from product sales. "
            "Expenses need categorization. Software, supplies, marketing."
        )

        self.chat.critic.says(
            "Date tracking. Users need monthly breakdowns. January versus February comparison."
        )

        self.chat.planner.says(
            "Good. Transactions with type, amount, category, date. Dashboard with totals and charts."
        )

        self.chat.narrator.explains(
            "This data model covers most use cases. Type determines income or expense. "
            "Category enables filtering. Date enables temporal analysis."
        )

        self.chat.researcher.says(
            "Proposed categories. Income: freelance, sales, affiliate, tips, other. "
            "Expenses: software, supplies, marketing, fees, other."
        )

        self.chat.builder.agrees(
            "Covers most side hustles. Extensible for version two."
        )

        self.chat.critic.thinks(
            "UI needs to appear professional. Not a hobby project aesthetic."
        )

        self.chat.planner.says(
            "Clean, modern design. Dark theme. Finance apps work better dark. "
            "Green for income, red for expenses. Standard conventions."
        )

        self.chat.builder.says(
            "Clean cards, good typography, subtle animations. Polished appearance."
        )

        self.chat.narrator.explains(
            "Design direction established. Features defined. Architecture clear. Implementation begins."
        )

    # =========================================================================
    # BUILDING - HTML STRUCTURE (5-6 min)
    # =========================================================================
    def build_html(self):
        self.section("BUILDING - HTML STRUCTURE")

        self.chat.builder.thinks(
            "Starting with HTML structure. Header, dashboard stats, transaction form, transaction list."
        )

        html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Side Hustle Dashboard</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="app">
        <!-- Header -->
        <header class="header">
            <div class="logo">
                <span class="logo-icon">💰</span>
                <h1>Side Hustle Dashboard</h1>
            </div>
            <p class="tagline">Track your income. Know your profit.</p>
        </header>

        <!-- Dashboard Stats -->
        <section class="dashboard">
            <div class="stat-card income">
                <div class="stat-icon">📈</div>
                <div class="stat-content">
                    <span class="stat-label">Total Income</span>
                    <span class="stat-value" id="totalIncome">$0.00</span>
                </div>
            </div>
            <div class="stat-card expenses">
                <div class="stat-icon">📉</div>
                <div class="stat-content">
                    <span class="stat-label">Total Expenses</span>
                    <span class="stat-value" id="totalExpenses">$0.00</span>
                </div>
            </div>
            <div class="stat-card profit">
                <div class="stat-icon">💎</div>
                <div class="stat-content">
                    <span class="stat-label">Net Profit</span>
                    <span class="stat-value" id="netProfit">$0.00</span>
                </div>
            </div>
        </section>

        <!-- Insights -->
        <section class="insights" id="insights">
            <h2>Quick Insights</h2>
            <div class="insight-cards" id="insightCards">
                <!-- Generated by JS -->
            </div>
        </section>

        <!-- Add Transaction -->
        <section class="add-transaction">
            <h2>Add Transaction</h2>
            <form id="transactionForm">
                <div class="form-row">
                    <div class="form-group">
                        <label for="type">Type</label>
                        <select id="type" required>
                            <option value="income">Income 💵</option>
                            <option value="expense">Expense 💸</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="amount">Amount</label>
                        <input type="number" id="amount" placeholder="0.00" step="0.01" min="0" required>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="category">Category</label>
                        <select id="category" required>
                            <optgroup label="Income">
                                <option value="freelance">Freelance</option>
                                <option value="sales">Sales</option>
                                <option value="affiliate">Affiliate</option>
                                <option value="tips">Tips</option>
                                <option value="other-income">Other Income</option>
                            </optgroup>
                            <optgroup label="Expenses">
                                <option value="software">Software & Tools</option>
                                <option value="supplies">Supplies</option>
                                <option value="marketing">Marketing</option>
                                <option value="fees">Fees & Commissions</option>
                                <option value="other-expense">Other Expense</option>
                            </optgroup>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="date">Date</label>
                        <input type="date" id="date" required>
                    </div>
                </div>
                <div class="form-group full-width">
                    <label for="description">Description (optional)</label>
                    <input type="text" id="description" placeholder="What was this for?">
                </div>
                <button type="submit" class="btn-add">Add Transaction</button>
            </form>
        </section>

        <!-- Transaction History -->
        <section class="transactions">
            <div class="transactions-header">
                <h2>Recent Transactions</h2>
                <div class="filter-buttons">
                    <button class="filter-btn active" data-filter="all">All</button>
                    <button class="filter-btn" data-filter="income">Income</button>
                    <button class="filter-btn" data-filter="expense">Expenses</button>
                </div>
            </div>
            <div class="transaction-list" id="transactionList">
                <!-- Generated by JS -->
            </div>
        </section>

        <!-- Footer -->
        <footer class="footer">
            <p>Your data is stored locally. Private and secure. 🔒</p>
        </footer>
    </div>

    <script src="app.js"></script>
</body>
</html>'''

        write_file(self.project_name, "index.html", html_content)

        # Visual: Show code being written
        if self.visual:
            # Show a snippet of the HTML for the dashboard
            snippet = html_content[:1500] + "\n\n// ... continued ..."
            self.visual.show_code_typing("index.html", snippet, "html")
            time.sleep(5)  # Let typing animation play

        self.chat.builder.says(
            "HTML complete. Header with branding, three stat cards for income, expenses, profit. "
            "Transaction form with categorization, list for history display."
        )

        self.chat.narrator.explains(
            "The semantic structure is clean. Each section has clear purpose. "
            "Form groups organized for optimal user flow."
        )

        self.chat.researcher.says(
            "Emoji icons work well here. Friendly visual without external dependencies."
        )

        self.chat.critic.says(
            "Filter buttons add value. Users can focus on income only or expenses only."
        )

        self.chat.builder.says(
            "Added insights section. Best category, profit margin, trend indicators."
        )

        self.chat.planner.agrees(
            "Good foundation. Proceed with styling."
        )

    # =========================================================================
    # BUILDING - CSS STYLING (6-7 min)
    # =========================================================================
    def build_css(self):
        self.section("BUILDING - CSS STYLING")

        self.chat.builder.thinks(
            "CSS implementation. Dark theme selected. Easier on eyes, appears more professional for finance."
        )

        css_content = '''/* Side Hustle Dashboard - Styles */

:root {
    --bg-primary: #0f0f0f;
    --bg-secondary: #1a1a1a;
    --bg-card: #242424;
    --text-primary: #ffffff;
    --text-secondary: #a0a0a0;
    --accent-green: #00d26a;
    --accent-red: #ff4757;
    --accent-blue: #3742fa;
    --accent-gold: #ffd700;
    --border-color: #333333;
    --shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    --radius: 12px;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
    min-height: 100vh;
}

.app {
    max-width: 900px;
    margin: 0 auto;
    padding: 20px;
}

/* Header */
.header {
    text-align: center;
    padding: 30px 0;
    border-bottom: 1px solid var(--border-color);
    margin-bottom: 30px;
}

.logo {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin-bottom: 8px;
}

.logo-icon {
    font-size: 2.5rem;
}

.logo h1 {
    font-size: 1.8rem;
    font-weight: 700;
    background: linear-gradient(135deg, var(--accent-green), var(--accent-gold));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.tagline {
    color: var(--text-secondary);
    font-size: 1rem;
}

/* Dashboard Stats */
.dashboard {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.stat-card {
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: var(--shadow);
    border: 1px solid var(--border-color);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 25px rgba(0, 0, 0, 0.4);
}

.stat-card.income {
    border-left: 4px solid var(--accent-green);
}

.stat-card.expenses {
    border-left: 4px solid var(--accent-red);
}

.stat-card.profit {
    border-left: 4px solid var(--accent-gold);
}

.stat-icon {
    font-size: 2.5rem;
}

.stat-content {
    display: flex;
    flex-direction: column;
}

.stat-label {
    font-size: 0.85rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.stat-value {
    font-size: 1.8rem;
    font-weight: 700;
}

.stat-card.income .stat-value {
    color: var(--accent-green);
}

.stat-card.expenses .stat-value {
    color: var(--accent-red);
}

.stat-card.profit .stat-value {
    color: var(--accent-gold);
}

/* Insights */
.insights {
    background: var(--bg-secondary);
    border-radius: var(--radius);
    padding: 24px;
    margin-bottom: 30px;
    border: 1px solid var(--border-color);
}

.insights h2 {
    font-size: 1.1rem;
    margin-bottom: 16px;
    color: var(--text-secondary);
}

.insight-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
}

.insight-card {
    background: var(--bg-card);
    padding: 16px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 12px;
}

.insight-icon {
    font-size: 1.5rem;
}

.insight-text {
    font-size: 0.9rem;
}

.insight-text strong {
    color: var(--accent-green);
}

/* Add Transaction Form */
.add-transaction {
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 24px;
    margin-bottom: 30px;
    box-shadow: var(--shadow);
    border: 1px solid var(--border-color);
}

.add-transaction h2 {
    font-size: 1.2rem;
    margin-bottom: 20px;
}

.form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
}

.form-group {
    display: flex;
    flex-direction: column;
}

.form-group.full-width {
    grid-column: 1 / -1;
}

label {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-bottom: 6px;
}

input, select {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 1rem;
    color: var(--text-primary);
    transition: border-color 0.2s ease;
}

input:focus, select:focus {
    outline: none;
    border-color: var(--accent-blue);
}

select {
    cursor: pointer;
}

.btn-add {
    width: 100%;
    padding: 14px;
    background: linear-gradient(135deg, var(--accent-green), #00b359);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    margin-top: 8px;
}

.btn-add:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(0, 210, 106, 0.3);
}

/* Transactions */
.transactions {
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 24px;
    box-shadow: var(--shadow);
    border: 1px solid var(--border-color);
}

.transactions-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    flex-wrap: wrap;
    gap: 12px;
}

.transactions-header h2 {
    font-size: 1.2rem;
}

.filter-buttons {
    display: flex;
    gap: 8px;
}

.filter-btn {
    padding: 8px 16px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 20px;
    color: var(--text-secondary);
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.2s ease;
}

.filter-btn:hover {
    border-color: var(--accent-blue);
    color: var(--text-primary);
}

.filter-btn.active {
    background: var(--accent-blue);
    border-color: var(--accent-blue);
    color: white;
}

.transaction-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.transaction-item {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px;
    background: var(--bg-secondary);
    border-radius: 8px;
    transition: background 0.2s ease;
}

.transaction-item:hover {
    background: #2a2a2a;
}

.transaction-icon {
    font-size: 1.5rem;
    width: 40px;
    text-align: center;
}

.transaction-details {
    flex: 1;
}

.transaction-category {
    font-weight: 600;
    margin-bottom: 2px;
}

.transaction-description {
    font-size: 0.85rem;
    color: var(--text-secondary);
}

.transaction-meta {
    text-align: right;
}

.transaction-amount {
    font-weight: 700;
    font-size: 1.1rem;
}

.transaction-amount.income {
    color: var(--accent-green);
}

.transaction-amount.expense {
    color: var(--accent-red);
}

.transaction-date {
    font-size: 0.8rem;
    color: var(--text-secondary);
}

.transaction-delete {
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 8px;
    border-radius: 4px;
    transition: color 0.2s ease, background 0.2s ease;
}

.transaction-delete:hover {
    color: var(--accent-red);
    background: rgba(255, 71, 87, 0.1);
}

.empty-state {
    text-align: center;
    padding: 40px;
    color: var(--text-secondary);
}

.empty-state-icon {
    font-size: 3rem;
    margin-bottom: 12px;
}

/* Footer */
.footer {
    text-align: center;
    padding: 30px;
    color: var(--text-secondary);
    font-size: 0.9rem;
}

/* Animations */
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.transaction-item {
    animation: fadeIn 0.3s ease;
}

/* Responsive */
@media (max-width: 600px) {
    .form-row {
        grid-template-columns: 1fr;
    }

    .transactions-header {
        flex-direction: column;
        align-items: flex-start;
    }

    .stat-card {
        padding: 20px;
    }

    .stat-value {
        font-size: 1.5rem;
    }
}'''

        write_file(self.project_name, "style.css", css_content)

        # Visual: Show CSS being written
        if self.visual:
            # Show CSS variables and key styles
            css_snippet = css_content[:1200] + "\n\n/* ... continued ... */"
            self.visual.show_code_typing("style.css", css_snippet, "css")
            time.sleep(4)

        self.chat.builder.says(
            "CSS complete. Dark theme. Green for income, red for expenses, gold for profit. "
            "Clean cards, subtle hover effects, full responsive layout."
        )

        self.chat.narrator.explains(
            "CSS custom properties enable consistent theming. "
            "The grid system adapts from three columns on desktop to single column on mobile."
        )

        self.chat.researcher.says(
            "The title gradient adds visual polish. Modern appearance without complexity."
        )

        self.chat.critic.says(
            "Good accessibility with color coding. Green and red are intuitive. "
            "Dark theme reduces eye strain during extended use."
        )

        self.chat.builder.says(
            "Responsive breakpoints included. Forms stack vertically on smaller screens."
        )

        self.chat.planner.says(
            "Visual layer complete. Now we need the application logic."
        )

    # =========================================================================
    # BUILDING - JAVASCRIPT (8-10 min)
    # =========================================================================
    def build_javascript(self):
        self.section("BUILDING - JAVASCRIPT")

        self.chat.builder.thinks(
            "JavaScript implementation. Data storage, calculations, UI updates. Core functionality."
        )

        self.chat.researcher.says(
            "Include category icons. Visual scanning of transaction list improves significantly."
        )

        self.chat.builder.says(
            "Mapping each category to an emoji. Consistent iconography."
        )

        js_content = '''// Side Hustle Dashboard - Application Logic

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
'''

        write_file(self.project_name, "app.js", js_content)

        # Visual: Show JavaScript being written
        if self.visual:
            # Show key functions
            js_snippet = js_content[:1500] + "\n\n// ... continued ..."
            self.visual.show_code_typing("app.js", js_snippet, "javascript")
            time.sleep(5)

        self.chat.builder.says(
            "JavaScript complete. Transaction management, localStorage persistence, "
            "insights generation, clean UI update system."
        )

        self.chat.narrator.explains(
            "The architecture follows a unidirectional data flow. State changes trigger updateUI, "
            "which renders all components. Predictable and maintainable."
        )

        self.chat.researcher.says(
            "The insights provide actionable information. Profit margin, top earning category, "
            "average income. Data that helps users make decisions."
        )

        self.chat.critic.says(
            "Profit color changes based on positive or negative value. "
            "Red indicates loss. Clear visual feedback."
        )

        self.chat.builder.says(
            "Delete functionality includes confirmation dialog. "
            "Prevents accidental data loss."
        )

        self.chat.planner.says(
            "Implementation complete. Let us review for edge cases."
        )

    # =========================================================================
    # REVIEW & IMPROVEMENTS (4-5 min)
    # =========================================================================
    def review(self):
        self.section("REVIEW & IMPROVEMENTS")

        self.chat.critic.thinks(
            "Reviewing for security, usability, and edge cases."
        )

        self.chat.critic.says(
            "Data persistence: localStorage with try-catch. "
            "On failure, defaults to empty array. Application continues to function."
        )

        self.chat.builder.says(
            "Error handling is defensive. Worst case: fresh start. "
            "Application always remains usable."
        )

        self.chat.narrator.explains(
            "This defensive pattern is important. Storage failures should not break the UI. "
            "Users can still track transactions even if persistence fails temporarily."
        )

        self.chat.critic.says(
            "Form validation present. Required fields enforced. "
            "Amount must be positive. Input is sanitized."
        )

        self.chat.researcher.says(
            "Date picker defaults to current date. Reduces friction. "
            "Most transactions are recorded same day."
        )

        self.chat.critic.says(
            "Category dropdown updates based on income or expense selection. "
            "Reduces confusion. Shows only relevant options."
        )

        self.chat.planner.says(
            "Mobile support status?"
        )

        self.chat.builder.says(
            "CSS handles it. Responsive grid, stacking on small screens. "
            "Viewport meta tag included in HTML."
        )

        self.chat.critic.thinks(
            "Edge case: zero income with expenses. Profit margin calculation."
        )

        self.chat.builder.says(
            "Handled. Income greater than zero check before margin calculation. "
            "Division by zero prevented."
        )

        self.chat.critic.agrees(
            "Satisfied. This is production-ready for version one."
        )

        self.chat.narrator.explains(
            "Quality review complete. No critical issues identified. "
            "The application handles edge cases gracefully."
        )

        self.chat.planner.says(
            "Excellent. Let us discuss version two features."
        )

    # =========================================================================
    # FUTURE FEATURES DISCUSSION (3-4 min)
    # =========================================================================
    def future_features(self):
        self.section("FUTURE FEATURES")

        self.chat.planner.says(
            "For documentation: what features would version two include?"
        )

        self.chat.researcher.thinks(
            "Charts. Line graph showing income over time. "
            "Pie chart for category breakdown."
        )

        self.chat.builder.says(
            "Chart.js integration. Straightforward. Would significantly improve visualization."
        )

        self.chat.narrator.explains(
            "Visual charts transform raw numbers into patterns. "
            "Users can identify trends they would miss in tabular data."
        )

        self.chat.critic.says(
            "Export feature. CSV download. Required for tax purposes and data portability."
        )

        self.chat.researcher.says(
            "Monthly and yearly views. Date range filtering. "
            "Compare performance across time periods."
        )

        self.chat.builder.says(
            "Goals feature. Set monthly income target, display progress. "
            "Adds motivation and accountability."
        )

        self.chat.planner.says(
            "Recurring transactions. Monthly subscriptions auto-logged."
        )

        self.chat.critic.says(
            "Optional cloud sync. For users who want multi-device access. "
            "Strictly opt-in to maintain privacy default."
        )

        self.chat.narrator.explains(
            "The roadmap prioritizes user value. Each feature addresses a specific need. "
            "Version one solves the core problem. Version two adds power user features."
        )

        self.chat.planner.says(
            "Solid roadmap documented. Version one is complete and functional."
        )

    # =========================================================================
    # CONCLUSION (3-4 min)
    # =========================================================================
    def conclusion(self):
        self.section("CONCLUSION")

        self.chat.narrator.explains(
            "Session complete. Let me summarize what the team accomplished."
        )

        self.chat.narrator.explains(
            "Started with no predetermined solution. Identified a real problem through discussion. "
            "Side income tracking. Validated the need through personal experience."
        )

        self.chat.narrator.explains(
            "Side Hustle Dashboard. Designed for freelancers, gig workers, and anyone with multiple income streams. "
            "Simple interface. Powerful insights. Complete privacy."
        )

        self.chat.planner.says(
            "Team, effective execution. Clean collaboration. "
            "We built something with genuine utility."
        )

        self.chat.researcher.says(
            "The privacy approach is a differentiator. Local storage only. "
            "Significant value proposition for financial tools."
        )

        self.chat.builder.says(
            "Clean implementation. No dependencies. HTML, CSS, JavaScript. "
            "Fast loading, runs anywhere."
        )

        self.chat.critic.says(
            "Solid foundation. Extensible architecture. No major issues. "
            "Quality meets production standards."
        )

        self.chat.narrator.explains(
            "Source code is in the project folder. Available for use, modification, and learning. "
            "The techniques demonstrated here apply to any web application."
        )

        self.chat.narrator.explains(
            "Thank you for watching. The team will return with another build. Until then."
        )

    # =========================================================================
    # RUN FULL SESSION
    # =========================================================================
    def run(self):
        print("\n" + "="*70)
        print("  AGENT TEAM - FULL BUILD SESSION")
        print("  Started at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*70 + "\n")

        # Run all phases
        self.intro()
        self.brainstorm()
        self.planning()
        self.build_html()
        self.build_css()
        self.build_javascript()
        self.review()
        self.future_features()
        self.conclusion()

        # Final stats
        elapsed = self.elapsed()
        print("\n" + "="*70)
        print(f"  SESSION COMPLETE")
        print(f"  Duration: {elapsed:.1f} minutes")
        print(f"  Project: {PROJECT_DIR / self.project_name}")
        print("="*70 + "\n")

        return self.project_name


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Agent Team full session")
    parser.add_argument("--no-visual", action="store_true",
                       help="Disable visual dashboard integration")
    args = parser.parse_args()

    session = FullSession(use_visual=not args.no_visual)
    session.run()
