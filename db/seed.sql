USE multivendor_db;
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE audit_logs;
TRUNCATE TABLE order_items;
TRUNCATE TABLE orders;
TRUNCATE TABLE cart_items;
TRUNCATE TABLE carts;
TRUNCATE TABLE coupons;
TRUNCATE TABLE product_reviews;
TRUNCATE TABLE product_images;
TRUNCATE TABLE product_variants;
TRUNCATE TABLE products;
TRUNCATE TABLE categories;
TRUNCATE TABLE users;
TRUNCATE TABLE tenant_billing_logs;
TRUNCATE TABLE tenant_settings;
TRUNCATE TABLE tenants;
TRUNCATE TABLE subscription_plans;

INSERT INTO subscription_plans (id, code, name, price_monthly, max_products, max_storage_mb) VALUES 
(1, 'free', 'Free Plan', 0.00, 50, 500),
(2, 'pro', 'Pro Plan', 29.99, 1000, 5000),
(3, 'enterprise', 'Enterprise Plan', 199.99, 999999, 50000);

INSERT INTO tenants (id, slug, name, plan_id, status) VALUES 
(1, 'tenant-a', 'Store A', 1, 'active'),
(2, 'tenant-b', 'Store B', 2, 'active');

INSERT INTO users (id, tenant_id, email, password_hash, full_name, role) VALUES 
(1, NULL, 'super@admin.com', '$2b$12$pYA7SjOOz.QHHGZMMqGqUu6tH9/MiUsyzKD/./VR.1OJJ4yzf8ZNu', 'Super Admin', 'super_admin'),
(2, 1, 'admin@tenanta.com', '$2b$12$pYA7SjOOz.QHHGZMMqGqUu6tH9/MiUsyzKD/./VR.1OJJ4yzf8ZNu', 'Tenant A Admin', 'tenant_admin'),
(3, 2, 'admin@tenantb.com', '$2b$12$pYA7SjOOz.QHHGZMMqGqUu6tH9/MiUsyzKD/./VR.1OJJ4yzf8ZNu', 'Tenant B Admin', 'tenant_admin'),
(4, 1, 'customer@tenanta.com', '$2b$12$pYA7SjOOz.QHHGZMMqGqUu6tH9/MiUsyzKD/./VR.1OJJ4yzf8ZNu', 'Customer A', 'customer'),
(5, 2, 'customer@tenantb.com', '$2b$12$pYA7SjOOz.QHHGZMMqGqUu6tH9/MiUsyzKD/./VR.1OJJ4yzf8ZNu', 'Customer B', 'customer');

INSERT INTO products (id, tenant_id, name, slug, base_price, is_active) VALUES 
(1, 1, 'Product A1', 'product-a1', 10.00, 1),
(2, 2, 'Product B1', 'product-b1', 20.00, 1);

INSERT INTO orders (id, tenant_id, user_id, order_number, subtotal, total_amount, status) VALUES 
(1, 1, 4, 'ORD-001', 100.00, 100.00, 'pending');

INSERT INTO product_reviews (id, tenant_id, product_id, user_id, rating, comment, approved) VALUES 
(1, 1, 1, 4, 5, 'Great product', 0);
INSERT INTO product_variants (id, tenant_id, product_id, sku, stock_quantity) VALUES 
(1, 1, 1, 'SKU-A1-1', 10);

INSERT INTO coupons (id, tenant_id, code, discount_type, discount_val, min_order_amt, usage_limit, used_count, valid_until) VALUES
(1, 1, 'VALID10', 'percentage', 10.00, 0.00, 100, 0, '2037-12-31 23:59:59'),
(2, 1, 'EXPIRED', 'percentage', 10.00, 0.00, 100, 0, '2020-12-31 23:59:59'),
(3, 1, 'MAX_USED', 'percentage', 10.00, 0.00, 10, 10, '2037-12-31 23:59:59'),
(4, 1, 'BELOW_MIN', 'percentage', 10.00, 1000.00, 100, 0, '2037-12-31 23:59:59');

SET FOREIGN_KEY_CHECKS = 1;
