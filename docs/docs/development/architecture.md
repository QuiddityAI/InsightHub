# Architecture Overview

## Document Ingestion
The document ingestion process is handled by [PDFerret](https://github.com/QuiddityAI/PDFerret), which is responsible for uploading and processing documents, including chunking. The chunked documents are stored in two different databases: OpenSearch for full-text storage and Qdrant for vector embeddings storage.

```mermaid
flowchart TD
    A[User] -->|Uploads Documents| B["PDFerret<br>(Document Ingestion)"]
    B --> C["Document Chunking"]
    C --> D1["OpenSearch<br>(Full Text Storage)"]
    C --> D2["Qdrant<br>(Vector Embeddings Storage)"]

```

## Search Process
The search process begins with the user selecting a search mode (by default, hybrid search is used).
Depending on the selected mode, the system fetches results from either OpenSearch or Qdrant. The results are then fused and reranked to provide the final output.

```mermaid
flowchart TD
    A[User] -->|Chooses Search Mode| SM["Search Mode Selection"]

    subgraph Search_Modes
        A1["Smart Search Mode"]
        A2["Vector Search Mode"]
        A3["Full Text Mode"]
    end

    SM --> A1
    SM --> A2
    SM --> A3

    A1 -->|Hybrid Search| E1["Fetch from OpenSearch"]
    A1 -->|Hybrid Search| E2["Fetch from Qdrant"]
    E1 --> F["Results Fusion"]
    E2 --> F

    A2 -->|Vector Search| E2a["Fetch from Qdrant"]
    A3 -->|Full Text Search| E1a["Fetch from OpenSearch"]

   F --> R1["Rerank"]
   E2a --> R2["Rerank"]
   E1a --> R3["Rerank"]

```

## Collections and columns

The results are displayed in a spreadsheet-like collection. The user (or the agent) can add columns to this collection. The system then finds relevant chunks using vector search and utilizes an LLM with the column settings to extract answers, filling the respective columns.

```mermaid
flowchart TD
    %% Entities (Modules)
    J["Spreadsheet-like Collection"]
    J1["New column"]
    M1["User or Agent"]
    M2["Vector Search"]
    M3["LLM"]

    %% Flow with actions as edge labels
    M1 -->|Add Columns| J
    J -->|Create new column| J1
    J1 -->|Fill| M2
    M2 -->|Find Relevant Chunks| M3
    M3 -->|Extract Answers| J1

```