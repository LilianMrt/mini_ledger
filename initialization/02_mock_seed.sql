-- Dev-only sample accounts. Do not apply to production.

INSERT INTO accounts (id, name, type) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'Revenue', 'REVENUE'),

    ('b0000000-0000-0000-0000-000000000002', 'Asset Account', 'ASSET'),

    ('c0000000-0000-0000-0000-000000000003', 'Client Account', 'LIABILITY'),

    ('d0000000-0000-0000-0000-000000000004', 'Member Wallet', 'LIABILITY')

ON CONFLICT (id) DO NOTHING;
