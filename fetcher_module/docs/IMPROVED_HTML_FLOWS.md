# Improved HTML Flow Architecture

This document contains the improved HTML flow broken down into simple, understandable diagrams based on channel flags (`is_new`, `fix_code`).

## HTML Flow Main Router

**Central routing logic for HTML source type based on channel configuration flags**

```mermaid
graph TD
    A[HTML Flow Entry] --> B[Extract Base Domain<br/>structure_id]
    B --> C[Load Channel Configuration]
    C --> D{Channel Flags?}
    
    D -->|is_new=True| E[New Channel Flow]
    D -->|is_new=False + fix_code=False| F[Existing Channel Flow]
    D -->|fix_code=True| G[Code Fix Flow]
    
    E --> H[See: New Channel Diagram]
    F --> I[See: Existing Channel Diagram]
    G --> J[See: Code Fix Diagram]
```

---

## 1. New Channel Flow (`is_new=True`)

**Flow for newly registered channels that need custom fetcher discovery and mapping**

```mermaid
graph TD
    A[New Channel Flow Entry<br/>is_new=True] --> B[API Call: Check Custom Fetcher Exists<br/>using structure_id]
    B --> C{Custom Fetcher Found?}
    
    %% Existing Fetcher Found Path
    C -->|Yes| D[Load Custom Fetcher from Git]
    D --> E[API Call: channel_fetcher_details<br/>Create Channel Mapping]
    E --> F[API Call: Update Channel<br/>Set is_new=False]
    F --> G{Fetcher Type?}
    
    G -->|playwright=true| H[Execute Playwright Code]
    G -->|playwright=false| I[Execute HTTP Code]
    
    H --> J{Execution Success?}
    I --> K{Execution Success?}
    
    J -->|Yes| L[Upload Results to S3]
    K -->|Yes| L
    
    J -->|No| M[Handle Execution Failure]
    K -->|No| M
    
    %% No Existing Fetcher Path
    C -->|No| N[Web Module: Browser AI Agent]
    N --> O[Explore Website<br/>Generate HAR + Screenshots]
    O --> P[API Module: Generate HTTP Code]
    P --> Q{Config: Generate Playwright?}
    
    Q -->|Yes| R[Generate Playwright Code]
    Q -->|No| S[Use HTTP Code Only]
    
    R --> T[Push Custom Fetcher to Git<br/>playwright=true]
    S --> U[Push Custom Fetcher to Git<br/>playwright=false]
    
    T --> V[API Call: channel_fetcher_details<br/>Create Channel Mapping]
    U --> W[API Call: channel_fetcher_details<br/>Create Channel Mapping]
    
    V --> X[API Call: Update Channel<br/>Set is_new=False]
    W --> Y[API Call: Update Channel<br/>Set is_new=False]
    
    X --> Z[Execute Playwright Code]
    Y --> AA[Execute HTTP Code]
    
    Z --> BB{Execution Success?}
    AA --> CC{Execution Success?}
    
    BB -->|Yes| L
    CC -->|Yes| L
    
    BB -->|No| M
    CC -->|No| M
    
    %% Final Steps
    L --> DD[Update Job Status: Success]
    M --> EE[Update Job Status: Failed]
    DD --> FF[Upload Logs to S3]
    EE --> FF
    FF --> GG[Job Cleanup]
```

**Key Operations:**
- Custom fetcher discovery using `structure_id`
- Channel-to-fetcher mapping creation
- Channel flag updates (`is_new=False`)
- New fetcher generation if needed

---

## 2. Existing Channel Flow (`is_new=False`, `fix_code=False`)

**Simple execution flow for existing channels with established fetcher mappings**

```mermaid
graph TD
    A[Existing Channel Flow Entry<br/>is_new=False, fix_code=False] --> B[API Call: channel_fetcher_details<br/>Get Channel Mapping]
    B --> C[Load Specific Custom Fetcher from Git<br/>using mapping details]
    C --> D{Fetcher Type?}
    
    D -->|playwright=true| E[Execute Playwright Code]
    D -->|playwright=false| F[Execute HTTP Code]
    
    E --> G{Execution Success?}
    F --> H{Execution Success?}
    
    G -->|Yes| I[Upload Results to S3]
    H -->|Yes| I
    
    G -->|No| J[Error Analysis]
    H -->|No| J
    
    J --> K{Error Type?}
    K -->|Transient| L[Simple Retry]
    K -->|Website Changed| M[Call fetcher_correction_api<br/>Set fix_code=True]
    K -->|Code Issue| N[Call fetcher_correction_api<br/>Set fix_code=True]
    
    L --> O{Retry Count < Max?}
    O -->|Yes| E
    O -->|No| P[Mark Job Failed]
    
    M --> Q[Call fetcher_correction_api<br/>Trigger Code Fix Flow]
    N --> Q
    
    %% Final Steps
    I --> R[Update Job Status: Success]
    P --> S[Update Job Status: Failed]
    Q --> T[Update Job Status: Failed<br/>Job Handed to Code Fix Flow]
    
    R --> U[Upload Logs to S3]
    S --> U
    T --> U
    U --> V[Job Cleanup]
```

**Key Operations:**
- Direct fetcher loading using channel mapping
- Execution with targeted error handling
- Automatic escalation to code fix mode when needed

---

## 3. Code Fix Flow (`fix_code=True`)

**Complete fetcher regeneration flow triggered when existing fetchers fail due to website changes**

```mermaid
graph TD
    A[Code Fix Flow Entry<br/>fix_code=True] --> B[Extract Base Domain<br/>structure_id]
    B --> C[Web Module: Browser AI Agent<br/>Complete Re-exploration]
    C --> D[Explore Website<br/>Generate New HAR + Screenshots]
    D --> E[API Module: Generate New HTTP Code<br/>Complete Regeneration]
    E --> F{Config: Generate Playwright?}
    
    F -->|Yes| G[Generate New Playwright Code]
    F -->|No| H[Use New HTTP Code Only]
    
    G --> I[Create New Custom Fetcher Version<br/>playwright=true]
    H --> J[Create New Custom Fetcher Version<br/>playwright=false]
    
    I --> K[Validation Pipeline<br/>Test Against Historical Data]
    J --> K
    
    K --> L[Test New Fetcher Against<br/>All Existing Channels for this structure_id]
    L --> M{Validation Passed?}
    
    M -->|Yes| N[Push New Version to Git]
    M -->|No| O{Retry Count < Max?}
    
    O -->|Yes| C
    O -->|No| P[Mark All Related Jobs Failed]
    
    N --> Q[API Call: channel_fetcher_details<br/>Update ALL Channel Mappings<br/>for this structure_id]
    Q --> R[Execute New Fetcher Code]
    R --> S{Execution Success?}
    
    S -->|Yes| T[Upload Results to S3]
    S -->|No| U[Error Analysis]
    
    U --> V{Critical Failure?}
    V -->|Yes| P
    V -->|No| W[Simple Retry with New Code]
    
    W --> X{Retry Count < Max?}
    X -->|Yes| R
    X -->|No| P
    
    %% Final Steps
    T --> Y[Update Job Status: Success]
    P --> Z[Update Job Status: Failed]
    Y --> AA[Upload Logs to S3]
    Z --> AA
    AA --> BB[Job Cleanup]
```

**Key Operations:**
- Complete fetcher regeneration from scratch
- Validation against historical data for ALL channels
- Bulk update of channel mappings
- Comprehensive testing before deployment

---

## API Flow Integration Points

**Simplified API flow connections with HTML flow**

```mermaid
graph TD
    A[API Flow Scenarios] --> B{When API Flow Triggered?}
    
    B -->|source_type=api| C[Generic API Fetcher<br/>Simple Execution]
    B -->|HTML + playwright=false<br/>+ is_new=False| D[Custom API Fetcher<br/>from Channel Mapping]
    B -->|HTML Code Generation<br/>from HAR file| E[API Module<br/>Generate HTTP Code]
    
    C --> F[Standard API Operations]
    D --> G[Execute Custom API Code]
    E --> H[Return Generated Code<br/>to HTML Flow]
    
    F --> I[Upload Results]
    G --> I
    H --> J[Continue HTML Flow]
```

**API Flow Characteristics:**
- **Simple**: No complex branching like HTML flow
- **Generic Focus**: Primarily uses generic API fetcher
- **HTML Integration**: Generates HTTP code for HTML flow when needed

---

## Flow Decision Matrix

| Scenario | is_new | fix_code | Flow Type | Key Operations |
|----------|--------|----------|-----------|----------------|
| **New Channel Registration** | True | False | New Channel Flow | Fetcher discovery, mapping creation |
| **Regular Execution** | False | False | Existing Channel Flow | Direct execution using mapping |
| **Website Changed** | False | True | Code Fix Flow | Complete regeneration, validation |
| **API Source** | N/A | N/A | API Flow | Generic API operations |

## Configuration Examples

### New Channel Config
```yaml
channel_id: "12345"
source_type: "html"
is_new: true
fix_code: false
url: "https://example.com/data"
```

### Existing Channel Config
```yaml
channel_id: "12345"
source_type: "html"
is_new: false
fix_code: false
fetcher_mapping_id: "example_com_v2"
```

### Code Fix Config
```yaml
channel_id: "12345"
source_type: "html"
is_new: false
fix_code: true
structure_id: "example.com"
reason: "website_structure_changed"
```

## Benefits of This Structure

1. **Clear Separation**: Each scenario has its own focused diagram
2. **Easy Understanding**: No complex branching in single diagram
3. **Targeted Development**: Teams can work on specific scenarios
4. **Better Testing**: Each flow can be tested independently
5. **Maintenance**: Easy to modify individual flows without affecting others

## Next Steps

1. **Review each flow diagram** for accuracy and completeness
2. **Validate API integration points** with HTML flows
3. **Define detailed interfaces** between components
4. **Create implementation TODOs** for each flow type
5. **Merge approved diagrams** into main SOURCE_TYPE_FLOWS.md file
