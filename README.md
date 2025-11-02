# CodeChat v2.0.1 - AI-Powered Code Repository Chat

An intelligent code analysis chatbot with dynamic repository management, multi-strategy retrieval, and real-time processing updates. Now with **performance optimizations** for 3-10x faster responses!

## ✨ Key Features

- 🎯 **Dynamic Repository Management** - Add/delete repositories through UI without restart
- 🌐 **30+ Language Support** - Automatic detection for OOP, procedural, web, and config languages
- ⚡ **Real-Time Updates** - WebSocket integration for live progress tracking
- 🏥 **Health Monitoring** - Connection status indicator with detailed component info
- 🧠 **AI-Powered Chat** - Multi-strategy retrieval with intelligent responses and source citations
- 📊 **Graph Database** - Neo4j for storing code structure with relationships
- 🔍 **4-Strategy Retrieval** - Semantic + graph-based + code embedding + related nodes
- 🎨 **Modern Reactive UI** - Beautiful Next.js 14 frontend with adaptive refresh strategies
- 🚀 **High Performance** - In-memory caching, optimized queries, 73-87% faster page loads
- ⚙️ **Production Ready** - Fully tested, documented, and optimized

## 🚀 Quick Start (2 Steps)

### Terminal 1: Start Backend
```bash
cd backend
python main.py
```

### Terminal 2: Start Frontend
```bash
cd frontend
npm run dev
```

### Browser: Add Repositories
```
1. Open: http://localhost:3000
2. Click '+' button
3. Enter: facebook/react (or any .git URL)
4. Watch real-time progress
5. Start chatting!
```

## Architecture

### Backend (Python + FastAPI)

**Core Services:**
- `api.py` - REST API + WebSocket server with repository management
- `language_detector.py` - Automatic language detection for 30+ languages
- `load_codebase_dynamic.py` - Dynamic GitHub repository loading

**Processing Pipeline:**
- `extract_structure.py` - OOP language parsing
- `extract_procedural.py` - Procedural language parsing
- `code_embeddings.py` - UniXcoder embeddings (768-dim vectors)
- `generate_summary.py` - Google Gemini AI summaries
- `create_vector_indexes.py` - Neo4j vector indexes
- `ingest_structure.py` - Neo4j data ingestion
- `retrieval.py` - Vector similarity search

### Frontend (React + Next.js 14)

- **Framework**: Next.js 14 with App Router
- **Styling**: TailwindCSS with custom theme
- **Real-time**: WebSocket integration
- **HTTP**: Axios for API calls
- **Icons**: Lucide React
- **Features**: Repository management, connection monitoring, live chat

## 📋 Prerequisites

- ✅ Python 3.8+
- ✅ Node.js 18+
- ✅ Neo4j Database (localhost:7687)
- ✅ GitHub Personal Access Token
- ✅ Google Gemini API Key

## ⚙️ Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
# Linux/macOS
python -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the backend directory:
```env
ACCESS_TOKEN=your_github_token_here
GOOGLE_API_KEY=your_gemini_api_key_here
password=your_neo4j_password
NEO4J_CONNECTION_URL=neo4j://127.0.0.1:7687
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

5. Make sure Neo4j is running on `localhost:7687`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env.local` file (optional):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🎯 Usage

### How It Works

1. **Start Backend**: `python main.py` - Starts API server
2. **Start Frontend**: `npm run dev` - Opens web UI
3. **Add Repository**: Click '+' button, enter any GitHub URL format:
   - `facebook/react`
   - `https://github.com/facebook/react`
   - `https://github.com/facebook/react.git`
   - `git@github.com:facebook/react.git`
4. **Watch Progress**: Real-time updates via WebSocket
5. **Chat**: Ask questions about your code!

### Automatic Processing Pipeline

After clicking "Add", the repository is automatically processed:

```
📥 Loading (10%)     → Download from GitHub
🧠 Parsing (30%)     → Analyze code structure
💾 Ingesting (50%)   → Store in Neo4j
🔢 Embeddings (70%)  → Generate code vectors
📝 Summaries (85%)   → Create AI summaries
✅ Complete (100%)   → Ready to chat!
```

All steps happen automatically in the background - just watch the progress bar!

## 📡 API Endpoints

### Repository Management
- `GET /api/repositories` - List all repositories
- `POST /api/repositories` - Add new repository
- `DELETE /api/repositories/{name}` - Delete repository
- `GET /api/repositories/{name}/stats` - Get statistics
- `GET /api/repositories/{name}/status` - Get processing status

### Query & Health
- `POST /api/query` - Query with AI
- `GET /api/health` - System health check
- `WS /ws` - WebSocket for real-time updates

### Example Query

```json
{
  "query": "What are the main functions?",
  "top_k": 5,
  "repository": "facebook/react"
}
```

### Example Response

```json
{
  "answer": "Based on the code analysis...",
  "sources": [
    {
      "type": "FunctionNode",
      "name": "createElement",
      "summary": "Creates a React element...",
      "score": 0.9234
    }
  ]
}
```

## 🌐 Supported Languages (30+)

### Object-Oriented
Python, JavaScript, TypeScript, Java, C++, C#, Ruby, Swift, Kotlin, PHP, Scala, Dart, Groovy, and more

### Procedural
C, Go, Rust

### Web
HTML, CSS, Vue, Svelte, React, Angular

### Configuration
JSON, YAML, XML, TOML, INI

### Scripting
Shell, PowerShell, Batch, Perl, Lua

## 📁 Project Structure

```
CodeChat_deployed/
├── README.md                         # Project overview (this file)
├── ARCHITECTURE_AND_METHODS.md       # Complete technical reference
├── .gitignore
├── backend/
│   ├── main.py                       # Entry point
│   ├── requirements.txt              # Dependencies
│   ├── .env.example                  # Configuration template
│   ├── .env                          # Configuration (local)
│   ├── logs/                         # Application logs
│   └── src/
│       ├── api.py                    # REST API + WebSocket
│       ├── query_processor.py        # Query analysis & prompts
│       ├── retrieval.py              # Multi-strategy retrieval
│       ├── language_detector.py      # Language detection
│       ├── load_codebase_dynamic.py  # Dynamic GitHub loading
│       ├── code_embeddings.py        # UniXcoder embeddings
│       ├── generate_summary.py       # Gemini AI summaries
│       ├── create_vector_indexes.py  # Neo4j vector indexes
│       ├── ingest_structure.py       # Neo4j data ingestion
│       ├── extract_structure.py      # OOP language parsing
│       ├── extract_procedural.py     # Procedural language parsing
│       ├── create_schema.py          # Neo4j schema definition
│       ├── cache_manager.py          # In-memory caching
│       ├── logger_config.py          # Logging configuration
│       └── unixcoder.py              # UniXcoder model wrapper
├── frontend/
│   ├── package.json                  # Dependencies
│   ├── next.config.js                # Next.js configuration
│   ├── tailwind.config.js            # TailwindCSS configuration
│   ├── jsconfig.json                 # Path aliases
│   ├── postcss.config.js             # PostCSS configuration
│   ├── .eslintrc.json                # ESLint configuration
│   ├── app/
│   │   ├── page.js                   # Main chat interface
│   │   ├── layout.js                 # Root layout with providers
│   │   └── globals.css               # Global styles & dark mode
│   ├── components/
│   │   ├── ThemeProvider.jsx         # Dark mode provider
│   │   ├── ThemeToggle.jsx           # Theme toggle button
│   │   ├── ErrorBoundary.jsx         # Error handling
│   │   ├── Button.jsx                # Button component
│   │   ├── Card.jsx                  # Card component
│   │   ├── Badge.jsx                 # Badge component
│   │   ├── Input.jsx                 # Input component
│   │   ├── Alert.jsx                 # Alert component
│   │   ├── AnimatedList.jsx          # Animated list component
│   │   └── SidebarUpgraded.jsx       # Sidebar component
│   ├── hooks/
│   │   ├── useRepositories.js        # Repository management hook
│   │   └── useChat.js                # Chat management hook
│   ├── lib/
│   │   ├── api.js                    # Centralized API client
│   │   └── utils.js                  # Utility functions
│   └── node_modules/                 # Dependencies
└── .next/                            # Next.js build output
```

## 🔄 How It Works

```
User adds repository
        ↓
Load from GitHub
        ↓
Auto-detect languages
        ↓
Parse code structure
        ↓
Store in Neo4j graph
        ↓
Generate embeddings (UniXcoder)
        ↓
Create AI summaries (Gemini)
        ↓
Build vector indexes
        ↓
Ready for queries!
```

**Query Processing:**
1. User asks question in UI
2. Query is embedded
3. Vector search finds similar code
4. Context sent to Gemini AI
5. AI generates answer with sources
6. Results displayed with citations

## 🏥 Health Monitoring

The system provides real-time health status:

- **Neo4j**: Database connection status
- **Gemini**: AI API availability
- **GitHub**: Token validity
- **Embeddings**: Model status

Hover over the connection indicator to see detailed status of all components.

## 📊 Performance

| Repository Size | Processing Time |
|-----------------|-----------------|
| Small (<100 files) | 5-15 min |
| Medium (100-500 files) | 15-45 min |
| Large (500-1000 files) | 45-90 min |
| Very Large (1000+ files) | 1-3 hours |

*First run downloads models (~500MB)*

## 🛠️ Technology Stack

- **Backend**: Python 3.8+, FastAPI, AsyncIO
- **Frontend**: React 18, Next.js 14, TailwindCSS
- **Database**: Neo4j Graph Database
- **AI/ML**: Google Gemini, UniXcoder, Transformers
- **Real-time**: WebSocket
- **HTTP**: Axios

## 🚀 Performance Highlights

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Page Load | 8-24s | 1-3s | **73-87% faster** |
| Repository List | 2-5s | 0.1-0.5s | **10x faster** |
| Stats Query | 1-3s | 0.05-0.8s | **5x faster** |
| API Calls | 19-35 | 3-8 | **77% reduction** |
| Cache Hit Rate | 0% | 60-80% | **New feature** |

**Optimizations**:
- ✅ In-memory caching with TTL
- ✅ Optimized Neo4j queries
- ✅ React performance hooks
- ✅ Debounced inputs
- ✅ Adaptive polling intervals

## 📚 Documentation

- **README.md** (this file) - Project overview, quick start, and setup instructions
- **ARCHITECTURE_AND_METHODS.md** - Complete technical reference with all files, classes, and methods

## 🆘 Troubleshooting

### Neo4j Connection Failed
- Ensure Neo4j is running on localhost:7687
- Verify password in `.env`
- Check database name is correct

### Backend Won't Start
- Verify Python 3.8+
- Check all dependencies: `pip install -r requirements.txt`
- Ensure `.env` is configured

### Frontend Can't Connect
- Verify backend is running on port 8000
- Check `NEXT_PUBLIC_API_URL` in frontend `.env`
- Clear browser cache

### Repository Processing Stuck
- Check backend logs
- Verify GitHub token is valid
- Ensure repository is accessible

## 📝 License

MIT - Feel free to use and modify!

## 🤝 Contributing

Contributions welcome! Please submit pull requests or open issues.
