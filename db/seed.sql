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
TRUNCATE TABLE storefront_templates;

INSERT INTO subscription_plans (id, code, name, price_monthly, max_products, max_storage_mb) VALUES
(1, 'free', 'Free Plan', 0.00, 50, 500),
(2, 'pro', 'Pro Plan', 29.99, 1000, 5000),
(3, 'enterprise', 'Enterprise Plan', 199.99, 999999, 50000);

-- Same 3 built-in templates seeded by alembic/versions/0002_storefront_templates_table.py
-- (kept in sync by hand, same convention as db/schema.sql vs that migration's DDL) --
-- needed here too since auto_clear_db (tests/conftest.py) truncates every table and
-- reloads only from this file before each test.
INSERT INTO storefront_templates (template_key, name, tagline, swatch_json, pages_json, display_order) VALUES
('aurora', 'Aurora', 'Soft, minimal, boutique-ready.', '{"bg": "#faf8f5", "text": "#1f2937", "accent": "#6366f1"}', '{"home": {"title": "Home", "background_color": "#faf8f5", "text_color": "#1f2937", "sections": [{"type": "hero_banner", "settings": {"headline": "Timeless pieces, thoughtfully made", "size": "large", "alignment": "center", "background_color": "#f1ede7", "text_color": "#1f2937"}, "media": {"type": "image", "url": "https://picsum.photos/seed/aurora-hero/1600/900", "aspect_ratio": "16/9"}}, {"type": "feature_highlights", "settings": {"title": "Why shop with us", "items": [{"icon": "Truck", "title": "Free shipping", "text": "On every order, no minimum spend."}, {"icon": "ShieldCheck", "title": "Secure checkout", "text": "Your payment details always stay protected."}, {"icon": "RotateCcw", "title": "30-day returns", "text": "Not quite right? Send it back, no questions asked."}]}}, {"type": "product_grid", "settings": {"title": "New Arrivals", "columns": 4, "card_style": "minimal"}}, {"type": "two_column_layout", "settings": {"design_variant": "muted"}, "zones": {"left": [{"type": "text_block", "settings": {"heading": "Our story", "body": "We started with a simple idea: fewer, better things. Every piece in our collection is chosen for how it''s made, not just how it looks — small runs, honest materials, and a supply chain we can actually stand behind."}}], "right": [{"type": "gallery", "settings": {"layout": "grid", "images": ["https://picsum.photos/seed/aurora-gallery-1/800/800", "https://picsum.photos/seed/aurora-gallery-2/800/800"]}}]}}, {"type": "testimonials", "settings": {"title": "Loved by our customers", "items": [{"quote": "The quality is unreal for the price. My new go-to store.", "author": "Maya R.", "role": "Verified buyer"}, {"quote": "Fast shipping and the packaging alone felt premium.", "author": "Daniel K.", "role": "Verified buyer"}, {"quote": "Customer support actually helped me pick the right size.", "author": "Sarah L.", "role": "Verified buyer"}]}}, {"type": "button_group", "settings": {"buttons": [{"label": "Shop the collection", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}}, {"label": "Our story", "variant": "outline", "actionType": "NAVIGATE", "actionPayload": {"page_key": "about"}}]}}]}, "about": {"title": "About", "background_color": "#faf8f5", "text_color": "#1f2937", "sections": [{"type": "hero_banner", "settings": {"headline": "About us", "size": "small", "alignment": "center", "background_color": "#f1ede7"}}, {"type": "two_column_layout", "settings": {"design_variant": "neutral"}, "zones": {"left": [{"type": "text_block", "settings": {"heading": "How it started", "body": "We opened our doors because we couldn''t find what we wanted to buy ourselves — thoughtfully designed, well made, and priced fairly. Today every product is still picked (or made) by our small team, one collection at a time."}}], "right": [{"type": "gallery", "settings": {"layout": "grid", "images": ["https://picsum.photos/seed/aurora-about-1/800/800"]}}]}}, {"type": "feature_highlights", "settings": {"title": "What we care about", "items": [{"icon": "Leaf", "title": "Sustainability", "text": "Responsibly sourced materials wherever we can."}, {"icon": "Award", "title": "Craftsmanship", "text": "Small batches, checked by hand."}, {"icon": "Heart", "title": "Community", "text": "A portion of every sale supports local makers."}]}}, {"type": "button_group", "settings": {"buttons": [{"label": "Shop the collection", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}}]}}]}, "contact": {"title": "Contact", "background_color": "#faf8f5", "text_color": "#1f2937", "sections": [{"type": "hero_banner", "settings": {"headline": "Get in touch", "size": "small", "alignment": "center", "background_color": "#f1ede7"}}, {"type": "two_column_layout", "settings": {"design_variant": "neutral"}, "zones": {"left": [{"type": "text_block", "settings": {"heading": "We''d love to hear from you", "body": "Email hello@yourstore.com and we''ll get back to you within one business day."}}], "right": [{"type": "table", "settings": {"title": "Support hours", "headers": ["Day", "Hours"], "rows": [["Mon – Fri", "9:00 – 18:00"], ["Saturday", "10:00 – 16:00"], ["Sunday", "Closed"]]}}]}}]}}', 0),
('atelier', 'Atelier', 'Dark, editorial, high-fashion.', '{"bg": "#15130f", "text": "#f5f0e6", "accent": "#c9a24b"}', '{"home": {"title": "Home", "background_color": "#15130f", "text_color": "#f5f0e6", "sections": [{"type": "hero_banner", "settings": {"headline": "Crafted for those who notice the details", "size": "large", "alignment": "left", "background_color": "#1f1c16", "text_color": "#f5f0e6"}, "media": {"type": "image", "url": "https://picsum.photos/seed/atelier-hero/1600/900", "aspect_ratio": "16/9"}}, {"type": "product_grid", "settings": {"title": "Bestsellers", "columns": 3, "card_style": "framed"}}, {"type": "two_column_layout", "settings": {"design_variant": "secondary"}, "zones": {"left": [{"type": "gallery", "settings": {"layout": "carousel", "images": ["https://picsum.photos/seed/atelier-gallery-1/900/900", "https://picsum.photos/seed/atelier-gallery-2/900/900", "https://picsum.photos/seed/atelier-gallery-3/900/900"]}}], "right": [{"type": "text_block", "settings": {"heading": "The atelier", "body": "Every collection begins on a workbench, not a spreadsheet. We work in small runs with artisans we''ve partnered with for years, so every piece carries a little more weight than the price tag suggests.", "background_color": "#1f1c16", "text_color": "#f5f0e6"}}]}}, {"type": "feature_highlights", "settings": {"title": "The Atelier promise", "items": [{"icon": "Award", "title": "Limited runs", "text": "Small batches, never mass-produced."}, {"icon": "PackageCheck", "title": "Gift-ready packaging", "text": "Every order arrives ready to give."}, {"icon": "Headphones", "title": "Personal styling", "text": "Message us for one-to-one advice."}]}}, {"type": "testimonials", "settings": {"title": "In their words", "items": [{"quote": "Feels like a piece I''ll still be wearing in ten years.", "author": "Noa B.", "role": "Verified buyer"}, {"quote": "The packaging alone made it feel like an occasion.", "author": "Itay G.", "role": "Verified buyer"}]}}, {"type": "button_group", "settings": {"background_color": "#1f1c16", "buttons": [{"label": "Explore the collection", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}}]}}]}, "about": {"title": "About", "background_color": "#15130f", "text_color": "#f5f0e6", "sections": [{"type": "hero_banner", "settings": {"headline": "About the atelier", "size": "small", "alignment": "left", "background_color": "#1f1c16", "text_color": "#f5f0e6"}}, {"type": "text_block", "settings": {"heading": "A house built on craft", "body": "Founded by a small group of designers who wanted to slow things down, we work directly with artisan workshops instead of factories. It costs more and takes longer — we think that''s the point.", "background_color": "#1f1c16", "text_color": "#f5f0e6"}}, {"type": "gallery", "settings": {"layout": "grid", "images": ["https://picsum.photos/seed/atelier-about-1/800/800", "https://picsum.photos/seed/atelier-about-2/800/800"]}}, {"type": "button_group", "settings": {"background_color": "#1f1c16", "buttons": [{"label": "Explore the collection", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}}]}}]}, "contact": {"title": "Contact", "background_color": "#15130f", "text_color": "#f5f0e6", "sections": [{"type": "hero_banner", "settings": {"headline": "Contact the atelier", "size": "small", "alignment": "left", "background_color": "#1f1c16", "text_color": "#f5f0e6"}}, {"type": "two_column_layout", "settings": {"design_variant": "secondary"}, "zones": {"left": [{"type": "text_block", "settings": {"heading": "Reach us", "body": "hello@yourstore.com — private styling appointments available on request.", "background_color": "#1f1c16", "text_color": "#f5f0e6"}}], "right": [{"type": "table", "settings": {"title": "Studio hours", "headers": ["Day", "Hours"], "rows": [["Tue – Sat", "11:00 – 19:00"], ["Sun – Mon", "By appointment"]]}}]}}]}}', 1),
('nova', 'Nova', 'Bold, vivid, modern.', '{"bg": "#ffffff", "text": "#111827", "accent": "#f0653a"}', '{"home": {"title": "Home", "background_color": "#ffffff", "text_color": "#111827", "sections": [{"type": "hero_banner", "settings": {"headline": "Everyday gear, leveled up", "size": "large", "alignment": "center", "background_color": "#fff1ec", "text_color": "#111827"}, "media": {"type": "image", "url": "https://picsum.photos/seed/nova-hero/1600/900", "aspect_ratio": "16/9"}}, {"type": "feature_highlights", "settings": {"title": "Why you''ll love it here", "items": [{"icon": "Truck", "title": "Fast shipping", "text": "Most orders ship within 24 hours."}, {"icon": "CreditCard", "title": "Flexible payment", "text": "Pay in full or split it up."}, {"icon": "Sparkles", "title": "New drops weekly", "text": "Fresh product every single week."}]}}, {"type": "product_grid", "settings": {"title": "Trending now", "columns": 4, "card_style": "default"}}, {"type": "two_column_layout", "settings": {"design_variant": "accent"}, "zones": {"left": [{"type": "text_block", "settings": {"heading": "Built different", "body": "We obsess over the details other stores skip — real materials, real testing, real reviews."}}], "right": [{"type": "gallery", "settings": {"layout": "grid", "images": ["https://picsum.photos/seed/nova-gallery-1/800/800", "https://picsum.photos/seed/nova-gallery-2/800/800"]}}]}}, {"type": "testimonials", "settings": {"title": "What people say", "items": [{"quote": "Ordered on Monday, wearing it by Wednesday. Insane.", "author": "Tom H.", "role": "Verified buyer"}, {"quote": "Finally a store that doesn''t feel like every other store.", "author": "Priya S.", "role": "Verified buyer"}, {"quote": "The quality shocked me for this price point.", "author": "Alex M.", "role": "Verified buyer"}]}}, {"type": "button_group", "settings": {"buttons": [{"label": "Shop now", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}}, {"label": "About us", "variant": "outline", "actionType": "NAVIGATE", "actionPayload": {"page_key": "about"}}]}}]}, "about": {"title": "About", "background_color": "#ffffff", "text_color": "#111827", "sections": [{"type": "hero_banner", "settings": {"headline": "About us", "size": "small", "alignment": "center", "background_color": "#fff1ec"}}, {"type": "two_column_layout", "settings": {"design_variant": "muted"}, "zones": {"left": [{"type": "gallery", "settings": {"layout": "grid", "images": ["https://picsum.photos/seed/nova-about-1/800/800"]}}], "right": [{"type": "text_block", "settings": {"heading": "Why we exist", "body": "We got tired of choosing between good design and a fair price — so we built a store that doesn''t make you choose."}}]}}, {"type": "button_group", "settings": {"buttons": [{"label": "Shop now", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}}]}}]}, "contact": {"title": "Contact", "background_color": "#ffffff", "text_color": "#111827", "sections": [{"type": "hero_banner", "settings": {"headline": "Talk to us", "size": "small", "alignment": "center", "background_color": "#fff1ec"}}, {"type": "two_column_layout", "settings": {"design_variant": "muted"}, "zones": {"left": [{"type": "text_block", "settings": {"heading": "Say hello", "body": "hello@yourstore.com — we usually reply the same day."}}], "right": [{"type": "table", "settings": {"title": "Support hours", "headers": ["Day", "Hours"], "rows": [["Mon – Fri", "9:00 – 20:00"], ["Weekends", "10:00 – 15:00"]]}}]}}]}}', 2);

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

INSERT INTO categories (id, tenant_id, name, slug) VALUES
(1, 1, JSON_OBJECT('en', 'Coffee', 'he', 'קפה'), 'coffee'),
(2, 2, JSON_OBJECT('en', 'Tea', 'he', 'תה'), 'tea');

INSERT INTO products (id, tenant_id, category_id, name, slug, base_price, is_active, show_in_marketplace) VALUES
(1, 1, 1, JSON_OBJECT('en', 'Product A1', 'he', 'מוצר א1'), 'product-a1', 10.00, 1, TRUE),
(2, 2, 2, JSON_OBJECT('en', 'Product B1', 'he', 'מוצר ב1'), 'product-b1', 20.00, 1, TRUE),
(3, 2, 2, JSON_OBJECT('en', 'Product B2 (store-only)', 'he', 'מוצר ב2'), 'product-b2', 15.00, 1, FALSE);

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
