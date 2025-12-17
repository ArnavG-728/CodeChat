from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import List, Optional, Dict
import os
import asyncio
import threading
import re
from dotenv import load_dotenv
from datetime import datetime
import json

# Import backend functions (using relative imports)
from .retrieval import retrieve_top_k
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from neo4j import GraphDatabase
from .language_detector import detect_language, analyze_repository
from .load_codebase_dynamic import DynamicGithubLoader
from .extract_structure import extract_codebase_structure
from .ingest_structure import IngestStructure
from .code_embeddings import run_all as generate_embeddings
from .generate_summary import main as generate_summaries
from .create_vector_indexes import create_vector_indexes
from .logger_config import setup_logger
from .query_processor import get_processor
from .cache_manager import get_cache, cached

load_dotenv()

# Setup logger
logger = setup_logger(__name__)

app = FastAPI(title="CodeChat Enhanced API", version="2.0.0")
logger.info("🚀 FastAPI application initialized")

# Configure CORS - Restrict to known origins for security
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Initialize LLM with configurable model
llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite"),
    google_api_key=os.getenv("GOOGLE_API_KEY", ""),
    temperature=0.2,
)

# Neo4j connection with production-ready pool configuration
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

# Initialize Neo4j driver with comprehensive error handling
try:
    if not NEO4J_PASSWORD:
        logger.error("❌ NEO4J_PASSWORD is not set in environment variables")
        logger.error("💡 Please set NEO4J_PASSWORD in your backend/.env file")
        raise ValueError("NEO4J_PASSWORD is required. Check backend/.env file.")
    
    logger.info(f"🔗 Connecting to Neo4j at {NEO4J_URI}...")
    logger.info(f"👤 Using username: {NEO4J_USERNAME}")
    
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        max_connection_pool_size=50,
        connection_acquisition_timeout=30.0,
        max_transaction_retry_time=15.0,
        keep_alive=True
    )
    
    # Test connection on startup
    logger.info("🔍 Testing Neo4j connection...")
    with driver.session(database="neo4j") as session:
        session.run("RETURN 1").single()
    logger.info("✅ Neo4j connection successful!")
    
except Exception as e:
    error_msg = str(e).lower()
    
    # Authentication errors
    if "authentication" in error_msg or "unauthorized" in error_msg or "credentials" in error_msg:
        logger.error("❌ Neo4j Authentication Failed!")
        logger.error(f"   Error: {e}")
        logger.error("")
        logger.error("💡 Possible fixes:")
        logger.error("   1. Check NEO4J_USERNAME in backend/.env (current: '{}')" .format(NEO4J_USERNAME))
        logger.error("   2. Check NEO4J_PASSWORD in backend/.env")
        logger.error("   3. For Neo4j Aura: Use credentials from Aura console")
        logger.error("   4. For local Neo4j: Verify password in Neo4j Browser")
        raise RuntimeError(f"Neo4j authentication failed. Check your credentials in backend/.env") from e
    
    # Connection errors
    elif "failed to establish connection" in error_msg or "unable to connect" in error_msg or "connection refused" in error_msg:
        logger.error("❌ Cannot connect to Neo4j database!")
        logger.error(f"   URI: {NEO4J_URI}")
        logger.error(f"   Error: {e}")
        logger.error("")
        logger.error("💡 Possible fixes:")
        logger.error("   1. Check if Neo4j is running (local) or URI is correct (Aura)")
        logger.error("   2. Verify NEO4J_URI in backend/.env")
        logger.error("      - Local: neo4j://127.0.0.1:7687")
        logger.error("      - Aura: neo4j+s://<instance>.databases.neo4j.io")
        logger.error("   3. Check firewall/network settings")
        raise RuntimeError(f"Cannot connect to Neo4j at {NEO4J_URI}. Check if database is running.") from e
    
    # Protocol/SSL errors (Aura-specific)
    elif "ssl" in error_msg or "certificate" in error_msg or "encryption" in error_msg:
        logger.error("❌ SSL/Encryption error connecting to Neo4j!")
        logger.error(f"   Error: {e}")
        logger.error("")
        logger.error("💡 For Neo4j Aura, use: neo4j+s://<instance>.databases.neo4j.io")
        logger.error("💡 For local Neo4j, use: neo4j://127.0.0.1:7687")
        raise RuntimeError("SSL/Encryption error. Check NEO4J_URI protocol (neo4j+s:// for Aura).") from e
    
    # Generic error
    else:
        logger.error("❌ Failed to initialize Neo4j driver!")
        logger.error(f"   URI: {NEO4J_URI}")
        logger.error(f"   Username: {NEO4J_USERNAME}")
        logger.error(f"   Error: {e}")
        logger.error("")
        logger.error("💡 Check your Neo4j configuration in backend/.env")
        raise RuntimeError(f"Neo4j initialization failed: {e}") from e

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# Thread-safe in-memory storage for repository processing status
repository_status = {}
status_lock = threading.Lock()

def get_repository_status(repo_name: str) -> Optional[Dict]:
    """Thread-safe getter for repository status"""
    with status_lock:
        return repository_status.get(repo_name)

def set_repository_status(repo_name: str, status: Dict) -> None:
    """Thread-safe setter for repository status"""
    with status_lock:
        repository_status[repo_name] = status

def delete_repository_status(repo_name: str) -> None:
    """Thread-safe deletion of repository status"""
    with status_lock:
        if repo_name in repository_status:
            del repository_status[repo_name]

# Pydantic models
class RepositoryAdd(BaseModel):
    repo_url: str  # Format: owner/repo-name
    branch: Optional[str] = "main"
    
    @validator('repo_url')
    def validate_repo_url(cls, v):
        """Validate repository URL format"""
        v = v.strip()
        # Allow owner/repo format
        if re.match(r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+$', v):
            return v
        # Allow full GitHub URLs and extract owner/repo
        match = re.match(r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?/?$', v)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
        raise ValueError('Invalid repository format. Use "owner/repo" or full GitHub URL')
    
    @validator('branch')
    def validate_branch(cls, v):
        """Validate branch name"""
        if not v or not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Invalid branch name')
        return v

class RepositoryInfo(BaseModel):
    name: str
    db_name: str
    status: str
    added_at: str
    languages: Optional[Dict] = None
    stats: Optional[Dict] = None

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    repository: Optional[str] = None
    
    @validator('query')
    def validate_query(cls, v):
        """Validate query string"""
        v = v.strip()
        if not v:
            raise ValueError('Query cannot be empty')
        if len(v) > 1000:
            raise ValueError('Query too long (max 1000 characters)')
        return v
    
    @validator('top_k')
    def validate_top_k(cls, v):
        """Validate top_k parameter"""
        if v < 1 or v > 20:
            raise ValueError('top_k must be between 1 and 20')
        return v

class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]

class HealthStatus(BaseModel):
    status: str
    components: Dict[str, Dict[str, str]]
    timestamp: str

class RepositoryStatus(BaseModel):
    repository: str
    status: str  # pending, loading, parsing, ingesting, embeddings, complete, error
    progress: int  # 0-100
    message: str
    current_step: Optional[str] = None


@app.get("/")
async def root():
    return {
        "message": "CodeChat Enhanced API v2.0",
        "version": "2.0.0",
        "features": [
            "Dynamic repository management",
            "Automatic language detection",
            "Real-time processing status",
            "WebSocket support",
            "Health monitoring"
        ],
        "endpoints": {
            "repositories": {
                "list": "GET /api/repositories",
                "add": "POST /api/repositories",
                "delete": "DELETE /api/repositories/{repo_name}",
                "stats": "GET /api/repositories/{repo_name}/stats",
                "status": "GET /api/repositories/{repo_name}/status"
            },
            "query": "POST /api/query",
            "health": "GET /api/health",
            "websocket": "WS /ws"
        }
    }


@app.get("/api/health", response_model=HealthStatus)
async def comprehensive_health_check():
    """Comprehensive health check for all components"""
    logger.debug("Health check requested")
    components = {}
    overall_status = "healthy"
    
    # Check Neo4j
    try:
        with driver.session(database="neo4j") as session:
            result = session.run("RETURN 1")
            result.single()
        components["neo4j"] = {
            "status": "connected",
            "message": "Neo4j database is accessible",
            "url": NEO4J_URI
        }
    except Exception as e:
        components["neo4j"] = {
            "status": "disconnected",
            "message": f"Failed to connect: {str(e)}",
            "url": NEO4J_URI
        }
        overall_status = "degraded"
    
    # Check Gemini API
    try:
        google_api_key = os.getenv("GOOGLE_API_KEY", "")
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        if google_api_key:
            components["gemini"] = {
                "status": "configured",
                "message": "API key is configured",
                "model": gemini_model
            }
        else:
            components["gemini"] = {
                "status": "not_configured",
                "message": "API key not found",
                "model": gemini_model
            }
            overall_status = "degraded"
    except Exception as e:
        components["gemini"] = {
            "status": "error",
            "message": str(e),
            "model": "gemini-2.5-flash"
        }
        overall_status = "degraded"
    
    # Check GitHub Access Token
    try:
        access_token = os.getenv("ACCESS_TOKEN", "")
        if access_token:
            components["github"] = {
                "status": "configured",
                "message": "Access token is configured",
                "api": "https://api.github.com"
            }
        else:
            components["github"] = {
                "status": "not_configured",
                "message": "Access token not found",
                "api": "https://api.github.com"
            }
            overall_status = "degraded"
    except Exception as e:
        components["github"] = {
            "status": "error",
            "message": str(e),
            "api": "https://api.github.com"
        }
        overall_status = "degraded"
    
    # Check Embedding Model
    try:
        components["embeddings"] = {
            "status": "ready",
            "message": "Embedding model initialized",
            "model": "text-embedding-004"
        }
    except Exception as e:
        components["embeddings"] = {
            "status": "error",
            "message": str(e),
            "model": "text-embedding-004"
        }
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "components": components,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/repositories")
async def list_repositories():
    """List all available repositories from the neo4j database (cached for 30 seconds)"""
    # Check cache first
    cache = get_cache()
    cache_key = "repos:list"
    cached_repos = cache.get(cache_key)
    
    if cached_repos is not None:
        logger.debug("✅ Returning cached repository list")
        return cached_repos
    
    logger.info("📋 Listing repositories")
    try:
        # Query all RepositoryNode entries in the neo4j database
        repositories = []
        with driver.session(database="neo4j") as session:
            # Optimized: Get all repo stats in one query
            result = session.run("""
                MATCH (r:RepositoryNode)
                OPTIONAL MATCH (r)-[:CHILD*]->(f:FileNode)
                WITH r, count(DISTINCT f) as file_count
                OPTIONAL MATCH (r)-[:CHILD*]->(c:ClassNode)
                WITH r, file_count, count(DISTINCT c) as class_count
                OPTIONAL MATCH (r)-[:CHILD*]->(fn:FunctionNode)
                RETURN r.name as name, file_count, class_count, count(DISTINCT fn) as function_count
            """)
            
            for record in result:
                repo_name = record["name"]
                file_count = record["file_count"] or 0
                class_count = record["class_count"] or 0
                function_count = record["function_count"] or 0
                
                status_info = get_repository_status(repo_name) or {}
                repositories.append({
                    "name": repo_name,
                    "db_name": "neo4j",  # All repos use the same database
                    "status": status_info.get("status", "complete"),
                    "stats": {
                        "files": file_count,
                        "classes": class_count,
                        "functions": function_count,
                        "total": file_count + class_count + function_count
                    }
                })
        
        logger.info(f"✅ Found {len(repositories)} repositories")
        response = {"repositories": repositories}
        
        # Cache for 30 seconds
        cache.set(cache_key, response, ttl=30)
        logger.debug("💾 Cached repository list")
        
        return response
    except Exception as e:
        logger.error(f"❌ Error fetching repositories: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching repositories: {str(e)}")


async def process_repository_task(repo_url: str, branch: str, repo_name: str):
    """Background task to process repository"""
    logger.info(f"🔄 Starting repository processing: {repo_url} (branch: {branch})")
    db_name = "neo4j"  # Use default database
    try:
        # Update status: loading
        logger.info(f"📥 Loading repository from GitHub: {repo_url}")
        status_data = {
            "status": "loading",
            "progress": 10,
            "message": "Loading repository from GitHub...",
            "current_step": "Loading"
        }
        set_repository_status(repo_name, status_data)
        await manager.broadcast({
            "type": "repository_status",
            "data": status_data | {"repository": repo_name}
        })
        
        # Load repository
        loader = DynamicGithubLoader(
            repo=repo_url,
            branch=branch,
            access_token=os.getenv("ACCESS_TOKEN", "")
        )
        documents = loader.load()
        logger.info(f"✅ Loaded {len(documents)} documents from {repo_url}")
        
        # Analyze languages
        filenames = [doc.metadata.get("source", "") for doc in documents]
        language_analysis = analyze_repository(filenames)
        logger.info(f"🔍 Language analysis: {language_analysis.get('primary_language', 'unknown')}")
        
        # Update status: parsing
        status_data = {
            "status": "parsing",
            "progress": 30,
            "message": f"Parsing {len(documents)} files...",
            "current_step": "Parsing",
            "languages": language_analysis
        }
        set_repository_status(repo_name, status_data)
        await manager.broadcast({
            "type": "repository_status",
            "data": status_data | {"repository": repo_name}
        })
        
        # Extract structure
        logger.info(f"🔧 Extracting code structure from {len(documents)} files")
        structures = extract_codebase_structure(documents)
        logger.info(f"✅ Extracted {len(structures)} structures")
        
        # Update status: ingesting
        status_data = {
            "status": "ingesting",
            "progress": 50,
            "message": f"Ingesting {len(structures)} structures...",
            "current_step": "Ingesting"
        }
        set_repository_status(repo_name, status_data)
        await manager.broadcast({
            "type": "repository_status",
            "data": status_data | {"repository": repo_name}
        })
        
        # Ingest into Neo4j
        logger.info(f"💾 Ingesting into Neo4j database: {db_name}")
        ingestor = IngestStructure(repo_name)
        ingestor.create_repository_node()
        
        for i, structure in enumerate(structures, 1):
            logger.debug(f"Ingesting structure {i}/{len(structures)}")
            ingestor.ingest(structure)
        logger.info(f"✅ Ingested {len(structures)} structures into Neo4j")
        
        # Validate repository structure
        logger.info("🔍 Validating repository structure...")
        validation = ingestor.validate_repository_structure()
        if validation:
            logger.info(f"📊 Validation complete: {validation['connected']} connected, {validation['orphaned']} orphaned nodes")
        
        # Update status: embeddings
        status_data = {
            "status": "embeddings",
            "progress": 70,
            "message": "Generating embeddings...",
            "current_step": "Embeddings"
        }
        set_repository_status(repo_name, status_data)
        await manager.broadcast({
            "type": "repository_status",
            "data": status_data | {"repository": repo_name}
        })
        
        # Set environment variable for database
        os.environ["NEO4J_DATABASE"] = db_name
        
        # Generate embeddings
        logger.info(f"🧠 Generating code embeddings for {db_name}")
        generate_embeddings()
        logger.info(f"✅ Code embeddings generated")
        
        # Update status: summaries
        status_data = {
            "status": "summaries",
            "progress": 85,
            "message": "Generating summaries...",
            "current_step": "Summaries"
        }
        set_repository_status(repo_name, status_data)
        await manager.broadcast({
            "type": "repository_status",
            "data": status_data | {"repository": repo_name}
        })
        
        # Generate summaries
        logger.info(f"📝 Generating AI summaries for {db_name}")
        generate_summaries()
        logger.info(f"✅ AI summaries generated")
        
        # Create vector indexes
        logger.info(f"🔍 Creating vector indexes for {db_name}")
        create_vector_indexes(dimension=768)
        logger.info(f"✅ Vector indexes created")
        
        # Update status: complete
        status_data = {
            "status": "complete",
            "progress": 100,
            "message": "Repository successfully processed!",
            "current_step": "Complete",
            "languages": language_analysis
        }
        set_repository_status(repo_name, status_data)
        await manager.broadcast({
            "type": "repository_status",
            "data": status_data | {"repository": repo_name}
        })
        
        # Invalidate cache to force refresh
        cache = get_cache()
        cache.invalidate("repos:list")
        cache.invalidate(f"stats:{repo_name}")
        logger.debug(f"🗑️ Cache invalidated for {repo_name} after completion")
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"❌ ERROR processing repository {repo_name}: {str(e)}")
        logger.error(f"Stack trace:\n{error_details}")
        
        status_data = {
            "status": "error",
            "progress": 0,
            "message": f"Error: {str(e)}",
            "current_step": "Error",
            "error_details": error_details
        }
        set_repository_status(repo_name, status_data)
        await manager.broadcast({
            "type": "repository_status",
            "data": status_data | {"repository": repo_name}
        })


@app.post("/api/repositories")
async def add_repository(repo: RepositoryAdd, background_tasks: BackgroundTasks):
    """Add a new repository for processing"""
    logger.info(f"➕ Adding repository: {repo.repo_url}")
    try:
        # Validate repository format
        if "/" not in repo.repo_url:
            raise HTTPException(status_code=400, detail="Invalid repository format. Use 'owner/repo-name'")
        
        # Get repository name
        repo_name = repo.repo_url.split("/")[-1]
        
        # Check if repository already exists in neo4j database
        with driver.session(database="neo4j") as session:
            existing = session.run(
                "MATCH (r:RepositoryNode {name: $repo_name}) RETURN r.name as name",
                repo_name=repo_name
            ).single()
            
            if existing:
                raise HTTPException(status_code=400, detail=f"Repository '{repo_name}' already exists")
        
        # Initialize status (use repo_name as key)
        set_repository_status(repo_name, {
            "status": "pending",
            "progress": 0,
            "message": "Repository added to queue...",
            "current_step": "Pending"
        })
        
        # Add to background tasks (pass repo_name instead of db_name)
        background_tasks.add_task(process_repository_task, repo.repo_url, repo.branch, repo_name)
        logger.info(f"✅ Repository {repo_name} added to processing queue")
        
        return {
            "message": "Repository added successfully",
            "repository": repo_name,
            "db_name": "neo4j",  # All repos use the same database
            "status": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding repository: {str(e)}")


@app.get("/api/repositories/{repo_name}/status", response_model=RepositoryStatus)
async def get_repo_status(repo_name: str):
    """Get processing status of a repository"""
    status = get_repository_status(repo_name)
    if not status:
        raise HTTPException(status_code=404, detail="Repository not found or not being processed")
    
    return {
        "repository": repo_name,
        **status
    }


@app.delete("/api/repositories/{repo_name}")
async def delete_repository(repo_name: str):
    """Delete a repository from the neo4j database"""
    try:
        with driver.session(database="neo4j") as session:
            # Check if repository exists
            existing = session.run(
                "MATCH (r:RepositoryNode {name: $repo_name}) RETURN r.name as name",
                repo_name=repo_name
            ).single()
            
            if not existing:
                raise HTTPException(status_code=404, detail=f"Repository '{repo_name}' not found")
            
            # Delete repository and all its children
            session.run(
                "MATCH (r:RepositoryNode {name: $repo_name})-[:CHILD*0..]->(n) DETACH DELETE n",
                repo_name=repo_name
            )
        
        # Remove from status
        delete_repository_status(repo_name)
        
        # Invalidate cache
        cache = get_cache()
        cache.invalidate("repos:list")
        cache.invalidate(f"stats:{repo_name}")
        logger.debug(f"🗑️ Cache invalidated for {repo_name}")
        
        return {"message": f"Repository '{repo_name}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting repository: {str(e)}")


@app.get("/api/repositories/{repo_name}/stats")
async def get_repository_stats(repo_name: str):
    """Get statistics for a specific repository (cached for 60 seconds)"""
    # Check cache first
    cache = get_cache()
    cache_key = f"stats:{repo_name}"
    cached_stats = cache.get(cache_key)
    
    if cached_stats is not None:
        logger.debug(f"✅ Returning cached stats for {repo_name}")
        return cached_stats
    
    try:
        # Use neo4j database and filter by repository name
        with driver.session(database="neo4j") as session:
            # Optimize: Run all count queries in a single transaction
            result = session.run("""
                MATCH (r:RepositoryNode {name: $repo_name})
                OPTIONAL MATCH (r)-[:CHILD*]->(f:FileNode)
                WITH r, count(DISTINCT f) as file_count
                OPTIONAL MATCH (r)-[:CHILD*]->(c:ClassNode)
                WITH r, file_count, count(DISTINCT c) as class_count
                OPTIONAL MATCH (r)-[:CHILD*]->(fn:FunctionNode)
                RETURN file_count, class_count, count(DISTINCT fn) as function_count
            """, repo_name=repo_name).single()
            
            file_count = result["file_count"] or 0
            class_count = result["class_count"] or 0
            function_count = result["function_count"] or 0
            
            # Get language distribution from file extensions
            languages = {}
            try:
                lang_result = session.run("""
                    MATCH (r:RepositoryNode {name: $repo_name})-[:CHILD*]->(f:FileNode)
                    WITH f.name as filename
                    WHERE filename CONTAINS '.'
                    WITH split(filename, '.')[-1] as ext
                    RETURN ext as lang, count(*) as count
                    ORDER BY count DESC
                    LIMIT 5
                """, repo_name=repo_name)
                for record in lang_result:
                    languages[record["lang"]] = record["count"]
            except Exception as e:
                logger.warning(f"Could not get language distribution: {e}")
            
            stats = {
                "repository": repo_name,
                "file_count": file_count,
                "class_count": class_count,
                "function_count": function_count,
                "total_nodes": file_count + class_count + function_count,
                "languages": languages
            }
            
            # Cache for 60 seconds
            cache.set(cache_key, stats, ttl=60)
            logger.debug(f"💾 Cached stats for {repo_name}")
            
            return stats
    except Exception as e:
        logger.error(f"Error fetching stats for {repo_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@app.post("/api/query", response_model=QueryResponse)
async def query_codebase(request: QueryRequest):
    """
    Advanced query endpoint with multi-strategy retrieval and intelligent prompt engineering.
    
    Features:
    - Multi-strategy retrieval (semantic + graph-based + code search)
    - Query type detection and analysis
    - Context-aware prompt engineering
    - Comprehensive source citations
    - Performance optimization
    """
    logger.info(f"🔍 Query received: {request.query[:50]}... (repository: {request.repository})")
    try:
        # Step 1: Retrieve relevant nodes using multi-strategy approach
        logger.debug(f"Retrieving top {request.top_k} nodes using multi-strategy retrieval for repository: {request.repository}")
        retrieved_nodes = retrieve_top_k(
            request.query, 
            top_k=request.top_k,
            use_multi_strategy=True,  # Enable advanced multi-strategy retrieval
            repository=request.repository  # Pass repository for filtering
        )
        logger.info(f"✅ Retrieved {len(retrieved_nodes)} relevant nodes from repository: {request.repository}")
        
        if not retrieved_nodes:
            return {
                "answer": "I couldn't find any relevant information in the codebase for your query. Try asking about specific functions, classes, or architectural components.",
                "sources": []
            }
        
        # Step 2: Process query with advanced query processor
        processor = get_processor()
        answer, metadata = processor.process_query(request.query, retrieved_nodes)
        
        logger.info(f"✅ Query processed - Type: {metadata['query_type']}, Answer length: {metadata['answer_length']}")
        
        # Step 3: Prepare response with enriched metadata
        response_sources = []
        for node in retrieved_nodes[:request.top_k]:  # Limit sources to requested top_k
            response_sources.append({
                'type': node['type'],
                'name': node['name'],
                'summary': node['summary'],
                'score': node['score'],
                'search_type': node.get('search_type', 'unknown'),
                'code_preview': node.get('code', '')[:200] if node.get('code') else '',
                'lineno': node.get('lineno', 0)
            })
        
        return {
            "answer": answer,
            "sources": response_sources
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now, can be extended for two-way communication
            await websocket.send_json({"type": "pong", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.on_event("startup")
async def startup_event():
    """Application startup event handler"""
    logger.info("🚀 Application starting up...")
    logger.info(f"📡 Allowed CORS origins: {ALLOWED_ORIGINS}")
    logger.info(f"🔗 Neo4j URI: {NEO4J_URI}")
    logger.info("✅ Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event handler - cleanup resources"""
    logger.info("🛑 Application shutting down...")
    
    try:
        # Close Neo4j driver
        if driver:
            driver.close()
            logger.info("✅ Neo4j driver closed")
        
        # Close all WebSocket connections
        for connection in manager.active_connections:
            try:
                await connection.close()
            except:
                pass
        logger.info("✅ WebSocket connections closed")
        
        # Clear cache
        cache = get_cache()
        cache.clear()
        logger.info("✅ Cache cleared")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")
    
    logger.info("✅ Application shutdown complete")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
