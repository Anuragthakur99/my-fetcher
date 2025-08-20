# Microservice Architecture - Fetcher Service Flows

## Overview
A microservice-based data fetching system that polls Kafka for tasks, processes different source types, and outputs results to S3 and downstream Kafka topics. The service maintains its own database (`amazoniax_fetcher_db`) for independent scaling and fetcher management.

## High-Level System Architecture

```mermaid
graph TD
    A[Kafka Topic<br/>amazoniax_fetcher_tasks] --> B[Worker Pod<br/>Kafka Consumer]
    B --> C[Message Handler<br/>Parse & Route]
    C --> D{Source Type Router}
    
    D -->|s3| E[S3 Flow]
    D -->|ftp| F[FTP Flow]
    D -->|html/api| G[Web/API Flow Controller]
    
    E --> H[File Processing & Upload]
    F --> H
    G --> H
    
    H --> I[Hash Comparison<br/>amazoniax_fetcher_db]
    I --> J[S3 Upload<br/>New/Updated Files Only]
    J --> K[Kafka Producers]
    
    K --> L[amazoniax_parsers Topic<br/>S3 Parent Folder Path]
    K --> M[amazoniax_status Topic<br/>Job Status Updates]
    
    G --> N[amazoniax_fetcher_db<br/>Fetcher Management]
    N --> O[Git Fetchers Repo<br/>Custom Code Storage]
```

---

## Kafka Message Schemas

### Input Topic: `amazoniax_fetcher`
```json
{
  "job_id": "job_12345",
  "channel_id": "001",
  "source_type": "html|api|s3|ftp",
  "is_new": true,
  "heal_mode": false,
  "config": {
    // Source-specific configuration (see below)
  }
}
```

### Output Topic: `amazoniax_parsers`
```json
{
  "job_id": "job_12345",
  "channel_id": "001",
  "s3_output_path": "s3://bucket/path/to/job_12345/",
  "file_count": 15,
  "timestamp": "2025-08-12T08:30:00Z"
}
```

### Status Topic: `amazoniax_status`
```json
{
  "job_id": "job_12345",
  "channel_id": "ch_001",
  "status": "success|failed|requires_human_review",
  "message": "Job completed successfully",
  "timestamp": "2025-08-12T08:30:00Z",
  "metadata": {
    "files_processed": 15,
    "execution_time_seconds": 120
  }
}
```

---

## Source Type Configuration Schemas

### S3 Configuration
```json
{
  "bucket": "source-bucket",
  "remote_path": "/data/files/",
  "access_key": "AKIA...",
  "secret_access_key": "secret...",
  "file_pattern": "*.csv",
  "other_optional_fields": ""
}
```

### FTP Configuration
```json
{
  "host": "ftp.example.com",
  "username": "user",
  "password": "pass",
  "remote_path": "/data/files/",
  "file_pattern": "*.xml",
  "other_optional_fields": ""
}
```

### HTML/API Configuration
```json
{
  "url": "https://example.com/data",
  "channel_name": "Example Channel",
  "login_credentials": {
    "username": "user",
    "password": "pass"
  },
  "navigation_details": {
    "date_range": "7_days",
    "filters": ["sports", "news"]
  },
  "api_documentation_path": "",
  "auth_keys": {
    "api_key": "key123",
    "bearer_token": "token456"
  }
  ,
  "other_optional_fields": ""
}
```

---

## Flow 1: S3 Source Type

**Simple and direct flow for S3 operations**

```mermaid
graph TD
    A[S3 Message Received] --> B[Parse S3 Configuration]
    B --> C[Connect to Source S3 Bucket]
    C --> D[List & Download Files<br/>Based on Pattern]
    D --> E{Download Success?}
    
    E -->|Yes| F[File Processing<br/>Hash Calculation]
    E -->|No| G[Retry Logic<br/>Configurable Count]
    
    G --> H{Retry Count < Max?}
    H -->|Yes| C
    H -->|No| I[Mark Job Failed]
    
    F --> J[Hash Comparison<br/>amazoniax_fetcher_db]
    J --> K[Upload New/Updated Files to S3]
    K --> L[Store File Metadata<br/>amazoniax_fetcher_db]
    L --> M[Send to Parsers Topic]
    M --> N[Send Status Update]
    
    I --> O[Send Failed Status]
```

---

## Flow 2: FTP Source Type

**Simple and direct flow for FTP operations**

```mermaid
graph TD
    A[FTP Message Received] --> B[Parse FTP Configuration]
    B --> C[Connect to FTP Server]
    C --> D[Navigate to Remote Path]
    D --> E[List & Download Files<br/>Based on Pattern]
    E --> F{Download Success?}
    
    F -->|Yes| G[File Processing<br/>Hash Calculation]
    F -->|No| H[Retry Logic<br/>Configurable Count]
    
    H --> I{Retry Count < Max?}
    I -->|Yes| C
    I -->|No| J[Mark Job Failed]
    
    G --> K[Hash Comparison<br/>amazoniax_fetcher_db]
    K --> L[Upload New/Updated Files to S3]
    L --> M[Store File Metadata<br/>amazoniax_fetcher_db]
    M --> N[Send to Parsers Topic]
    N --> O[Send Status Update]
    
    J --> P[Send Failed Status]
```

---

## Flow 3: Web/API Source Type - Main Controller

**Unified flow for HTML and API sources with intelligent routing**

```mermaid
graph TD
    A[Web/API Message Received] --> B[Parse Configuration<br/>Extract Base Domain]
    B --> C{Flow Type Determination}
    
    C -->|is_new=True| D[New Channel Flow]
    C -->|is_new=False + heal_mode=False| E[Existing Channel Flow]
    C -->|heal_mode=True| F[Heal Mode Flow]
    
    D --> G[See: New Channel Diagram]
    E --> H[See: Existing Channel Diagram]
    F --> I[See: Heal Mode Diagram]
```

---

## Flow 3A: New Channel Flow (`is_new=True`)

**Discovery and initial setup for new channels**

```mermaid
graph TD
    A[New Channel Flow Entry] --> B[Extract Base Domain<br/>structure_id = domain.com]
    B --> C[Git Sync at Startup<br/>Load All Custom Fetchers]
    C --> D[Query amazoniax_fetcher_db<br/>Check Existing Fetcher]
    D --> E{Custom Fetcher Found?}
    
    E -->|Yes| F[Load Existing Fetcher Code<br/>from Git Repository]
    E -->|No| G[Generate New Custom Fetcher]
    
    F --> H[Execute Existing Fetcher]
    G --> I[Web Module: Browser AI Agent<br/>Generate HAR + Screenshots]
    I --> J[API Module: Generate HTTP Code<br/>from HAR File]
    J --> K[Push New Fetcher to Git<br/>fetcher_name = domain_fetcher_v1]
    K --> L[Store in amazoniax_fetcher_db<br/>fetcher_details table]
    L --> M[Create Channel Mapping<br/>channel_fetcher_details table]
    M --> N[Execute New Fetcher]
    
    H --> O{Execution Success?}
    N --> O
    
    O -->|Yes| P[File Processing & Upload]
    O -->|No| Q[Mark Job Failed<br/>Requires Investigation]
    
    P --> R[Send to Parsers Topic]
    R --> S[Send Success Status]
    Q --> T[Send Failed Status]
```

---

## Flow 3B: Existing Channel Flow (`is_new=False`)

**Standard execution for established channels**

```mermaid
graph TD
    A[Existing Channel Flow Entry] --> B[Query amazoniax_fetcher_db<br/>Get Channel Mapping]
    B --> C[Load Specific Fetcher Code<br/>from Git Repository]
    C --> D[Execute Custom Fetcher]
    D --> E{Execution Success?}
    
    E -->|Yes| F[File Processing & Upload]
    E -->|No| G[Error Analysis]
    
    G --> H{Error Type?}
    H -->|Temporary/Network| I[Simple Retry<br/>Configurable Count]
    H -->|Website Changed| J[Trigger Heal Mode<br/>Set heal_mode=True]
    H -->|Code Issue| J
    
    I --> K{Retry Count < Max?}
    K -->|Yes| D
    K -->|No| L[Mark Job Failed]
    
    J --> M[Mark Job Failed<br/>Will Retry with heal_mode=True]
    
    F --> N[Send to Parsers Topic]
    N --> O[Send Success Status]
    L --> P[Send Failed Status]
    M --> P
```

---

## Flow 3C: Heal Mode Flow (`heal_mode=True`)

**Complete fetcher regeneration with validation**

```mermaid
graph TD
    A[Heal Mode Flow Entry] --> B[Extract Base Domain<br/>structure_id]
    B --> C[Query amazoniax_fetcher_db<br/>Get Current Fetcher Details]
    C --> D[Check Channel Mappings<br/>How Many Channels Use This Fetcher?]
    D --> E[Generate New Custom Fetcher<br/>Web + API Modules]
    E --> F[Create New Version<br/>domain_fetcher_v2, v3, etc.]
    F --> G[Validation Pipeline<br/>Test Against All Mapped Channels]
    
    G --> H{Validation Success?}
    H -->|Yes| I[Push New Version to Git]
    H -->|No| J{Retry Count < Max?}
    
    J -->|Yes| E
    J -->|No| K[Mark Job Failed<br/>Requires Human Review]
    
    I --> L[Update amazoniax_fetcher_db<br/>fetcher_details table]
    L --> M[Update All Channel Mappings<br/>channel_fetcher_details table]
    M --> N[Execute New Fetcher Version]
    N --> O{Execution Success?}
    
    O -->|Yes| P[File Processing & Upload]
    O -->|No| Q[Mark Job Failed<br/>Critical Issue]
    
    P --> R[Send to Parsers Topic]
    R --> S[Send Success Status]
    Q --> T[Send Failed Status]
    K --> T
```

---

## File Processing & Deduplication Flow

**Common flow for all source types after successful data retrieval**

```mermaid
graph TD
    A[Files Retrieved Successfully] --> B[Calculate Content Hash<br/>for Each File]
    B --> C[Query amazoniax_fetcher_db<br/>Compare with Historical Hashes]
    C --> D{Hash Comparison}
    
    D -->|New File| E[Mark for Upload & Processing]
    D -->|Updated File| E
    D -->|Duplicate File| F[Skip File]
    
    E --> G[Upload to S3<br/>Organized by job_id]
    F --> H[Continue to Next File]
    G --> I[Store File Metadata<br/>amazoniax_fetcher_db]
    
    I --> J{More Files?}
    H --> J
    J -->|Yes| B
    J -->|No| K[Send S3 Parent Folder Path<br/>to Parsers Topic]
    
    K --> L[Update Job Status<br/>Success with Metadata]
```

---

## Database Tables (High-Level)

### `fetcher_details`
- `id`, `structure_id` (domain.com), `fetcher_name`, `version`, `created_at`

### `channel_fetcher_details`
- `id`, `channel_id`, `fetcher_id` (FK), `config_json`, `created_at`

### `job_runs`
- `id`, `job_id`, `channel_id`, `status`, `metadata_json`, `created_at`

### `file_metadata`
- `id`, `job_id`, `file_path`, `content_hash`, `file_size`, `created_at`

---

## Key Design Decisions

### 1. **Unified Web/API Flow**
- Both HTML and API sources follow the same discovery and execution pattern
- Web Module generates HAR files, API Module converts to HTTP code
- Single fetcher management system for both types

### 2. **Independent Database**
- `amazoniax_fetcher_db` provides complete independence from upstream services
- Enables independent scaling and deployment
- Stores all fetcher metadata and job history

### 3. **Git-Based Code Storage**
- Custom fetchers stored in separate Git repository
- Versioning strategy: `domain_fetcher_v1`, `domain_fetcher_v2`
- Sync at startup ensures latest code availability

### 4. **Intelligent Deduplication**
- Content-based hashing prevents duplicate processing
- Historical comparison across all job runs
- Only new/updated files sent to parsers

### 5. **Validation Pipeline**
- Triggered only during heal_mode for safety
- Tests new fetchers against all mapped channels
- Prevents deployment of faulty code

## Configuration Management

### Retry Configuration (Database Stored)
```json
{
  "max_simple_retries": 3,
  "max_heal_retries": 2,
  "retry_delay_seconds": 30
}
```

### Git Configuration
```json
{
  "fetchers_repo_path": "/fetchers",
  "sync_on_startup": true,
  "auto_commit": true
}
```

## Error Handling Summary

| Error Type | Action | Next Step |
|------------|--------|-----------|
| **Network/Temporary** | Simple Retry | Configurable retry count |
| **Website Changed** | Trigger Heal Mode | New job with heal_mode=True |
| **Code Generation Failed** | Retry Generation | Max retries → Human Review |
| **Validation Failed** | Retry Generation | Max retries → Human Review |
| **Critical Execution Error** | Immediate Failure | Human Review Required |

## Benefits of This Architecture

1. **Simplicity**: Clear separation of concerns with focused flows
2. **Scalability**: Independent microservice with own database
3. **Reliability**: Comprehensive validation and retry mechanisms
4. **Maintainability**: Unified Web/API flow reduces complexity
5. **Efficiency**: Smart deduplication prevents unnecessary processing
6. **Flexibility**: Configurable retry and validation parameters
