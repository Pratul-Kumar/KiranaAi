-- Digital Store Manager - SQL Schema (Supabase/PostgreSQL)

-- Enable LTREE extension for hierarchy if needed (optional, using path or JSONB otherwise)
CREATE EXTENSION IF NOT EXISTS ltree;

-- 1. Stores
CREATE TABLE stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    owner_name TEXT,
    contact_phone TEXT UNIQUE NOT NULL,
    location_lat DECIMAL,
    location_long DECIMAL,
    address JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Customers
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID REFERENCES stores(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    consent_flag BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB,
    UNIQUE(store_id, phone)
);

-- 3. Suppliers
CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID REFERENCES stores(id),
    name TEXT NOT NULL,
    contact_person TEXT,
    phone TEXT,
    category TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. SKUs (Hierarchical Structure)
CREATE TABLE skus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID REFERENCES stores(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category_path LTREE, -- e.g. "FMCG.Beverages.Tea"
    ean_code TEXT,
    unit TEXT DEFAULT 'pcs',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    -- embedding VECTOR(1536) -- Uncomment if pgvector is enabled
);

-- 5. Inventory
CREATE TABLE inventory (
    sku_id UUID PRIMARY KEY REFERENCES skus(id) ON DELETE CASCADE,
    stock_level DECIMAL DEFAULT 0,
    reorder_point DECIMAL DEFAULT 5,
    abc_classification CHAR(1) CHECK (abc_classification IN ('A', 'B', 'C')),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Transactions
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID REFERENCES stores(id),
    customer_id UUID REFERENCES customers(id),
    items JSONB NOT NULL, -- List of {sku_id, quantity, price}
    total_amount DECIMAL NOT NULL,
    payment_type TEXT CHECK (payment_type IN ('cash', 'khata', 'digital')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. Khata Ledger
CREATE TABLE khata_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    balance DECIMAL DEFAULT 0, -- Positive means customer owes shop
    last_payment_date TIMESTAMP WITH TIME ZONE,
    lead_score DECIMAL DEFAULT 0, -- Calculated lead/reliability score
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 8. Lost Sales
CREATE TABLE lost_sales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID REFERENCES stores(id),
    sku_name TEXT,
    requested_qty DECIMAL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 9. Demand Signals
CREATE TABLE demand_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku_id UUID REFERENCES skus(id),
    demand_score DECIMAL DEFAULT 0,
    velocity DECIMAL,
    external_factors JSONB, -- {weather: 'Rainy', festival: 'Holi'}
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 10. Audit Log & Compliance
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action TEXT NOT NULL,
    table_name TEXT,
    record_id UUID,
    performed_by UUID,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    details JSONB
);

-- Indexes
CREATE INDEX idx_skus_hierarchy ON skus USING GIST (category_path);
CREATE INDEX idx_transactions_store ON transactions(store_id);
CREATE INDEX idx_inventory_abc ON inventory(abc_classification);
