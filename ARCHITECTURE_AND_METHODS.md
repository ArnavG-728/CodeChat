# CodeChat v2.0 - Architecture & Methods Documentation

Complete reference guide for all files, classes, and methods in the CodeChat system.

---

## 📋 Table of Contents

1. [Backend Architecture](#backend-architecture)
2. [Frontend Architecture](#frontend-architecture)
3. [Database Schema](#database-schema)
4. [API Reference](#api-reference)
5. [Data Flow](#data-flow)

---

## Backend Architecture

### Core Files

#### `main.py` - Application Entry Point
**Purpose**: Initializes and starts the FastAPI server

**Key Functions**:
- `if __name__ == "__main__"`: Starts Uvicorn server on port 8000

**Dependencies**: FastAPI, Uvicorn, api_enhanced

---

#### `api.py` - REST API & WebSocket Server
**Purpose**: Handles all HTTP endpoints and WebSocket connections

**Classes**:
- `RepositoryAdd(BaseModel)`: Request model for adding repositories
- `QueryRequest(BaseModel)`: Request model for queries
  - `query: str` - User query
  - `top_k: int` - Number of results (default: 5)
  - `repository: str` - Selected repository (optional)
- `QueryResponse(BaseModel)`: Response model for queries
  - `answer: str` - AI-generated answer
  - `sources: List[dict]` - Source citations
- `RepositoryStatus(BaseModel)`: Repository processing status
- `HealthStatus(BaseModel)`: System health status
- `ConnectionManager`: WebSocket connection management

**Key Methods**:
- `comprehensive_health_check()` - GET `/api/health`
  - Checks Neo4j, Gemini API, GitHub token, embeddings model
  - Returns component status and overall system health
  
- `list_repositories()` - GET `/api/repositories`
  - Returns all repositories with stats (files, classes, functions)
  
- `add_repository(repo: RepositoryAdd)` - POST `/api/repositories`
  - Validates repository format
  - Adds to processing queue
  - Returns status
  
- `delete_repository(repo_name: str)` - DELETE `/api/repositories/{repo_name}`
  - Removes repository and all child nodes from Neo4j
  
- `get_repository_status(repo_name: str)` - GET `/api/repositories/{repo_name}/status`
  - Returns current processing status
  
- `get_repository_stats(repo_name: str)` - GET `/api/repositories/{repo_name}/stats`
  - Returns node counts and language distribution
  
- `query_codebase(request: QueryRequest)` - POST `/api/query`
  - Multi-strategy retrieval with repository filtering
  - Processes query with QueryProcessor
  - Returns answer with source citations
  
- `process_repository_task(repo_url, branch, repo_name)` - Background task
  - Orchestrates entire processing pipeline
  - Broadcasts progress via WebSocket
  - Steps: Clone → Parse → Ingest → Embeddings → Summaries → Index
  
- `websocket_endpoint(websocket)` - WS `/ws`
  - Handles real-time status updates
  - Broadcasts repository processing progress

**Status Codes**:
- 200: Success
- 400: Invalid request
- 404: Not found
- 500: Server error

---

#### `retrieval.py` - Multi-Strategy Retrieval System
**Purpose**: Implements 4-strategy code retrieval with repository filtering

**Constants**:
- `SUMMARY_INDEXES`: Vector indexes for summaries
- `CODE_INDEXES`: Vector indexes for code
- `db_name`: Neo4j database name
- `embedding_model`: Google Generative AI embeddings

**Key Functions**:

1. **`retrieve_semantic_results(query, top_k, use_code_index, repository)`**
   - Embeds query using Google embeddings
   - Searches vector indexes
   - Filters by repository if specified
   - Returns sorted results by relevance score

2. **`retrieve_graph_based_results(query, top_k, repository)`**
   - Extracts keywords from query
   - Matches against node names and summaries
   - Calculates relevance scores
   - Filters by repository

3. **`retrieve_related_nodes(node_name, node_type, depth, repository)`**
   - Finds child nodes (direct relationships)
   - Finds parent nodes (reverse relationships)
   - Filters by repository
   - Returns related nodes with scores

4. **`retrieve_top_k(query, top_k, use_multi_strategy, repository)`**
   - **Strategy 1**: Semantic search (100% weight)
   - **Strategy 2**: Graph-based search (60% weight)
   - **Strategy 3**: Code embedding search (40% weight)
   - **Strategy 4**: Related node enrichment (70-80% weight)
   - Deduplicates and combines scores
   - Returns top-k results

**Cypher Queries**:
- Vector search with repository filter
- Keyword matching with repository constraint
- Relationship traversal (CHILD relationships)

---

#### `query_processor.py` - Query Analysis & Prompt Engineering
**Purpose**: Analyzes queries and generates context-aware prompts

**Classes**:

1. **`QueryAnalyzer`**
   - **Methods**:
     - `_detect_query_type()`: Classifies query (overview, functionality, architecture, etc.)
     - `_extract_keywords()`: Extracts important terms
     - `_detect_multi_part()`: Detects compound queries
   
   - **Query Types**:
     - `overview`: "What is", "Explain", "Describe"
     - `functionality`: "How does", "Purpose", "What does"
     - `architecture`: "Structure", "Design", "Components"
     - `implementation`: "How to", "Example", "Usage"
     - `relationships`: "Related", "Connects", "Calls"
     - `comparison`: "Difference", "Compare", "vs"
     - `debugging`: "Bug", "Error", "Issue", "Fix"

2. **`ContextBuilder`**
   - **Methods**:
     - `_organize_nodes()`: Groups nodes by type
     - `build_context_string()`: Formats context for LLM
     - `_format_node()`: Formats individual node info
     - `get_summary_stats()`: Returns retrieval statistics
   
   - **Output**: Organized context with file/class/function nodes

3. **`PromptEngineer`**
   - **Methods**:
     - `generate_system_prompt()`: Creates query-type-specific system prompt
     - `generate_user_message()`: Formats user query with context
   
   - **Prompt Types**: Customized for each query type

4. **`QueryProcessor`**
   - **Methods**:
     - `process_query()`: Main orchestrator
       - Analyzes query
       - Builds context
       - Generates prompt
       - Invokes LLM
       - Returns answer with metadata

---

#### `ingest_structure.py` - Neo4j Data Ingestion
**Purpose**: Ingests parsed code structure into Neo4j graph database

**Classes**:
- `StructureIngester`: Handles Neo4j ingestion

**Key Methods**:
- `__init__(repo_name)`: Initializes ingester and creates repository node
- `ingest(structure)`: Main ingestion method
  - Creates file node with repository as parent
  - Recursively creates child nodes (classes, functions)
  - Connects all nodes via CHILD relationships
  - Validates repository structure
  
- `recursive_create(node_data, parent_node_obj, depth, is_file_node)`:
  - Creates individual nodes
  - Connects to parent
  - Processes children
  - Prevents orphaned nodes
  
- `validate_repository_structure()`: Validates all nodes are connected

**Node Types Created**:
- `RepositoryNode`: Root repository
- `FileNode`: Source files
- `ClassNode`: Classes/types
- `FunctionNode`: Functions/methods

**Relationships**: CHILD (parent → child)

---

#### `extract_structure.py` - OOP Language Parsing
**Purpose**: Parses Python code using AST to extract structure

**Classes**:
- `StructuredExtractor(ast.NodeVisitor)`: AST visitor for code extraction

**Key Methods**:
- `extract()`: Main extraction method
  - Parses source code
  - Visits AST nodes
  - Returns structured data
  
- `visit_Module(node)`: Processes module-level items
- `visit_ClassDef(node)`: Extracts class definitions
  - Captures class name, line number, code
  - Recursively processes methods
  
- `visit_FunctionDef(node)`: Extracts function definitions
- `visit_AsyncFunctionDef(node)`: Extracts async functions
- `_visit_function(node, is_async)`: Common function processing
  - Captures parameters
  - Extracts function code
  - Processes nested functions
  
- `visit_Call(node)`: Extracts function calls
- `generic_visit(node)`: Default visitor (returns None)

**Output Structure**:
```python
{
  "file": "filename.py",
  "code": "full source code",
  "children": [
    {
      "type": "class|function|async_function|call",
      "name": "entity_name",
      "lineno": 42,
      "code": "code snippet",
      "parameters": ["param1", "param2"],
      "parent": "parent_name",
      "children": [...]
    }
  ]
}
```

---

#### `extract_procedural.py` - Procedural Language Parsing
**Purpose**: Parses procedural languages (C, Go, Rust) using regex

**Classes**:
- `ProceduralExtractor`: Regex-based code extraction

**Key Methods**:
- `extract()`: Main extraction method
  - Uses regex patterns for language
  - Extracts functions and structures
  - Returns structured data
  
- `_extract_c_functions()`: C/C++ function extraction
- `_extract_go_functions()`: Go function extraction
- `_extract_rust_functions()`: Rust function extraction

**Supported Languages**:
- C, C++, Go, Rust, and others

---

#### `code_embeddings.py` - Code Vector Embeddings
**Purpose**: Generates 768-dimensional embeddings using UniXcoder

**Key Functions**:
- `generate_embeddings(code_snippets)`: Main embedding function
  - Tokenizes code
  - Passes through UniXcoder model
  - Returns 768-dim vectors
  
- `batch_embed()`: Batch processing for efficiency

**Model**: UniXcoder (768 dimensions)
**Framework**: Hugging Face Transformers

---

#### `generate_summary.py` - AI Summary Generation
**Purpose**: Generates summaries using Google Gemini API

**Key Functions**:
- `generate_summary(code, node_type)`: Main summary function
  - Sends code to Gemini API
  - Generates concise summary
  - Returns summary text
  
- `batch_generate_summaries()`: Batch processing

**Model**: Google Gemini 2.5 Flash
**Temperature**: 0.3 (deterministic)

---

#### `create_vector_indexes.py` - Neo4j Vector Indexes
**Purpose**: Creates vector indexes for semantic search

**Key Functions**:
- `create_vector_indexes(dimension)`: Creates indexes
  - `fileSummaryEmbeddingIndex`: File summaries
  - `classSummaryEmbeddingIndex`: Class summaries
  - `functionSummaryEmbeddingIndex`: Function summaries
  - `fileCodeEmbeddingIndex`: File code
  - `classCodeEmbeddingIndex`: Class code
  - `functionCodeEmbeddingIndex`: Function code

**Dimension**: 768 (UniXcoder)

---

#### `create_schema.py` - Neo4j Schema Definition
**Purpose**: Defines Neo4j node types and relationships

**Classes**:

1. **`BaseNodeMixin`**: Shared properties
   - `name`: Node name (indexed)
   - `lineno`: Line number
   - `code`: Source code
   - `parameters`: Function parameters
   - `code_embedding`: Code vector (768-dim)
   - `summary`: AI summary
   - `summary_embedding`: Summary vector (768-dim)
   - `parent_source_identifier`: Parent reference
   - `children_source_identifiers`: Child references
   - **Relationships**: `parent` (from), `children` (to)

2. **`FileNode(StructuredNode, BaseNodeMixin)`**
   - Represents source files
   - `type`: "file"

3. **`ClassNode(StructuredNode, BaseNodeMixin)`**
   - Represents classes/types
   - `type`: "class"

4. **`FunctionNode(StructuredNode, BaseNodeMixin)`**
   - Represents functions/methods
   - `type`: "function"

5. **`RepositoryNode(StructuredNode)`**
   - Represents code repositories
   - `name`: Repository name (unique)
   - `type`: "Code repository"
   - **Relationships**: `children` (to nodes)

**Relationships**:
- `CHILD`: Parent → Child relationship
- `PARENT`: Child → Parent relationship (reverse)

---

#### `language_detector.py` - Language Detection
**Purpose**: Detects programming language from file extension

**Key Functions**:
- `detect_language(file_path)`: Returns language name
- `get_parser(language)`: Returns appropriate parser

**Supported**: 30+ languages (OOP, procedural, web, config, scripting)

---

#### `load_codebase_dynamic.py` - GitHub Repository Loading
**Purpose**: Clones and loads repositories from GitHub

**Key Functions**:
- `load_repository(repo_url, branch)`: Main loading function
  - Clones repository
  - Detects languages
  - Returns file structure
  
- `get_files_by_language()`: Groups files by language

---

#### `logger_config.py` - Logging Configuration
**Purpose**: Sets up consistent logging across backend

**Key Functions**:
- `setup_logger(name)`: Creates logger instance
  - Logs to console and file
  - Includes timestamps
  - Color-coded by level

---

## Frontend Architecture

### Core Files

#### `app/page.js` - Main Chat Interface
**Purpose**: Primary React component for the chat application

**State Variables**:
- `query`: Current user input
- `messages`: Chat history
- `loading`: Query processing state
- `repositories`: Available repositories
- `selectedRepo`: Currently selected repository
- `stats`: Repository statistics
- `health`: System health status
- `showAddRepo`: Add repository modal visibility
- `newRepoUrl`: New repository URL input
- `addingRepo`: Repository addition state
- `processingStatus`: Repository processing progress
- `lastRefresh`: Last refresh timestamps
- `isRefreshing`: Manual refresh state
- `refreshError`: Refresh error messages

**Refs**:
- `messagesEndRef`: Auto-scroll to latest message
- `wsRef`: WebSocket connection
- `healthIntervalRef`: Health check interval
- `reposIntervalRef`: Repository polling interval
- `statsIntervalRef`: Stats polling interval

**Key Functions**:

1. **`useEffect` Hooks**:
   - Initial setup: Fetch repos, health, WebSocket
   - Adaptive polling based on processing activity
   - Auto-cleanup on unmount

2. **`connectWebSocket()`**:
   - Connects to `/ws` endpoint
   - Listens for `repository_status` events
   - Auto-reconnects on disconnect
   - Updates processing status

3. **`scrollToBottom()`**:
   - Auto-scrolls to latest message
   - Smooth scroll behavior

4. **`fetchHealth()`**:
   - GET `/api/health`
   - Updates system status
   - Tracks refresh time
   - Handles errors

5. **`fetchRepositories()`**:
   - GET `/api/repositories`
   - Updates repository list
   - Auto-selects first repo
   - Tracks refresh time

6. **`fetchStats(repoName)`**:
   - GET `/api/repositories/{repoName}/stats`
   - Updates stats display
   - Tracks refresh time

7. **`handleManualRefresh()`**:
   - Refreshes all data in parallel
   - Shows loading state
   - Prevents duplicate requests

8. **`getTimeSinceRefresh(key)`**:
   - Returns human-readable time
   - Formats: "30s ago", "5m ago", "2h ago"

9. **`handleRepoChange(repoName)`**:
   - Switches selected repository
   - Clears chat history
   - Fetches new stats

10. **`parseGitUrl(input)`**:
    - Parses various GitHub URL formats
    - Returns `owner/repo` format
    - Handles: URLs, SSH, .git suffix

11. **`handleAddRepository()`**:
    - POST `/api/repositories`
    - Validates input
    - Shows success/error
    - Clears form

12. **`handleDeleteRepository(repoDbName)`**:
    - DELETE `/api/repositories/{repoDbName}`
    - Confirms deletion
    - Clears selection if needed
    - Refreshes list

13. **`handleSubmit(e)`**:
    - POST `/api/query`
    - Sends query with repository
    - Displays AI response
    - Shows sources
    - Handles errors

14. **`getStatusIcon(status)`**:
    - Returns status indicator icon
    - Green: connected/configured/ready
    - Red: disconnected/not configured
    - Yellow: other

15. **`getOverallStatus()`**:
    - Determines system health
    - Returns color and text
    - Green: healthy
    - Yellow: degraded
    - Red: error

**UI Components**:
- Sidebar: Repository list, stats, connection status
- Main area: Chat messages, input form
- Header: Repository name, connection status
- Messages: User/AI/error message rendering
- Markdown: Rich text formatting with ReactMarkdown
- Sources: Citation cards with relevance scores
- Status: Real-time processing progress
- Refresh: Manual refresh button with spinner

**Refresh Strategy**:
- Health: 10 seconds (constant)
- Repositories: 5 seconds (active), 30 seconds (idle)
- Stats: 15 seconds (when repo selected)

---

#### `app/layout.js` - Root Layout
**Purpose**: Wraps entire application with layout

**Features**:
- Metadata configuration
- Font imports
- Global styles
- Root provider setup

---

#### `app/globals.css` - Global Styles
**Purpose**: Application-wide styling

**Key Classes**:
- `.markdown-content`: Markdown rendering styles
  - Headings (h1-h6): Sizing, bold, spacing
  - Paragraphs: Line height, margins
  - Code: Inline and block styling
  - Lists: Bullets, numbering
  - Tables: Borders, alignment
  - Blockquotes: Border, background
  - Links: Color, hover effects

---

#### `lib/utils.js` - Utility Functions
**Purpose**: Shared utility functions

**Functions**:
- `cn()`: Class name merging (Tailwind utilities)

---

#### `package.json` - Dependencies
**Key Dependencies**:
- `react`: UI library
- `next`: Framework
- `axios`: HTTP client
- `react-markdown`: Markdown rendering
- `remark-gfm`: GitHub-flavored markdown
- `lucide-react`: Icons
- `tailwindcss`: Styling
- `socket.io-client`: WebSocket (optional)

---

## Database Schema

### Node Types

```
RepositoryNode
├── name (unique)
├── type: "Code repository"
└── children → [FileNode, ClassNode, FunctionNode]

FileNode
├── name
├── lineno
├── code
├── code_embedding (768-dim)
├── summary
├── summary_embedding (768-dim)
├── parameters
└── children → [ClassNode, FunctionNode]

ClassNode
├── name
├── lineno
├── code
├── code_embedding (768-dim)
├── summary
├── summary_embedding (768-dim)
├── parameters
└── children → [FunctionNode]

FunctionNode
├── name
├── lineno
├── code
├── code_embedding (768-dim)
├── summary
├── summary_embedding (768-dim)
└── parameters
```

### Relationships

- `CHILD`: Parent → Child (one-to-many)
- `PARENT`: Child → Parent (reverse)

### Vector Indexes

- `fileSummaryEmbeddingIndex`: File summary vectors
- `classSummaryEmbeddingIndex`: Class summary vectors
- `functionSummaryEmbeddingIndex`: Function summary vectors
- `fileCodeEmbeddingIndex`: File code vectors
- `classCodeEmbeddingIndex`: Class code vectors
- `functionCodeEmbeddingIndex`: Function code vectors

---

## API Reference

### Endpoints

#### Repository Management

**GET /api/repositories**
- Returns all repositories
- Response: `{ repositories: [{ name, db_name, status, stats }] }`

**POST /api/repositories**
- Adds new repository
- Body: `{ repo_url: "owner/repo", branch: "main" }`
- Response: `{ message, repository, db_name, status }`

**DELETE /api/repositories/{repo_name}**
- Deletes repository
- Response: `{ message }`

**GET /api/repositories/{repo_name}/stats**
- Returns repository statistics
- Response: `{ repository, file_count, class_count, function_count, total_nodes, languages }`

**GET /api/repositories/{repo_name}/status**
- Returns processing status
- Response: `{ repository, status, progress, message, current_step }`

#### Query & Health

**POST /api/query**
- Queries codebase with AI
- Body: `{ query: "...", top_k: 5, repository: "..." }`
- Response: `{ answer: "...", sources: [...] }`

**GET /api/health**
- System health check
- Response: `{ status, components: {...}, timestamp }`

**WS /ws**
- WebSocket for real-time updates
- Events: `repository_status`

---

## Data Flow

### Repository Ingestion Flow

```
User adds repository
    ↓
POST /api/repositories
    ↓
parse_git_url() → validate format
    ↓
process_repository_task() [Background]
    ↓
load_codebase_dynamic() → Clone from GitHub
    ↓
language_detector() → Detect file types
    ↓
extract_structure() / extract_procedural() → Parse code
    ↓
ingest_structure() → Store in Neo4j
    ↓
code_embeddings() → Generate vectors (768-dim)
    ↓
generate_summary() → Create AI summaries
    ↓
create_vector_indexes() → Build search indexes
    ↓
WebSocket broadcast: status = "complete"
    ↓
Ready for queries!
```

### Query Processing Flow

```
User asks question
    ↓
POST /api/query { query, repository }
    ↓
QueryAnalyzer → Detect type, extract keywords
    ↓
retrieve_top_k() [4 strategies]
    ├─ Strategy 1: Semantic search (summaries)
    ├─ Strategy 2: Graph-based search (keywords)
    ├─ Strategy 3: Code embedding search
    └─ Strategy 4: Related node enrichment
    ↓
ContextBuilder → Organize nodes by type
    ↓
PromptEngineer → Generate query-type-specific prompt
    ↓
LLM (Gemini) → Generate answer
    ↓
Format response with sources
    ↓
Return to frontend
    ↓
Display answer + citations
```

---

## Configuration

### Environment Variables

**Backend (.env)**:
```env
ACCESS_TOKEN=github_personal_access_token
GOOGLE_API_KEY=gemini_api_key
password=neo4j_password
NEO4J_DATABASE=neo4j
NEO4J_CONNECTION_URL=neo4j://127.0.0.1:7687
```

**Frontend (.env)**:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Performance Metrics

- **Embedding Generation**: 768-dimensional vectors
- **Vector Search**: Sub-second retrieval
- **LLM Response**: 2-10 seconds
- **Total Query Time**: 2.5-11.5 seconds
- **Repository Processing**: 5 min - 3 hours (depends on size)

---

## Error Handling

- **400**: Invalid request format
- **404**: Repository/resource not found
- **500**: Server error (check logs)
- **WebSocket**: Auto-reconnect with 3-second delay

---

## Logging

All components log to:
- Console: Real-time output
- **File**: `backend/src/api.py`
t_YYYYMMDD.log`

Log levels: DEBUG, INFO, WARNING, ERROR

---

## Future Enhancements

- [ ] Multi-language support for UI
- [ ] Advanced filtering options
- [ ] Code diff analysis
- [ ] Performance profiling
- [ ] Custom embeddings model
- [ ] Database query optimization
- [ ] Caching layer
- [ ] Rate limiting

---

**Last Updated**: November 2, 2025
**Version**: 2.0
**Status**: Production Ready
