# Database Schema README

## Overview

This module provides a database abstraction layer that supports both:

1. **MongoDB** (Production)
2. **In-Memory Database** (Development/Testing fallback)

When MongoDB configuration is available, the application uses MongoDB collections. Otherwise, it automatically falls back to an in-memory datastore.

---

# Database Architecture

```text
Application
    │
    ▼
Database Adapter Layer
    │
    ├── MongoCollectionAdapter (Production)
    │
    └── InMemoryContainer (Development/Test)
```

Both implementations expose a common interface:

* `create_item()`
* `read_item()`
* `read_all_items()`
* `replace_item()`
* `delete_item()`
* `upsert_item()`
* `query_items()`

This allows the rest of the application to work independently of the underlying database.

---

# Collections

The system automatically creates and manages the following collections:

| Container Variable    | MongoDB Collection |
| --------------------- | ------------------ |
| checkpoints_container | checkpoints        |
| users_container       | USERS              |
| stores_container      | stores             |
| tags_container        | tags               |
| settings_container    | settings           |
| scan_container        | scan               |
| alerts_container      | alerts             |
| rounds_container      | rounds             |
| audit_logs_container  | audit_logs         |
| reports_container     | reports            |

---

# Collection Descriptions

## USERS

Stores application users and authentication-related information.

### Example Document

```json
{
  "_id": "uuid",
  "id": "uuid",
  "username": "john",
  "email": "john@example.com",
  "role": "admin",
  "created_at": "timestamp"
}
```

---

## checkpoints

Stores checkpoint information used during scanning, inspections, or workflow execution.

### Example Document

```json
{
  "_id": "uuid",
  "id": "uuid",
  "name": "Entrance Gate",
  "description": "Main Entry Checkpoint",
  "status": "active"
}
```

---

## stores

Stores store or facility information.

### Example Document

```json
{
  "_id": "uuid",
  "id": "uuid",
  "store_name": "Store A",
  "location": "Hyderabad",
  "manager": "John Doe"
}
```

---

## tags

Stores reusable tags for categorization.

### Example Document

```json
{
  "_id": "uuid",
  "id": "uuid",
  "tag_name": "High Priority",
  "color": "#FF0000"
}
```

---

## settings

Stores application-level configuration settings.

### Example Document

```json
{
  "_id": "uuid",
  "id": "uuid",
  "setting_key": "notifications_enabled",
  "value": true
}
```

---

## scan

Stores scan records generated during operations.

### Example Document

```json
{
  "_id": "uuid",
  "id": "uuid",
  "checkpoint_id": "uuid",
  "user_id": "uuid",
  "timestamp": "2025-01-01T10:00:00Z",
  "status": "completed"
}
```

---

## alerts

Stores generated alerts and notifications.

### Example Document

```json
{
  "_id": "uuid",
  "id": "uuid",
  "title": "Unauthorized Access",
  "severity": "high",
  "message": "Unexpected scan detected",
  "created_at": "timestamp"
}
```

---

## rounds

Stores inspection or patrol round information.

### Example Document

```json
{
  "_id": "uuid",
  "id": "uuid",
  "round_name": "Morning Patrol",
  "start_time": "timestamp",
  "end_time": "timestamp",
  "status": "completed"
}
```

---

## audit_logs

Stores audit trail events for tracking user and system actions.

### Example Document

```json
{
  "_id": "uuid",
  "id": "uuid",
  "action": "LOGIN",
  "performed_by": "user_id",
  "timestamp": "timestamp",
  "details": {}
}
```

---

## reports

Stores generated reports and report metadata.

### Example Document

```json
{
  "_id": "uuid",
  "id": "uuid",
  "report_name": "Monthly Summary",
  "generated_by": "user_id",
  "generated_at": "timestamp",
  "file_url": "https://example.com/report.pdf"
}
```

---

# Document Normalization

Before being stored, each document is automatically normalized.

```json
{
  "_id": "generated_uuid",
  "id": "generated_uuid"
}
```

If no identifier is provided, a UUID is automatically generated.

---

# Supported Operations

## Create

```python
container.create_item(document)
```

## Read

```python
container.read_item(item_id)
```

## Read All

```python
container.read_all_items()
```

## Update / Replace

```python
container.replace_item(item_id, document)
```

## Delete

```python
container.delete_item(item_id)
```

## Upsert

```python
container.upsert_item(document)
```

---

# Query Support

The adapter supports simple SQL-like filtering.

### Example

```python
query = """
SELECT * FROM c
WHERE c.user_id = @user_id
AND c.status = 'active'
"""

parameters = [
    {
        "name": "@user_id",
        "value": "123"
    }
]
```

### Supported Conditions

* Equality (`=`)
* Multiple conditions using `AND`
* String literals
* Numeric values
* Parameterized values (`@parameter`)

---

# Environment Configuration

Create a `.env` file:

```env
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGO_DATABASE=my_database
```

---

# Automatic Fallback

The application follows this startup flow:

```text
Start Application
        │
        ▼
Check MongoDB Configuration
        │
 ┌──────┴──────┐
 │             │
 ▼             ▼
Valid       Missing
Config      Config
 │             │
 ▼             ▼
MongoDB    In-Memory
Backend     Backend
```

This ensures the application can run locally even when MongoDB is unavailable.

---

# Available Containers

```python
checkpoints_container
users_container
stores_container
tags_container
settings_container
scan_container
alerts_container
rounds_container
audit_logs_container
reports_container
```

These containers are initialized during application startup and are available globally throughout the project.

---

# Features

* MongoDB Support
* In-Memory Fallback Database
* Automatic Collection Creation
* UUID-Based Document IDs
* CRUD Operations
* Upsert Support
* SQL-Like Query Filtering
* Environment-Based Configuration
* Consistent Adapter Interface Across Storage Backends

---

# Notes

* The database layer defines collections and storage behavior.
* Actual document structures depend on how the application writes data to each collection.
* Collection schemas shown in this document are examples and may be extended based on business requirements.
* Both MongoDB and in-memory implementations expose identical APIs, making them interchangeable.
