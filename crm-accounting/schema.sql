-- ============================================
-- BIM OPS STUDIO — CRM & ACCOUNTING DATABASE
-- ============================================
-- Location: Used via SQLite MCP server
-- Created: 2026-02-24
-- ============================================

-- CLIENTS — People/companies Weber works for
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    company TEXT,
    email TEXT,
    phone TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    type TEXT DEFAULT 'residential',  -- residential, commercial, developer, architect, contractor
    source TEXT,                        -- referral, google, repeat, direct, word-of-mouth
    default_rate REAL DEFAULT 85.00,    -- hourly rate
    notes TEXT,
    tags TEXT,                          -- JSON array
    status TEXT DEFAULT 'active',       -- active, inactive, prospect
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- PROJECTS — Individual jobs
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT,               -- cd-set, permit-drawings, as-builts, consulting, design, renovation, addition
    status TEXT DEFAULT 'active',  -- prospect, active, on-hold, completed, archived
    start_date TEXT,
    end_date TEXT,
    budget REAL,
    actual_cost REAL DEFAULT 0,
    address TEXT,            -- project/site address
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

-- INVOICES — What gets billed
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    client_id INTEGER NOT NULL,
    invoice_number TEXT NOT NULL UNIQUE,  -- INV-2026-001
    date_issued TEXT NOT NULL,
    date_due TEXT NOT NULL,
    subtotal REAL DEFAULT 0,
    tax_rate REAL DEFAULT 0,
    tax_amount REAL DEFAULT 0,
    total REAL DEFAULT 0,
    amount_paid REAL DEFAULT 0,
    status TEXT DEFAULT 'draft',  -- draft, sent, paid, partial, overdue, void
    notes TEXT,
    date_paid TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

-- INVOICE ITEMS — Line items on invoices
CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    quantity REAL DEFAULT 1,
    unit_price REAL NOT NULL,
    amount REAL NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

-- PAYMENTS — Money received
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER,
    client_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    date TEXT NOT NULL,
    method TEXT DEFAULT 'zelle',  -- zelle, check, wire, cash, venmo, ach
    reference TEXT,               -- check #, confirmation code, etc.
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

-- EXPENSES — Money spent
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    category TEXT NOT NULL,  -- software, hardware, travel, materials, subscriptions, office, marketing, professional, insurance, vehicle, meals, other
    description TEXT NOT NULL,
    vendor TEXT,
    amount REAL NOT NULL,
    date TEXT NOT NULL,
    receipt_path TEXT,
    tax_deductible INTEGER DEFAULT 1,  -- 1=yes, 0=no
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- TIME ENTRIES — Hours worked
CREATE TABLE IF NOT EXISTS time_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    client_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    hours REAL NOT NULL,
    rate REAL NOT NULL,
    date TEXT NOT NULL,
    billable INTEGER DEFAULT 1,   -- 1=billable, 0=non-billable
    invoiced INTEGER DEFAULT 0,   -- 1=already on an invoice
    invoice_id INTEGER,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

-- ============================================
-- VIEWS — Common queries as views
-- ============================================

-- Outstanding AR
CREATE VIEW IF NOT EXISTS v_outstanding_ar AS
SELECT
    i.invoice_number,
    c.name AS client_name,
    p.name AS project_name,
    i.total,
    i.amount_paid,
    (i.total - i.amount_paid) AS balance_due,
    i.date_issued,
    i.date_due,
    i.status,
    CAST(julianday('now') - julianday(i.date_due) AS INTEGER) AS days_overdue
FROM invoices i
JOIN clients c ON i.client_id = c.id
LEFT JOIN projects p ON i.project_id = p.id
WHERE i.status IN ('sent', 'partial', 'overdue')
ORDER BY i.date_due;

-- Unbilled time
CREATE VIEW IF NOT EXISTS v_unbilled_time AS
SELECT
    t.id,
    c.name AS client_name,
    p.name AS project_name,
    t.description,
    t.hours,
    t.rate,
    (t.hours * t.rate) AS amount,
    t.date
FROM time_entries t
JOIN clients c ON t.client_id = c.id
JOIN projects p ON t.project_id = p.id
WHERE t.billable = 1 AND t.invoiced = 0
ORDER BY t.date;

-- Monthly P&L
CREATE VIEW IF NOT EXISTS v_monthly_summary AS
SELECT
    strftime('%Y-%m', date) AS month,
    'revenue' AS type,
    SUM(amount) AS total
FROM payments
GROUP BY strftime('%Y-%m', date)
UNION ALL
SELECT
    strftime('%Y-%m', date) AS month,
    'expense' AS type,
    SUM(amount) AS total
FROM expenses
GROUP BY strftime('%Y-%m', date)
ORDER BY month, type;

-- Client revenue
CREATE VIEW IF NOT EXISTS v_client_revenue AS
SELECT
    c.id AS client_id,
    c.name AS client_name,
    c.company,
    COUNT(DISTINCT p.id) AS total_projects,
    COUNT(DISTINCT i.id) AS total_invoices,
    COALESCE(SUM(DISTINCT i.total), 0) AS total_billed,
    COALESCE((SELECT SUM(amount) FROM payments WHERE client_id = c.id), 0) AS total_paid
FROM clients c
LEFT JOIN projects p ON c.id = p.client_id
LEFT JOIN invoices i ON c.id = i.client_id AND i.status != 'void'
GROUP BY c.id
ORDER BY total_paid DESC;
