# Database Design Review

This document reviews the schema design for the Authentication & Identity Management Module. The tables are structured to ensure high performance, security, strict referential integrity, audit compliance, and compatibility with both SQLite (development) and PostgreSQL (production).

---

## 1. Table Definitions & Schemas

All tables utilize UUID primary keys, automatic creation/update timestamps, and soft delete fields.

### 1.1 `users`
Represents the system users (Forest Officers, Emergency Responders, Research Analysts, Administrators).
* **`id`**: `UUID` (Primary Key)
* **`email`**: `VARCHAR(255)` (Unique, Indexed)
* **`username`**: `VARCHAR(50)` (Unique, Indexed)
* **`hashed_password`**: `VARCHAR(255)` (Not Null)
* **`profile_image_url`**: `VARCHAR(512)` (Nullable)
* **`is_active`**: `BOOLEAN` (Default: True)
* **`is_verified`**: `BOOLEAN` (Default: False)
* **`last_login_at`**: `TIMESTAMP` (Nullable)
* **`failed_login_attempts`**: `INTEGER` (Default: 0)
* **`locked_until`**: `TIMESTAMP` (Nullable)
* **`created_at`**: `TIMESTAMP` (Default: NOW)
* **`updated_at`**: `TIMESTAMP` (Default: NOW, updated on edit)
* **`deleted_at`**: `TIMESTAMP` (Nullable, for soft delete support)

### 1.2 `roles`
Defines system roles.
* **`id`**: `UUID` (Primary Key)
* **`name`**: `VARCHAR(50)` (Unique, Not Null) - e.g., `Super Admin`, `Forest Officer`, `Emergency Response Officer`, `Research Analyst`, `Viewer`
* **`description`**: `VARCHAR(255)` (Nullable)
* **`created_at`**: `TIMESTAMP` (Default: NOW)
* **`updated_at`**: `TIMESTAMP` (Default: NOW)

### 1.3 `permissions`
Finer-grained access controls.
* **`id`**: `UUID` (Primary Key)
* **`name`**: `VARCHAR(100)` (Unique, Not Null) - e.g., `manage_users`, `upload_images`, `view_predictions`, `access_audit_logs`
* **`description`**: `VARCHAR(255)` (Nullable)
* **`created_at`**: `TIMESTAMP` (Default: NOW)
* **`updated_at`**: `TIMESTAMP` (Default: NOW)

### 1.4 `role_permissions` (Association Table)
Maps permissions to roles.
* **`role_id`**: `UUID` (Foreign Key -> `roles.id`, Cascade Delete)
* **`permission_id`**: `UUID` (Foreign Key -> `permissions.id`, Cascade Delete)
* *Constraint*: Primary Key on `(role_id, permission_id)`

### 1.5 `user_roles` (Association Table)
Maps roles to users. Supports future multi-role capabilities.
* **`user_id`**: `UUID` (Foreign Key -> `users.id`, Cascade Delete)
* **`role_id`**: `UUID` (Foreign Key -> `roles.id`, Cascade Delete)
* *Constraint*: Primary Key on `(user_id, role_id)`

### 1.6 `refresh_tokens`
Stores refresh tokens for token rotation (RTR) and revocation.
* **`id`**: `UUID` (Primary Key)
* **`user_id`**: `UUID` (Foreign Key -> `users.id`, Cascade Delete)
* **`token_hash`**: `VARCHAR(255)` (Unique, Indexed)
* **`parent_token_hash`**: `VARCHAR(255)` (Nullable, Indexed) - Tracks rotation chain
* **`expires_at`**: `TIMESTAMP` (Not Null)
* **`is_revoked`**: `BOOLEAN` (Default: False)
* **`created_at`**: `TIMESTAMP` (Default: NOW)

### 1.7 `sessions`
Active user login sessions.
* **`id`**: `UUID` (Primary Key)
* **`user_id`**: `UUID` (Foreign Key -> `users.id`, Cascade Delete)
* **`refresh_token_id`**: `UUID` (Foreign Key -> `refresh_tokens.id`, Nullable, Cascade Delete)
* **`ip_address`**: `VARCHAR(45)` (IPv4/IPv6 support)
* **`user_agent`**: `VARCHAR(512)` (Nullable)
* **`device_type`**: `VARCHAR(50)` (e.g. Mobile, Desktop, Tablet)
* **`is_active`**: `BOOLEAN` (Default: True)
* **`last_activity_at`**: `TIMESTAMP` (Default: NOW)
* **`created_at`**: `TIMESTAMP` (Default: NOW)
* **`expires_at`**: `TIMESTAMP` (Not Null)

### 1.8 `audit_logs`
Records security and sensitive business modifications.
* **`id`**: `UUID` (Primary Key)
* **`user_id`**: `UUID` (Nullable, Foreign Key -> `users.id`, Set Null on delete)
* **`action`**: `VARCHAR(100)` (Not Null, e.g. `user.login`, `user.register`, `role.create`)
* **`ip_address`**: `VARCHAR(45)` (Nullable)
* **`user_agent`**: `VARCHAR(512)` (Nullable)
* **`resource_type`**: `VARCHAR(100)` (e.g., `user`, `role`, `image`)
* **`resource_id`**: `VARCHAR(100)` (Nullable)
* **`details`**: `JSON` (Nullable)
* **`created_at`**: `TIMESTAMP` (Default: NOW)

---

## 2. Index Optimization

To maintain sub-millisecond query execution speeds under load, the following indices are defined:
1. **`users(email)`** & **`users(username)`**: For extremely fast user lookup during login.
2. **`refresh_tokens(token_hash)`**: For fast RTR checks on token exchange.
3. **`sessions(user_id, is_active)`**: For quick extraction of a user's active devices and remote session termination.
4. **`audit_logs(user_id, action)`**: For security reporting, incident response, and login pattern investigations.

---

## 3. Migration & Compatibility Considerations

* **UUID Compatibility**: Since we support SQLite for testing and PostgreSQL for production:
  * For SQLAlchemy, we will use a custom UUID mapping class that stores UUIDs as a `CHAR(36)` string in SQLite and as a native `UUID` type in PostgreSQL.
* **Foreign Key Constraints**: Constraints are explicitly declared. In SQLite, foreign key enforcement is turned on via event listeners upon DB connection.
* **Soft Deletes**: Standard queries will filter out records where `deleted_at IS NOT NULL` by utilizing repository wrapper helper functions or SQLAlchemy global query options.
