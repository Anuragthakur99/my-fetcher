# Source Type Specific Flow Architectures

This document contains clean, focused architecture diagrams for each source type to make it easier to understand, review, optimize, and track individual flows.

## Common Entry Point

All source types start with the same entry flow:

```mermaid
graph TD
    A[Kafka Message<br/>channel_id, job_id] --> B[Job Manager<br/>Max 20 Parallel Jobs]
    B --> C[Initialize Job Context<br/>Logging, State, Config]
    C --> D[Channel Lookup API<br/>Get source_type, configs]
    D --> E{Source Type Router}
    
    E -->|s3| F[S3 Flow]
    E -->|ftp| G[FTP Flow]
    E -->|html| H[HTML Flow]
    E -->|api| I[API Flow]
```

---

## 1. S3 Source Type Flow

**Simple and Direct Flow for S3 Operations**

```mermaid
graph TD
    A[S3 Flow Entry] --> B[Load S3 Configuration]
    B --> C[API Call: Get S3 Credentials]
    C --> D[Generic S3 Fetcher]
    
    D --> E[Connect to S3 Bucket]
    E --> F[List/Download Files]
    F --> G{Download Success?}
    
    G -->|Yes| H[Process Files]
    G -->|No| I[Retry Logic]
    
    I --> J{Retry Count < Max?}
    J -->|Yes| E
    J -->|No| K[Mark Job Failed]
    
    H --> L[Upload Results to Output S3]
    L --> M[Update Job Status: Success]
    M --> N[Upload Logs to S3]
    N --> O[Job Cleanup]
    
    K --> P[Update Job Status: Failed]
    P --> N
```

**Key Components:**
- `fetchers/s3_fetcher/config.py` - S3 configuration management
- `fetchers/s3_fetcher/fetch.py` - Core S3 operations
- `common/s3_uploader.py` - Output upload functionality

---

## 2. FTP Source Type Flow

**Simple and Direct Flow for FTP Operations**

```mermaid
graph TD
    A[FTP Flow Entry] --> B[Load FTP Configuration]
    B --> C[API Call: Get FTP Credentials]
    C --> D[Generic FTP Fetcher]
    
    D --> E[Connect to FTP Server]
    E --> F[Navigate to Directory]
    F --> G[List/Download Files]
    G --> H{Download Success?}
    
    H -->|Yes| I[Process Files]
    H -->|No| J[Retry Logic]
    
    J --> K{Retry Count < Max?}
    K -->|Yes| E
    K -->|No| L[Mark Job Failed]
    
    I --> M[Upload Results to Output S3]
    M --> N[Update Job Status: Success]
    N --> O[Upload Logs to S3]
    O --> P[Job Cleanup]
    
    L --> Q[Update Job Status: Failed]
    Q --> O
```

**Key Components:**
- `fetchers/ftp_fetcher/config.py` - FTP configuration management
- `fetchers/ftp_fetcher/fetch.py` - Core FTP operations
- `common/s3_uploader.py` - Output upload functionality

---

## 3. HTML Source Type Flow

**Complex Flow with Custom Fetcher Management and LLM Integration**

```mermaid
graph TD
    A[HTML Flow Entry] --> B[Extract Base Domain<br/>structure_id]
    B --> C[API Call: Check Custom Fetcher Exists]
    C --> D{Custom Fetcher Found?}
    
    %% No Custom Fetcher Path
    D -->|No + create=true| E[Web Module: Browser AI Agent]
    E --> F[Explore Website<br/>Generate HAR + Screenshots]
    F --> G[API Module: Generate HTTP Code]
    G --> H{Config: Generate Playwright?}
    
    H -->|Yes| I[Generate Playwright Code]
    H -->|No| J[Use HTTP Code Only]
    
    I --> K[Push Custom Fetcher to Git]
    J --> L[Push Custom Fetcher to Git]
    K --> M[Update Config: is_playwright=true]
    L --> N[Execute HTTP Code]
    M --> O[Execute Playwright Code]
    
    %% Existing Custom Fetcher Path
    D -->|Yes + playwright=false| P[Load Custom HTTP Fetcher from Git]
    D -->|Yes + playwright=true| Q[Load Custom Playwright Fetcher from Git]
    
    P --> R[Execute Custom HTTP Code]
    Q --> S[Execute Custom Playwright Code]
    
    %% Execution Results
    N --> T{Execution Success?}
    O --> U{Execution Success?}
    R --> V{Execution Success?}
    S --> W{Execution Success?}
    
    %% Success Path
    T -->|Yes| X[Upload Results to S3]
    U -->|Yes| X
    V -->|Yes| X
    W -->|Yes| X
    
    %% Failure Path
    T -->|No| Y[Error Analysis]
    U -->|No| Y
    V -->|No| Y
    W -->|No| Y
    
    Y --> Z{Error Type?}
    Z -->|Transient| AA[Simple Retry]
    Z -->|Code Issue| BB[Complete Workflow Retry]
    
    AA --> CC{Retry Count < Max?}
    CC -->|Yes| T
    CC -->|No| DD[Mark Job Failed]
    
    BB --> EE{Workflow Retry < Max?}
    EE -->|Yes| FF[Validation Pipeline]
    EE -->|No| DD
    
    FF --> GG[Test Against Historical Data]
    GG --> HH{Validation Passed?}
    HH -->|Yes| E
    HH -->|No| DD
    
    %% Final Steps
    X --> II[Update Job Status: Success]
    DD --> JJ[Update Job Status: Failed]
    II --> KK[Upload Logs to S3]
    JJ --> KK
    KK --> LL[Job Cleanup]
```

**Key Components:**
- `fetchers/web_fetcher/` - Browser AI agent and Playwright execution
- `fetchers/api_fetcher/` - HTTP code generation from HAR
- `common/git_integration/` - Custom fetcher storage and retrieval
- `common/validation_pipeline/` - Historical data validation
- `common/structure_id_generator.py` - Base domain extraction

---

## 4. API Source Type Flow

**Flexible Flow for Generic and Custom API Operations**

```mermaid
graph TD
    A[API Flow Entry] --> B[Load API Configuration]
    B --> C[API Call: Get API Details & Credentials]
    C --> D{API Fetcher Type?}
    
    %% Generic API Path
    D -->|Generic| E[Generic API Fetcher]
    E --> F[Execute Generic API Calls]
    F --> G{Execution Success?}
    
    %% Existing Custom API Path
    D -->|Custom Existing| H[Load Custom API Fetcher from Git]
    H --> I[Execute Custom API Code]
    I --> J{Execution Success?}
    
    %% Create New Custom API Path
    D -->|Custom New| K[API Module: Generate Custom Code]
    K --> L[Push Custom API Fetcher to Git]
    L --> M[Execute Generated API Code]
    M --> N{Execution Success?}
    
    %% Success Paths
    G -->|Yes| O[Process API Response]
    J -->|Yes| O
    N -->|Yes| O
    
    %% Failure Paths
    G -->|No| P[Error Analysis]
    J -->|No| P
    N -->|No| P
    
    P --> Q{Error Type?}
    Q -->|Transient| R[Simple Retry]
    Q -->|Code Issue| S[Regenerate Custom Code]
    Q -->|Config Issue| T[Fix Configuration]
    
    R --> U{Retry Count < Max?}
    U -->|Yes| G
    U -->|No| V[Mark Job Failed]
    
    S --> W{Regenerate Count < Max?}
    W -->|Yes| K
    W -->|No| V
    
    T --> X[Update Configuration]
    X --> C
    
    %% Final Steps
    O --> Y[Upload Results to S3]
    Y --> Z[Update Job Status: Success]
    V --> AA[Update Job Status: Failed]
    Z --> BB[Upload Logs to S3]
    AA --> BB
    BB --> CC[Job Cleanup]
```

**Key Components:**
- `fetchers/api_fetcher/` - Generic and custom API operations
- `common/git_integration/` - Custom API fetcher storage
- `common/api_configuration_manager.py` - API type determination

---

## Flow Comparison Summary

| Source Type | Complexity | Custom Code | LLM Usage | Git Integration | Validation Pipeline |
|-------------|------------|-------------|-----------|-----------------|-------------------|
| **S3** | Low | No | No | No | No |
| **FTP** | Low | No | No | No | No |
| **HTML** | High | Yes | Yes | Yes | Yes |
| **API** | Medium | Optional | Optional | Optional | No |

## Common Error Handling Patterns

All flows use consistent error handling:

```mermaid
graph TD
    A[Error Occurs] --> B{Error Classification}
    B -->|Network/Timeout| C[Transient Error<br/>Simple Retry]
    B -->|Code Generation Failed| D[Code Issue<br/>Regenerate/Retry Workflow]
    B -->|Invalid Configuration| E[Config Issue<br/>Fix & Retry]
    B -->|Authentication Failed| F[Credential Issue<br/>Refresh & Retry]
    
    C --> G[Exponential Backoff Retry]
    D --> H[Complete Workflow Retry]
    E --> I[Configuration Update]
    F --> J[Credential Refresh]
```

## Next Steps

1. **Review each flow individually** for accuracy and completeness
2. **Optimize specific flows** based on requirements
3. **Add missing scenarios** to individual flows
4. **Define interfaces** between components
5. **Create implementation TODOs** for each source type

Each flow can now be developed, tested, and maintained independently while sharing common components and patterns.
