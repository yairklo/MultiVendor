# MultiVendor Hub — Final Technical Specification & Complete Database Schema (ERD)

מפרט בסיס נתונים (ERD) מלא וארכיטקטורת נתונים עבור פלטפורמת SaaS מרובת דיירים (Multi-Tenant) עם תמיכה בבידוד נתונים ברמת השורות (Row-Level Security), נעילות דינמיות ב-Redis, ניהול מנויים, וקפאת היסטוריית הזמנות.

---

## 1. ארכיטקטורה ועקרונות ליבה

1. **Multi-Tenant Data Isolation (Row-Level Security):**
   * כל טבלאות ה-Tenant במערכת כוללות שדה `tenant_id` מפורש.
   * כל שאילתת SQL/ORM מוגבלת ומסוננת ברמת ה-Middleware/Dependency:
     `WHERE tenant_id = :current_tenant_id`
2. **Identity & Scope Separation:**
   * `super_admin`: מנהל מערכת ראשי בעל `tenant_id = NULL`.
   * `tenant_admin` / `customer`: משתמשים המשויכים לדייר ספציפי (`tenant_id NOT NULL`).
   * ייחודיות חשבון משתמש נשמרת ברמת הדייר: `UNIQUE(tenant_id, email)`.
3. **Historical Data Integrity (Data Snapshot):**
   * פריטי הזמנות (`order_items`) שומרים עותק קפוא של שם המוצר, המק"ט (SKU) והמחיר בעת הרכישה, למניעת עיוות נתונים היסטורי בעת עדכון קטלוג.
4. **Concurrency & Race Condition Control (Redis):**
   * נעילות אטומיות (Distributed Locks) ב-Redis למניעת מכירת יתר (Overselling) ומרוץ בקשות בזמן ה-Checkout.

---

## 2. תרשים זרימה וישויות (Visual ERD Diagram)

```text
========================================================================================
                              1. TENANTS & SUBSCRIPTIONS LAYER
========================================================================================

+-----------------------------------+       +-----------------------------------+
|              TENANTS              |       |        SUBSCRIPTION_PLANS         |
+-----------------------------------+       +-----------------------------------+
| PK  id           : INT / BIGINT   |       | PK  id          : INT             |
| U   slug         : VARCHAR(100)   |       | U   code        : VARCHAR(50)     |
|     name         : VARCHAR(255)   |       |     name        : VARCHAR(100)    |
| FK  plan_id      : INT            |------>|     price_monthly: DECIMAL(10,2)   |
|     status       : ENUM(...)      |       |     max_products: INT             |
|     custom_domain: VARCHAR(255)   |       |     max_storage_mb: INT           |
|     created_at   : TIMESTAMP      |       |     features_json: JSON           |
|     updated_at   : TIMESTAMP      |       +-----------------------------------+
+-----------------------------------+
  |                  |
  | 1:1              | 1:N
  v                  v
+-----------------------+  +-----------------------------------+
|    TENANT_SETTINGS    |  |        TENANT_BILLING_LOGS        |
+-----------------------+  +-----------------------------------+
| PK  tenant_id  : INT  |  | PK  id           : BIGINT         |
|     logo_url   : TEXT |  | FK  tenant_id    : INT            |
|     primary_col: VARCHAR |  |     amount       : DECIMAL(10,2)   |
|     banner_url : TEXT |  |     currency     : VARCHAR(3)      |
|     currency   : VARCHAR |  |     status       : ENUM(...)       |
|     custom_css : TEXT |  |     invoice_url  : TEXT            |
|     support_email: VARCHAR|  |     created_at   : TIMESTAMP       |
+-----------------------+  +-----------------------------------+


========================================================================================
                              2. IDENTITY & SECURITY LAYER
========================================================================================

+-----------------------------------+       +-----------------------------------+
|               USERS               |       |            AUDIT_LOGS             |
+-----------------------------------+       +-----------------------------------+
| PK  id           : BIGINT         |       | PK  id           : BIGINT         |
| FK  tenant_id    : INT (NULLABLE) |       | FK  tenant_id    : INT (NULLABLE) |
| U   email        : VARCHAR(255)   |       | FK  user_id      : BIGINT (NULL)  |
|     password_hash: VARCHAR(255)   |       |     action       : VARCHAR(100)   |
|     full_name    : VARCHAR(255)   |       |     resource     : VARCHAR(100)   |
|     role         : ENUM(...)      |       |     ip_address   : VARCHAR(45)    |
|     is_active    : BOOLEAN        |       |     details_json : JSON           |
|     last_login_at: TIMESTAMP      |       |     created_at   : TIMESTAMP      |
|     created_at   : TIMESTAMP      |       +-----------------------------------+
+-----------------------------------+
  (UQ: tenant_id + email)


========================================================================================
                              3. CATALOG & INVENTORY LAYER
========================================================================================

+-----------------------------------+       +-----------------------------------+
|            CATEGORIES             |       |             PRODUCTS              |
+-----------------------------------+       +-----------------------------------+
| PK  id           : BIGINT         |       | PK  id           : BIGINT         |
| FK  tenant_id    : INT            |       | FK  tenant_id    : INT            |
| FK  parent_id    : BIGINT (NULL)  |-----> | FK  category_id  : BIGINT (NULL)  |
|     name         : VARCHAR(100)   |       |     name         : VARCHAR(255)   |
|     slug         : VARCHAR(100)   |       |     slug         : VARCHAR(255)   |
+-----------------------------------+       |     description  : TEXT           |
                                            |     base_price   : DECIMAL(10,2)   |
                                            |     is_active    : BOOLEAN        |
                                            |     created_at   : TIMESTAMP      |
                                            +-----------------------------------+
                                              |                |
                                              | 1:N            | 1:N
                                              v                v
+-----------------------------------+  +------------------+  +------------------+
|          PRODUCT_VARIANTS         |  |  PRODUCT_IMAGES  |  | PRODUCT_REVIEWS  |
+-----------------------------------+  +------------------+  +------------------+
| PK  id           : BIGINT         |  | PK id   : BIGINT |  | PK id   : BIGINT |
| FK  tenant_id    : INT            |  | FK ten_id: INT   |  | FK ten_id: INT   |
| FK  product_id   : BIGINT         |  | FK prod_id: BIGINT|  | FK prod_id:BIGINT|
|     sku          : VARCHAR(100)   |  |    image_url:TEXT|  | FK user_id:BIGINT|
|     attributes_json: JSON (Color) |  |    is_primary:BOOL|  |    rating: INT   |
|     price_override: DECIMAL(10,2) |  |    sort_order:INT|  |    comment: TEXT |
|     stock_quantity: INT           |  +------------------+  |    approved:BOOL |
+-----------------------------------+                        +------------------+


========================================================================================
                              4. CART, ORDERS & PROMOTIONS LAYER
========================================================================================

+-----------------------------------+       +-----------------------------------+
|              COUPONS              |       |               CARTS               |
+-----------------------------------+       +-----------------------------------+
| PK  id           : BIGINT         |       | PK  id           : VARCHAR(36) (UUID)
| FK  tenant_id    : INT            |       | FK  tenant_id    : INT            |
| U   code         : VARCHAR(50)    |       | FK  user_id      : BIGINT (NULL)  |
|     discount_type: ENUM(%, fixed) |       |     created_at   : TIMESTAMP      |
|     discount_val : DECIMAL(10,2)  |       |     updated_at   : TIMESTAMP      |
|     min_order_amt: DECIMAL(10,2)  |       +-----------------------------------+
|     usage_limit  : INT            |                         |
|     used_count   : INT            |                         | 1:N
|     valid_until  : TIMESTAMP      |                         v
+-----------------------------------+       +-----------------------------------+
                                            |            CART_ITEMS             |
                                            +-----------------------------------+
                                            | PK  id           : BIGINT         |
                                            | FK  tenant_id    : INT            |
                                            | FK  cart_id      : VARCHAR(36)    |
                                            | FK  variant_id   : BIGINT         |
                                            |     quantity     : INT            |
                                            +-----------------------------------+

+-----------------------------------+       +-----------------------------------+
|              ORDERS               |       |            ORDER_ITEMS            |
+-----------------------------------+       +-----------------------------------+
| PK  id           : BIGINT         |       | PK  id           : BIGINT         |
| FK  tenant_id    : INT            |       | FK  tenant_id    : INT            |
| FK  user_id      : BIGINT         |------>| FK  order_id     : BIGINT         |
| FK  coupon_id    : BIGINT (NULL)  |       | FK  variant_id   : BIGINT (NULL)  |
|     order_number : VARCHAR(50)    |       |     product_name : VARCHAR(255)   |
|     subtotal     : DECIMAL(10,2)  |       |     sku          : VARCHAR(100)   |
|     discount_amt : DECIMAL(10,2)  |       |     unit_price   : DECIMAL(10,2)   |
|     total_amount : DECIMAL(10,2)  |       |     quantity     : INT            |
|     status       : ENUM(...)      |       +-----------------------------------+
|     shipping_json: JSON           |
|     created_at   : TIMESTAMP      |
+-----------------------------------+