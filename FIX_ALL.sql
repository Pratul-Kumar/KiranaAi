-- 🛠️ FIX_ALL: Run this in Supabase SQL Editor to reset and fix everything

-- 1. Create all missing tables
CREATE TABLE IF NOT EXISTS stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    owner_name TEXT,
    contact_phone TEXT UNIQUE NOT NULL,
    location_lat DECIMAL,
    location_long DECIMAL,
    address JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID REFERENCES stores(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    consent_flag BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB,
    UNIQUE(store_id, phone)
);

CREATE TABLE IF NOT EXISTS suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID REFERENCES stores(id),
    name TEXT NOT NULL,
    contact_person TEXT,
    phone TEXT,
    category TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS skus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID REFERENCES stores(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category_path TEXT, -- Simplifed from LTREE for guaranteed success
    ean_code TEXT,
    unit TEXT DEFAULT 'pcs',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inventory (
    sku_id UUID PRIMARY KEY REFERENCES skus(id) ON DELETE CASCADE,
    stock_level DECIMAL DEFAULT 0,
    reorder_point DECIMAL DEFAULT 5,
    abc_classification CHAR(1),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lost_sales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID REFERENCES stores(id),
    sku_name TEXT,
    requested_qty DECIMAL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Insert Test Data for your number
INSERT INTO stores (name, contact_phone, owner_name)
VALUES ('My Test Kirana', '15551551425', 'Pratul')
ON CONFLICT (contact_phone) DO NOTHING;

DO $$
DECLARE
    v_store_id UUID;
BEGIN
    SELECT id INTO v_store_id FROM stores WHERE contact_phone = '15551551425';

    INSERT INTO skus (store_id, name)
    VALUES (v_store_id, 'Milk')
    ON CONFLICT DO NOTHING;

    INSERT INTO inventory (sku_id, stock_level)
    SELECT id, 10 FROM skus WHERE store_id = v_store_id AND name = 'Milk'
    ON CONFLICT DO NOTHING;
END $$;
