-- 🚀 QUICKSTART: Run this in Supabase SQL Editor to enable your test number

-- 1. Create the store for your provided number
INSERT INTO stores (name, contact_phone, owner_name)
VALUES ('My Test Kirana', '15551551425', 'Pratul')
ON CONFLICT (contact_phone) DO NOTHING;

-- 2. Get the ID of the store we just created
DO $$
DECLARE
    v_store_id UUID;
BEGIN
    SELECT id INTO v_store_id FROM stores WHERE contact_phone = '15551551425';

    -- 3. Add a sample SKU so the "milk" update works
    INSERT INTO skus (store_id, name, category_path)
    VALUES (v_store_id, 'Milk', 'Dairy')
    ON CONFLICT DO NOTHING;

    -- 4. Initialize inventory for that SKU
    INSERT INTO inventory (sku_id, stock_level)
    SELECT id, 10 FROM skus WHERE store_id = v_store_id AND name = 'Milk'
    ON CONFLICT DO NOTHING;
END $$;
