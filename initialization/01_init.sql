CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL, -- 'ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    idempotency_key VARCHAR(255) PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'PROCESSING',
    response_code INT NULL,
    response_body JSONB NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    description TEXT NOT NULL,
    idempotency_key VARCHAR(255) REFERENCES idempotency_keys(idempotency_key),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id),
    amount NUMERIC(12, 4) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_entries_account ON entries(account_id);

--MOCK

INSERT INTO accounts (id, name, type) VALUES 
    ('a0000000-0000-0000-0000-000000000001', 'Revenue', 'REVENUE'),
    
    ('b0000000-0000-0000-0000-000000000002', 'Asset Account', 'ASSET'),
    
    ('c0000000-0000-0000-0000-000000000003', 'Client Account', 'LIABILITY'),
    
    ('d0000000-0000-0000-0000-000000000004', 'Member Wallet', 'LIABILITY')

ON CONFLICT (id) DO NOTHING;