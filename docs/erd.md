# MultiVendor Hub — Database Schema Reference (ERD)

מפרט בסיס נתונים (ERD) עבור פלטפורמת SaaS מרובת דיירים (Multi-Tenant) עם בידוד נתונים ברמת השורות, נעילות דינמיות ב-Redis, ניהול מנויים, שוק צולב-חנויות (marketplace), ו-CMS מבוסס AI.

תרשים זה משקף את הסכימה בפועל כפי שהיא מוגדרת ב-`server/app/models/*.py` (לא ספק חיצוני / מסמך עיצוב נפרד) — כדי לוודא שהוא לא מתיישן, השווה מול המודלים בכל שינוי סכימה משמעותי.

---

## 1. ארכיטקטורה ועקרונות ליבה

1. **Multi-Tenant Data Isolation (Row-Level Security):**
   * כל טבלאות ה-Tenant במערכת כוללות שדה `tenant_id` מפורש (`TenantScoped` mixin).
   * כל שאילתת SQL/ORM מוגבלת ומסוננת ברמת ה-Middleware/Dependency: `WHERE tenant_id = :current_tenant_id`.
   * נבדק ישירות ב-`tests/test_tenant_isolation_rls.py` (IDOR, הזרקת JWT חוצה-דיירים, בידוד נתיבי אדמין).
2. **Identity & Scope Separation:**
   * `User` הוא זהות **גלובלית** (email ייחודי בכל המערכת), עם `role` גלובלי של `super_admin` או `user` בלבד.
   * התפקיד בפועל בכל חנות (`tenant_admin` / `customer`) חי על `UserStoreMembership` — זהות אחת יכולה להיות `tenant_admin` בחנות אחת ו-`customer` בחנות אחרת בו-זמנית.
   * ייחודיות חברות בחנות: `UNIQUE(user_id, tenant_id)`.
3. **Historical Data Integrity (Data Snapshot):**
   * `order_items` שומרים עותק קפוא של שם המוצר, המק"ט (SKU) והמחיר בעת הרכישה, למניעת עיוות נתונים היסטורי בעת עדכון קטלוג.
4. **Concurrency & Race Condition Control (Redis):**
   * נעילות אטומיות (Distributed Locks) ב-Redis למניעת מכירת יתר (Overselling) ומרוץ בקשות בזמן ה-Checkout — `lock:tenant:{id}:variant:{id}`, ננעלות בסדר ממוין כשיש כמה פריטים (bundles) כדי למנוע deadlock.
5. **i18n:**
   * שדות תוכן שהלקוח רואה (`Product.name`, `Product.description`, `Category.name`, `StorePage.title`/`sections`) מאוחסנים כ-JSON `{locale: text}` ולא כ-`VARCHAR` בודד.
6. **Marketplace checkout:**
   * עגלה שחוצה כמה דיירים לא נשמרת כ-`Cart` רגיל (ש-`tenant_id` שלו NOT NULL) אלא כ-`MarketplaceCartItem`, ובצ'קאאוט מתפצלת ל-`MasterOrder` + כמה `Order` בני-דייר תחתיו, עם פיצול עמלה/תשלום לספק.

---

## 2. Tenants, Subscriptions & Storefront Config

```text
+-----------------------------------+       +-----------------------------------+
|         SUBSCRIPTION_PLANS        |       |              TENANTS              |
+-----------------------------------+       +-----------------------------------+
| PK  id             : INT          |       | PK  id             : INT          |
| U   code           : VARCHAR(50)  |<------| FK  plan_id        : INT          |
|     name           : VARCHAR(100) |       | U   slug           : VARCHAR(100) |
|     price_monthly  : DECIMAL(10,2)|       |     name           : VARCHAR(255) |
|     max_products   : INT          |       |     status         : ENUM(active,suspended,cancelled)
|     max_storage_mb : INT          |       | U   custom_domain  : VARCHAR(255) NULL
|     features_json  : JSON         |       |     show_all_products_in_marketplace: BOOLEAN
|     created_at     : TIMESTAMP    |       |     stripe_account_id: VARCHAR(255) NULL
+-----------------------------------+       |     created_at / updated_at       |
                                             +-----------------------------------+
                                               |                          |
                                               | 1:1                      | 1:N
                                               v                          v
                                  +-----------------------------+  +---------------------------+
                                  |        TENANT_SETTINGS       |  |  USER_STORE_MEMBERSHIPS   |
                                  +-----------------------------+  |     (see section 3)       |
                                  | PK  tenant_id      : INT     |  +---------------------------+
                                  |     logo_url       : TEXT    |
                                  |     primary_color  : VARCHAR |
                                  |     banner_url     : TEXT    |
                                  |     currency       : CHAR(3) |
                                  |     custom_css     : TEXT    |
                                  |     support_email  : VARCHAR |
                                  |     supported_languages: JSON|
                                  |     default_language: VARCHAR|
                                  |     review_moderation_enabled: BOOLEAN
                                  |     allow_unverified_reviews: BOOLEAN
                                  |     template_key / draft_template_key: VARCHAR NULL
                                  |     nav_items      : JSON NULL
                                  +-----------------------------+

+-----------------------------------+
|        STOREFRONT_TEMPLATES       |   global reference catalog (not tenant-scoped) —
+-----------------------------------+   the 3 built-in premium templates a seller can apply
| PK  id             : INT          |   (stamps TenantSettings.template_key on apply)
| U   template_key   : VARCHAR(50)  |
|     name / tagline : VARCHAR      |
|     swatch_json    : JSON         |
|     pages_json     : JSON         |
|     display_order  : INT          |
|     is_active      : BOOLEAN      |
+-----------------------------------+
```

---

## 3. Identity & Security

```text
+-----------------------------------+       +-----------------------------------+
|               USERS                |       |       USER_STORE_MEMBERSHIPS       |
+-----------------------------------+       +-----------------------------------+
| PK  id             : BIGINT       |       | PK  id             : BIGINT       |
| U   email          : VARCHAR(255) |<------| FK  user_id        : BIGINT       |
|     password_hash  : VARCHAR(255) |       | FK  tenant_id      : INT          |
|     full_name      : VARCHAR(255) |       |     role           : ENUM(tenant_admin, customer)
|     role           : ENUM(super_admin, user)  |    is_active       : BOOLEAN      |
|     is_active      : BOOLEAN      |       |     created_at     : TIMESTAMP    |
|     last_login_at  : TIMESTAMP    |       +-----------------------------------+
|     created_at     : TIMESTAMP    |         UNIQUE(user_id, tenant_id)
+-----------------------------------+

+-----------------------------------+
|             AUDIT_LOGS             |
+-----------------------------------+
| PK  id             : BIGINT       |
| FK  tenant_id       : INT NULL    |
| FK  user_id         : BIGINT NULL |
|     action          : VARCHAR(100)|
|     resource        : VARCHAR(100)|
|     ip_address      : VARCHAR(45) |
|     details_json    : JSON        |
|     created_at      : TIMESTAMP   |
+-----------------------------------+
```

`role` הגלובלי על `User` מבחין רק בין `super_admin` (מנהל פלטפורמה) לכל שאר המשתמשים; ההרשאה בפועל בכל חנות ספציפית נגזרת מ-`UserStoreMembership.role`.

---

## 4. Catalog & Inventory

```text
+-----------------------------------+       +-----------------------------------+
|            CATEGORIES              |       |              PRODUCTS              |
+-----------------------------------+       +-----------------------------------+
| PK  id              : BIGINT       |       | PK  id                : BIGINT     |
| FK  tenant_id        : INT         |       | FK  tenant_id          : INT       |
| FK  parent_id        : BIGINT NULL |<------| FK  category_id        : BIGINT NULL
|     name             : JSON (i18n) |       |     name               : JSON (i18n)
|     slug             : VARCHAR(100)|       |     slug               : VARCHAR(255)
+-----------------------------------+       |     description        : JSON (i18n) NULL
                                             |     base_price         : DECIMAL(10,2)
                                             |     is_active          : BOOLEAN
                                             |     show_in_marketplace: BOOLEAN
                                             |     product_type       : ENUM(physical, digital, service)
                                             |     digital_file_url   : VARCHAR(512) NULL
                                             |     download_limit     : INT NULL
                                             |     is_bundle          : BOOLEAN
                                             |     created_at         : TIMESTAMP
                                             +-----------------------------------+
                                               |          |             |
                                               | 1:N       | 1:N         | 1:N
                                               v           v             v
+-----------------------------------+  +------------------+  +------------------+
|          PRODUCT_VARIANTS          |  |  PRODUCT_IMAGES  |  | PRODUCT_REVIEWS  |
+-----------------------------------+  +------------------+  +------------------+
| PK  id              : BIGINT       |  | PK id  : BIGINT  |  | PK id  : BIGINT  |
| FK  tenant_id        : INT         |  | FK tenant_id: INT|  | FK tenant_id: INT|
| FK  product_id       : BIGINT      |  | FK product_id: BIGINT| FK product_id: BIGINT
|     sku              : VARCHAR(100)|  |    image_url: TEXT| FK user_id: BIGINT
|     attributes_json  : JSON NULL   |  |    is_primary: BOOLEAN| rating (1-5): INT
|     price_override   : DECIMAL NULL|  |    sort_order: INT|    comment: TEXT NULL
|     stock_quantity   : INT         |  +------------------+  |    is_approved: BOOLEAN
+-----------------------------------+                        |    is_verified_buyer: BOOLEAN
                                                               |    created_at: TIMESTAMP
                                                               +------------------+

+-----------------------------------+
|        PRODUCT_BUNDLE_ITEMS        |   not tenant-scoped directly (inherits via bundle_product_id)
+-----------------------------------+   links a bundle Product to the ProductVariants it's made of
| PK  id                : BIGINT     |
| FK  bundle_product_id  : BIGINT    |
| FK  component_variant_id: BIGINT   |
|     quantity           : INT       |
+-----------------------------------+
```

מוצר דיגיטלי (`product_type='digital'`) לא מוגבל ע"י `stock_quantity` של הוריאנט שלו (ראה `catalog.py::tracks_inventory`) ולא דורש כתובת משלוח בצ'קאאוט.

---

## 5. Cart, Orders & Promotions

```text
+-----------------------------------+       +-----------------------------------+
|              COUPONS               |       |               CARTS                |
+-----------------------------------+       +-----------------------------------+
| PK  id              : BIGINT       |       | PK  id (UUID)      : VARCHAR(36)  |
| FK  tenant_id        : INT         |       | FK  tenant_id       : INT         |
|     code             : VARCHAR(50) |       | FK  user_id         : BIGINT NULL |
|     discount_type    : ENUM(percentage, fixed)|  created_at / updated_at        |
|     discount_val     : DECIMAL(10,2)|      +-----------------------------------+
|     min_order_amt    : DECIMAL(10,2)|                        |
|     usage_limit / used_count: INT  |                        | 1:N
|     valid_until      : TIMESTAMP   |                        v
|     is_active        : BOOLEAN     |       +-----------------------------------+
+-----------------------------------+       |             CART_ITEMS             |
                                             +-----------------------------------+
                                             | PK  id              : BIGINT       |
                                             | FK  tenant_id        : INT         |
                                             | FK  cart_id          : VARCHAR(36) |
                                             | FK  variant_id       : BIGINT      |
                                             |     quantity         : INT         |
                                             +-----------------------------------+

+-----------------------------------+   cross-tenant cart used only for marketplace checkout —
|       MARKETPLACE_CART_ITEMS       |   cart_id here is a client UUID grouping key, NOT a FK
+-----------------------------------+   into CARTS (which is single-tenant, tenant_id NOT NULL)
| PK  id              : BIGINT       |
|     cart_id          : VARCHAR(36) |
| FK  tenant_id        : INT         |
| FK  variant_id       : BIGINT      |
|     quantity         : INT         |
|     created_at       : TIMESTAMP   |
+-----------------------------------+

+-----------------------------------+       +-----------------------------------+
|            MASTER_ORDERS           |       |               ORDERS               |
+-----------------------------------+       +-----------------------------------+
| PK  id              : BIGINT       |       | PK  id                  : BIGINT   |
| FK  user_id          : BIGINT      |<------| FK  master_order_id      : BIGINT NULL (set only for marketplace sub-orders)
| U   master_order_number: VARCHAR(50)|      | FK  tenant_id            : INT     |
|     total_amount     : DECIMAL(10,2)|      | FK  user_id              : BIGINT  |
| U   payment_intent_id: VARCHAR(255) NULL|  | FK  coupon_id            : BIGINT NULL
|     created_at       : TIMESTAMP   |       | FK  shipping_method_id   : BIGINT NULL
+-----------------------------------+       |     order_number         : VARCHAR(50)
  groups the per-tenant sub-orders            |     subtotal / discount_amt / shipping_fee / total_amount: DECIMAL(10,2)
  produced by one marketplace checkout;        |     platform_commission / vendor_net_payout: DECIMAL(10,2)
  a master order has no single tenant_id       |     status  : ENUM(pending, pending_payment, processing, shipped, completed, cancelled, expired)
                                                |     order_type: ENUM(physical, digital)
                                                |     shipping_json: JSON NULL
                                                | U   payment_intent_id   : VARCHAR(255) NULL
                                                |     tracking_number / shipping_label_url: VARCHAR NULL
                                                |     shipping_provider   : ENUM(hfd, lionwheel) NULL
                                                |     shipped_at / created_at: TIMESTAMP
                                                +-----------------------------------+
                                                  |
                                                  | 1:N
                                                  v
                                                +-----------------------------------+
                                                |            ORDER_ITEMS             |
                                                +-----------------------------------+
                                                | PK  id           : BIGINT          |
                                                | FK  tenant_id     : INT            |
                                                | FK  order_id      : BIGINT         |
                                                | FK  variant_id    : BIGINT NULL    |
                                                |     product_name  : VARCHAR(255)   |  (frozen snapshot at purchase time)
                                                |     sku           : VARCHAR(100)   |  (frozen snapshot at purchase time)
                                                |     unit_price    : DECIMAL(10,2)  |  (frozen snapshot at purchase time)
                                                |     quantity      : INT            |
                                                +-----------------------------------+
```

---

## 6. Shipping

```text
+-----------------------------------+       +-----------------------------------+
|          SHIPPING_METHODS          |       |       TENANT_SHIPPING_CONFIGS      |
+-----------------------------------+       +-----------------------------------+
| PK  id              : BIGINT       |       | PK  id                 : BIGINT    |
| FK  tenant_id        : INT         |       | FK  tenant_id           : INT      |
|     name             : VARCHAR(100)|       |     provider            : ENUM(hfd, lionwheel)
|     price            : DECIMAL(10,2)|      |     credentials_encrypted: TEXT (Fernet-encrypted)
|     free_shipping_threshold: DECIMAL NULL| |     sender_name/phone/city/street/house_number: VARCHAR
|     is_active        : BOOLEAN     |       |     is_active / is_default / auto_fulfill: BOOLEAN
+-----------------------------------+       |     created_at / updated_at         |
  seller-defined flat rates shown at         +-----------------------------------+
  checkout                                    UNIQUE(tenant_id, provider) — one row per courier a
                                               vendor has connected; auto_fulfill dispatches an order
                                               to this courier the instant it's marked paid
```

---

## 7. Storefront CMS & AI Copilot

```text
+-----------------------------------+       +-----------------------------------+
|             STORE_PAGES            |       |        STORE_PAGE_VERSIONS         |
+-----------------------------------+       +-----------------------------------+
| PK  id              : BIGINT       |       | PK  id                : BIGINT     |
| FK  tenant_id        : INT         |<------| FK  store_page_id      : BIGINT    |
|     page_key         : VARCHAR(100)|       | FK  tenant_id          : INT       |
|     page_type        : ENUM(static_page, template)| page_key / page_type (snapshot)
|     title            : VARCHAR(255)|       |     title / sections   : (snapshot)|
|     sections         : JSON        |       |     background_color / text_color  |
|     background_color / text_color: VARCHAR NULL|  created_at        : TIMESTAMP  |
|     published_*      : (same fields, snapshot published by the seller;   +-----------------------------------+
|                          the public storefront only ever reads these)      version history — one row per publish,
|     published_at     : TIMESTAMP NULL                                       for rollback
|     created_at / updated_at        |
+-----------------------------------+
  UNIQUE(tenant_id, page_key, page_type)
  draft fields (sections/title/colors) are what the AI copilot and admin
  preview read/write; published_* only changes on explicit publish

+-----------------------------------+       +-----------------------------------+
|           AI_CONVERSATIONS         |       |         AI_PENDING_ACTIONS         |
+-----------------------------------+       +-----------------------------------+
| PK  id              : BIGINT       |       | PK  id (UUID)       : VARCHAR(36)  |
| FK  tenant_id        : INT         |       | FK  tenant_id        : INT         |
|     page_key / page_type: NULL together = tenant-wide global copilot thread |
|     gemini_history   : JSON NULL (serialized google.genai Content[])|  tool_name    : VARCHAR(100) |
|     messages         : JSON (display transcript)|  tool_args    : JSON         |
|     updated_at       : TIMESTAMP   |       |     summary          : VARCHAR(255)|
+-----------------------------------+       |     created_at / expires_at        |
  UNIQUE(tenant_id, page_key, page_type)    +-----------------------------------+
                                               a destructive AI-proposed action (delete
                                               product, cancel order) that only executes
                                               once a human confirms via a UI button —
                                               one-time use, deleted on confirm/cancel
```

---

## 8. Related documents

- Feature overview, how to run locally, deployment: [../README.md](../README.md)
- Point-in-time QA audit (test coverage, bugs found/fixed): [QA_AUDIT_REPORT.md](QA_AUDIT_REPORT.md)
- Migration history: `server/alembic/versions/`
