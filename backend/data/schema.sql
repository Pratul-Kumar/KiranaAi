-- ============================================================
-- ZnShop — Full Database Schema
-- Run in Supabase SQL Editor (enable ltree extension first)
-- ============================================================

-- Prerequisites
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS ltree;

-- ============================================================
-- MULTI-TENANT CORE
-- ============================================================

CREATE TABLE IF NOT EXISTS stores (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    contact_phone   TEXT UNIQUE NOT NULL,
    owner_name      TEXT NOT NULL,
    address         TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vendors (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    phone       TEXT UNIQUE NOT NULL,
    category    TEXT NOT NULL,  -- e.g. dairy, snacks, beverages
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS store_vendors (
    store_id    UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    vendor_id   UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (store_id, vendor_id)
);

-- ============================================================
-- INVENTORY
-- ============================================================

CREATE TABLE IF NOT EXISTS skus (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id        UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    category_path   ltree,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (store_id, name)
);

CREATE TABLE IF NOT EXISTS inventory (
    sku_id          UUID PRIMARY KEY REFERENCES skus(id) ON DELETE CASCADE,
    stock_level     NUMERIC NOT NULL DEFAULT 0,
    last_updated    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lost_sales (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id        UUID REFERENCES stores(id) ON DELETE CASCADE,
    sku_name        TEXT,
    requested_qty   NUMERIC,
    detected_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- CUSTOMERS & KHATA
-- ============================================================

CREATE TABLE IF NOT EXISTS customers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id        UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    phone           TEXT,
    consent_flag    BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (store_id, phone)
);

CREATE TABLE IF NOT EXISTS khata_ledger (
    customer_id         UUID PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
    balance             NUMERIC DEFAULT 0,
    lead_score          NUMERIC DEFAULT 0,
    last_payment_date   TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    store_id        UUID NOT NULL REFERENCES stores(id),
    total_amount    NUMERIC NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- REORDER WORKFLOW
-- ============================================================

CREATE TABLE IF NOT EXISTS reorder_requests (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id        UUID NOT NULL REFERENCES stores(id),
    supplier_id     UUID NOT NULL REFERENCES vendors(id),
    sku_name        TEXT NOT NULL,
    quantity        NUMERIC NOT NULL DEFAULT 1,
    unit_price      NUMERIC,
    total_amount    NUMERIC,
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending | pending_price | approved | declined
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- DEMAND SENSING
-- ============================================================

CREATE TABLE IF NOT EXISTS demand_signals (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku_id          UUID REFERENCES skus(id) ON DELETE CASCADE,
    demand_score    NUMERIC NOT NULL,
    velocity        NUMERIC,
    external_factors JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- AI OBSERVABILITY
-- ============================================================

CREATE TABLE IF NOT EXISTS ai_audit_logs (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id    TEXT,
    step        TEXT,
    input       TEXT,
    output      TEXT,
    confidence  NUMERIC,
    reasoning   TEXT,
    timestamp   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- COMPLIANCE & AUDIT
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action      TEXT NOT NULL,
    table_name  TEXT,
    record_id   TEXT,
    details     JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SECURITY (RLS)
-- ============================================================

-- For this production audit/demo, we disable RLS to allow the 
-- backend and seed scripts to operate freely. 

ALTER TABLE stores DISABLE ROW LEVEL SECURITY;
ALTER TABLE vendors DISABLE ROW LEVEL SECURITY;
ALTER TABLE store_vendors DISABLE ROW LEVEL SECURITY;
ALTER TABLE skus DISABLE ROW LEVEL SECURITY;
ALTER TABLE inventory DISABLE ROW LEVEL SECURITY;
ALTER TABLE lost_sales DISABLE ROW LEVEL SECURITY;
ALTER TABLE customers DISABLE ROW LEVEL SECURITY;
ALTER TABLE khata_ledger DISABLE ROW LEVEL SECURITY;
ALTER TABLE transactions DISABLE ROW LEVEL SECURITY;
ALTER TABLE reorder_requests DISABLE ROW LEVEL SECURITY;
ALTER TABLE demand_signals DISABLE ROW LEVEL SECURITY;
ALTER TABLE ai_audit_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY;
