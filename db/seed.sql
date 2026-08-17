USE multivendor_test;
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE store_pages;
TRUNCATE TABLE audit_logs;
TRUNCATE TABLE order_items;
TRUNCATE TABLE orders;
TRUNCATE TABLE master_orders;
TRUNCATE TABLE marketplace_cart_items;
TRUNCATE TABLE cart_items;
TRUNCATE TABLE carts;
TRUNCATE TABLE coupons;
TRUNCATE TABLE product_reviews;
TRUNCATE TABLE product_images;
TRUNCATE TABLE product_variants;
TRUNCATE TABLE products;
TRUNCATE TABLE categories;
TRUNCATE TABLE user_store_memberships;
TRUNCATE TABLE users;
TRUNCATE TABLE tenant_billing_logs;
TRUNCATE TABLE tenant_settings;
TRUNCATE TABLE tenants;
TRUNCATE TABLE subscription_plans;

INSERT INTO subscription_plans (id, code, name, price_monthly, max_products, max_storage_mb) VALUES
(1, 'free', 'Free Plan', 0.00, 50, 500),
(2, 'pro', 'Pro Plan', 29.99, 1000, 5000),
(3, 'enterprise', 'Enterprise Plan', 199.99, 999999, 50000);

INSERT INTO tenants (id, slug, name, plan_id, status, show_all_products_in_marketplace) VALUES
(1, 'tenant-a', 'Store A', 1, 'active', TRUE),
(2, 'tenant-b', 'Store B', 2, 'active', FALSE);

INSERT INTO users (id, email, password_hash, full_name, role) VALUES
(1, 'superadmin@platform.com', '$2b$12$pYA7SjOOz.QHHGZMMqGqUu6tH9/MiUsyzKD/./VR.1OJJ4yzf8ZNu', 'Platform Super Admin', 'super_admin'),
(2, 'admin.store1@platform.com', '$2b$12$pYA7SjOOz.QHHGZMMqGqUu6tH9/MiUsyzKD/./VR.1OJJ4yzf8ZNu', 'Store 1 Admin', 'user'),
(3, 'admin.store2@platform.com', '$2b$12$pYA7SjOOz.QHHGZMMqGqUu6tH9/MiUsyzKD/./VR.1OJJ4yzf8ZNu', 'Store 2 Admin', 'user'),
(4, 'customer@gmail.com', '$2b$12$pYA7SjOOz.QHHGZMMqGqUu6tH9/MiUsyzKD/./VR.1OJJ4yzf8ZNu', 'Global Customer', 'user');

INSERT INTO user_store_memberships (id, user_id, tenant_id, role) VALUES
(1, 2, 1, 'tenant_admin'),
(2, 3, 2, 'tenant_admin'),
(3, 4, 1, 'customer'),
(4, 4, 2, 'customer');

INSERT INTO products (id, tenant_id, name, slug, base_price, is_active, show_in_marketplace) VALUES
(1, 1, JSON_OBJECT('en', 'Product A1', 'he', 'מוצר א1'), 'product-a1', 10.00, 1, TRUE),
(2, 2, JSON_OBJECT('en', 'Product B1', 'he', 'מוצר ב1'), 'product-b1', 20.00, 1, TRUE),
(3, 2, JSON_OBJECT('en', 'Product B2 (store-only)', 'he', 'מוצר ב2'), 'product-b2', 15.00, 1, FALSE);

INSERT INTO orders (id, tenant_id, user_id, order_number, subtotal, total_amount, status) VALUES
(1, 1, 4, 'ORD-001', 100.00, 100.00, 'pending');

INSERT INTO product_reviews (id, tenant_id, product_id, user_id, rating, comment, is_approved) VALUES
(1, 1, 1, 4, 5, 'Great product', 0);

INSERT INTO product_variants (id, tenant_id, product_id, sku, stock_quantity) VALUES
(1, 1, 1, 'SKU-A1-1', 10),
(2, 2, 2, 'SKU-B1-1', 10),
(3, 2, 3, 'SKU-B2-1', 5);

INSERT INTO coupons (id, tenant_id, code, discount_type, discount_val, min_order_amt, usage_limit, used_count, valid_until) VALUES
(1, 1, 'VALID10', 'percentage', 10.00, 0.00, 100, 0, '2037-12-31 23:59:59'),
(2, 1, 'EXPIRED', 'percentage', 10.00, 0.00, 100, 0, '2020-12-31 23:59:59'),
(3, 1, 'MAX_USED', 'percentage', 10.00, 0.00, 10, 10, '2037-12-31 23:59:59'),
(4, 1, 'BELOW_MIN', 'percentage', 10.00, 1000.00, 100, 0, '2037-12-31 23:59:59');

INSERT INTO store_pages (id, tenant_id, page_key, page_type, title, sections) VALUES
(1, 1, 'home', 'static_page', 'Home Page', JSON_ARRAY(
    JSON_OBJECT('id', 'sec_hero_1', 'type', 'hero_banner', 'settings', JSON_OBJECT('headline', 'Summer Collection', 'size', 'medium', 'alignment', 'center')),
    JSON_OBJECT('id', 'sec_grid_1', 'type', 'product_grid', 'settings', JSON_OBJECT('title', 'Best Sellers', 'columns', 4, 'collection', 'best-sellers'))
)),
(2, 2, 'home', 'static_page', 'Home Page', JSON_ARRAY(
    JSON_OBJECT('id', 'sec_hero_1', 'type', 'hero_banner', 'settings', JSON_OBJECT('headline', 'Welcome to Store B', 'size', 'medium', 'alignment', 'center'))
));

SET FOREIGN_KEY_CHECKS = 1;
