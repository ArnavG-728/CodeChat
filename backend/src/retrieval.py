# retrieval.py - Advanced Multi-Strategy Code Retrieval System
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from .logger_config import setup_logger
from typing import List, Dict, Any
import re

# Setup logger
logger = setup_logger(__name__)

# Load environment variables
load_dotenv()

# Module-level variables (lazy initialized)
_embedding_model = None
_driver = None

# Get database configuration
db_name = os.getenv('NEO4J_DATABASE', 'neo4j')
neo4j_uri = os.getenv('NEO4J_URI', 'neo4j://127.0.0.1:7687')
neo4j_username = os.getenv('NEO4J_USERNAME', 'neo4j')
neo4j_password = os.getenv('NEO4J_PASSWORD', '')


def get_embedding_model():
    """Lazy initialization of embedding model"""
    global _embedding_model
    
    if _embedding_model is None:
        try:
            google_api_key = os.getenv("GOOGLE_API_KEY", "")
            if not google_api_key:
                logger.error("❌ GOOGLE_API_KEY not found in environment variables")
                raise ValueError("GOOGLE_API_KEY is required for embedding model initialization")
            
            logger.info("🔧 Initializing Google Generative AI Embeddings...")
            _embedding_model = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=google_api_key,
            )
            logger.info("✅ Embedding model initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize embedding model: {e}", exc_info=True)
            raise
    
    return _embedding_model


def get_driver():
    """Lazy initialization of Neo4j driver with comprehensive error handling"""
    global _driver
    
    if _driver is None:
        try:
            # Validate password
            if not neo4j_password:
                logger.error("❌ NEO4J_PASSWORD not found in environment variables")
                logger.error("💡 Set NEO4J_PASSWORD in your backend/.env file")
                raise ValueError("Neo4j password is required. Set NEO4J_PASSWORD in .env")
            
            logger.info(f"🔧 Connecting to Neo4j at {neo4j_uri}...")
            logger.debug(f"👤 Username: {neo4j_username}")
            logger.debug(f"🗄️  Database: {db_name}")
            
            _driver = GraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_username, neo4j_password)
            )
            
            # Test connection
            logger.debug("🔍 Testing connection...")
            with _driver.session(database=db_name) as session:
                session.run("RETURN 1").single()
            logger.info(f"✅ Neo4j driver initialized successfully (database: {db_name})")
            
        except ValueError as ve:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            error_msg = str(e).lower()
            
            # Authentication errors
            if "authentication" in error_msg or "unauthorized" in error_msg:
                logger.error("❌ Neo4j Authentication Failed!")
                logger.error(f"   URI: {neo4j_uri}")
                logger.error(f"   Username: {neo4j_username}")
                logger.error(f"   Error: {e}")
                logger.error("")
                logger.error("💡 Fix: Check NEO4J_USERNAME and NEO4J_PASSWORD in backend/.env")
                raise RuntimeError("Neo4j authentication failed. Verify credentials in .env") from e
            
            # Connection errors
            elif "connection" in error_msg or "unable to" in error_msg:
                logger.error("❌ Cannot connect to Neo4j!")
                logger.error(f"   URI: {neo4j_uri}")
                logger.error(f"   Error: {e}")
                logger.error("")
                logger.error("💡 Fixes:")
                logger.error("   - Verify NEO4J_URI in backend/.env")
                logger.error("   - Ensure Neo4j is running (local) or URI is correct (Aura)")
                raise RuntimeError(f"Cannot connect to Neo4j at {neo4j_uri}") from e
            
            # Database not found
            elif "database" in error_msg and "not found" in error_msg:
                logger.error(f"❌ Database '{db_name}' not found!")
                logger.error("💡 Fix: Check NEO4J_DATABASE in backend/.env or use default 'neo4j'")
                raise RuntimeError(f"Database '{db_name}' does not exist") from e
            
            # Generic error
            else:
                logger.error(f"❌ Failed to initialize Neo4j driver: {e}", exc_info=True)
                raise RuntimeError(f"Neo4j initialization failed: {e}") from e
    
    return _driver


def close_connections():
    """Close all connections gracefully"""
    global _driver
    
    if _driver is not None:
        try:
            _driver.close()
            logger.info("✅ Neo4j driver closed successfully")
        except Exception as e:
            logger.warning(f"⚠️ Error closing Neo4j driver: {e}")
        finally:
            _driver = None

# List of vector indexes to search
SUMMARY_INDEXES = [
    ('fileSummaryEmbeddingIndex', 'FileNode'),
    ('classSummaryEmbeddingIndex', 'ClassNode'),
    ('functionSummaryEmbeddingIndex', 'FunctionNode')
]

CODE_INDEXES = [
    ('fileCodeEmbeddingIndex', 'FileNode'),
    ('classCodeEmbeddingIndex', 'ClassNode'),
    ('functionCodeEmbeddingIndex', 'FunctionNode')
]


def retrieve_semantic_results(query: str, top_k: int = 10, use_code_index: bool = False, repository: str = None) -> List[Dict[str, Any]]:
    """
    Retrieve results using semantic similarity search on embeddings.
    Can search either summary or code embeddings.
    Optionally filters by repository.
    """
    # Input validation
    if not query or not query.strip():
        logger.warning("⚠️ Empty query provided to retrieve_semantic_results")
        return []
    
    if top_k < 1 or top_k > 50:
        logger.warning(f"⚠️ Invalid top_k value: {top_k}, using default 10")
        top_k = 10
    
    logger.debug(f"🔍 Semantic search: {query[:50]}... (use_code_index={use_code_index}, repo={repository})")
    
    try:
        # Embed the query
        logger.debug("📊 Generating query embedding...")
        embedding_model = get_embedding_model()  # Lazy initialization
        embedding = embedding_model.embed_query(query)
        logger.debug(f"✅ Generated embedding vector of length {len(embedding)}")
    except Exception as e:
        logger.error(f"❌ Failed to generate embedding for query: {e}", exc_info=True)
        return []

    all_results = []
    indexes = CODE_INDEXES if use_code_index else SUMMARY_INDEXES

    try:
        driver = get_driver()  # Lazy initialization
        with driver.session(database=db_name) as session:
            for index_name, node_type in indexes:
                try:
                    if repository:
                        # Filter by repository
                        cypher = f"""
                            CALL db.index.vector.queryNodes('{index_name}', {top_k * 2}, $embedding)
                            YIELD node, score
                            WHERE (:RepositoryNode {{name: $repo_name}})-[:CHILD*]->(node)
                            RETURN 
                                node.name AS name, 
                                node.summary AS summary, 
                                node.code AS code,
                                node.lineno AS lineno,
                                score
                            ORDER BY score DESC
                            LIMIT {top_k}
                        """
                        res = session.run(cypher, embedding=embedding, repo_name=repository)
                    else:
                        # Original query without repository filter
                        cypher = f"""
                            CALL db.index.vector.queryNodes('{index_name}', {top_k}, $embedding)
                            YIELD node, score
                            RETURN 
                                node.name AS name, 
                                node.summary AS summary, 
                                node.code AS code,
                                node.lineno AS lineno,
                                score
                            ORDER BY score DESC
                        """
                        res = session.run(cypher, embedding=embedding)
                    
                    count = 0
                    for record in res:
                        all_results.append({
                            'type': node_type,
                            'name': record['name'],
                            'summary': record.get('summary') or "",
                            'code': record.get('code') or "",
                            'lineno': record.get('lineno') or 0,
                            'score': record['score'],
                            'search_type': 'code' if use_code_index else 'summary'
                        })
                        count += 1
                    logger.debug(f"✅ Found {count} results from {index_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Error querying {index_name}: {e}")
                    # Continue with other indexes instead of failing completely
                    continue
    except Exception as e:
        logger.error(f"❌ Neo4j session error in retrieve_semantic_results: {e}", exc_info=True)
        return []

    all_results.sort(key=lambda x: x['score'], reverse=True)
    logger.info(f"🎯 Retrieved {len(all_results[:top_k])} semantic results")
    return all_results[:top_k]


def retrieve_graph_based_results(query: str, top_k: int = 10, repository: str = None) -> List[Dict[str, Any]]:
    """
    Retrieve results using graph-based search (keyword matching + relationships).
    Finds nodes by name/summary keywords and includes related nodes.
    Optionally filters by repository.
    """
    logger.debug(f"📊 Graph-based search: {query[:50]}... (repo={repository})")
    
    # Extract keywords from query
    keywords = query.lower().split()
    keywords = [kw for kw in keywords if len(kw) > 2]  # Filter short words
    
    all_results = []
    
    driver = get_driver()  # Lazy initialization
    with driver.session(database=db_name) as session:
        try:
            if repository:
                # Search with repository filter
                cypher = """
                    MATCH (r:RepositoryNode {name: $repo_name})-[:CHILD*]->(n:FileNode|ClassNode|FunctionNode)
                    WHERE 
                        ANY(kw IN $keywords WHERE toLower(n.name) CONTAINS kw) OR
                        ANY(kw IN $keywords WHERE toLower(n.summary) CONTAINS kw)
                    RETURN 
                        n.name AS name,
                        n.summary AS summary,
                        n.code AS code,
                        n.lineno AS lineno,
                        labels(n)[0] AS type
                    LIMIT $limit
                """
                res = session.run(cypher, keywords=keywords, repo_name=repository, limit=top_k * 2)
            else:
                # Original search without repository filter
                cypher = """
                    MATCH (n:FileNode|ClassNode|FunctionNode)
                    WHERE 
                        ANY(kw IN $keywords WHERE toLower(n.name) CONTAINS kw) OR
                        ANY(kw IN $keywords WHERE toLower(n.summary) CONTAINS kw)
                    RETURN 
                        n.name AS name,
                        n.summary AS summary,
                        n.code AS code,
                        n.lineno AS lineno,
                        labels(n)[0] AS type
                    LIMIT $limit
                """
                res = session.run(cypher, keywords=keywords, limit=top_k * 2)
            
            for record in res:
                # Calculate relevance score based on keyword matches
                name = record['name'].lower()
                summary = record['summary'].lower()
                matches = sum(1 for kw in keywords if kw in name or kw in summary)
                score = matches / len(keywords) if keywords else 0
                
                all_results.append({
                    'type': record['type'],
                    'name': record['name'],
                    'summary': record['summary'],
                    'code': record['code'],
                    'lineno': record['lineno'],
                    'score': score,
                    'search_type': 'graph'
                })
            
            logger.debug(f"Found {len(all_results)} results from graph search")
        except Exception as e:
            logger.warning(f"⚠️ Error in graph-based search: {e}")
    
    all_results.sort(key=lambda x: x['score'], reverse=True)
    return all_results[:top_k]


def retrieve_related_nodes(node_name: str, node_type: str, depth: int = 2, repository: str = None) -> List[Dict[str, Any]]:
    """
    Retrieve nodes related to a given node through the graph structure.
    Includes parent, children, and siblings.
    Optionally filters by repository.
    """
    logger.debug(f"🔗 Retrieving related nodes for {node_type}: {node_name} (repo={repository})")
    
    related_results = []
    
    driver = get_driver()  # Lazy initialization
    with driver.session(database=db_name) as session:
        try:
            # Get child nodes (the graph uses CHILD relationships, not PARENT)
            if repository:
                cypher_child = """
                    MATCH (r:RepositoryNode {name: $repo_name})-[:CHILD*]->(n:FileNode|ClassNode|FunctionNode {name: $name})-[:CHILD*1..2]->(child)
                    RETURN 
                        child.name AS name,
                        child.summary AS summary,
                        child.code AS code,
                        child.lineno AS lineno,
                        labels(child)[0] AS type,
                        'child' AS relation
                """
                res = session.run(cypher_child, name=node_name, repo_name=repository)
            else:
                cypher_child = """
                    MATCH (n:FileNode|ClassNode|FunctionNode {name: $name})-[:CHILD*1..2]->(child)
                    RETURN 
                        child.name AS name,
                        child.summary AS summary,
                        child.code AS code,
                        child.lineno AS lineno,
                        labels(child)[0] AS type,
                        'child' AS relation
                """
                res = session.run(cypher_child, name=node_name)
            
            for record in res:
                related_results.append({
                    'type': record['type'],
                    'name': record['name'],
                    'summary': record['summary'],
                    'code': record['code'],
                    'lineno': record['lineno'],
                    'score': 0.8,  # Child nodes get high score
                    'search_type': 'related',
                    'relation': record['relation']
                })
            
            # Get parent nodes (reverse relationship - nodes that have this node as a child)
            if repository:
                cypher_parents = """
                    MATCH (r:RepositoryNode {name: $repo_name})-[:CHILD*]->(parent:FileNode|ClassNode|FunctionNode)-[:CHILD*1..2]->(n:FileNode|ClassNode|FunctionNode {name: $name})
                    RETURN 
                        parent.name AS name,
                        parent.summary AS summary,
                        parent.code AS code,
                        parent.lineno AS lineno,
                        labels(parent)[0] AS type,
                        'parent' AS relation
                """
                res = session.run(cypher_parents, name=node_name, repo_name=repository)
            else:
                cypher_parents = """
                    MATCH (parent:FileNode|ClassNode|FunctionNode)-[:CHILD*1..2]->(n:FileNode|ClassNode|FunctionNode {name: $name})
                    RETURN 
                        parent.name AS name,
                        parent.summary AS summary,
                        parent.code AS code,
                        parent.lineno AS lineno,
                        labels(parent)[0] AS type,
                        'parent' AS relation
                """
                res = session.run(cypher_parents, name=node_name)
            for record in res:
                related_results.append({
                    'type': record['type'],
                    'name': record['name'],
                    'summary': record['summary'],
                    'code': record['code'],
                    'lineno': record['lineno'],
                    'score': 0.7,  # Parent nodes get slightly lower score
                    'search_type': 'related',
                    'relation': record['relation']
                })
            
            logger.debug(f"Found {len(related_results)} related nodes")
        except Exception as e:
            logger.warning(f"⚠️ Error retrieving related nodes: {e}")
    
    return related_results


def retrieve_top_k(query: str, top_k: int = 10, use_multi_strategy: bool = True, repository: str = None) -> List[Dict[str, Any]]:
    """
    Advanced multi-strategy retrieval system.
    Combines semantic search, graph-based search, and code search for comprehensive results.
    
    Args:
        query: User query string
        top_k: Number of results to return
        use_multi_strategy: If True, uses multiple search strategies; if False, only semantic
        repository: Optional repository name to filter results
    
    Returns:
        List of top-k results with combined scores
    """
    logger.info(f"🔍 Retrieving top {top_k} results for query: {query[:50]}... (repo={repository})")
    
    if not use_multi_strategy:
        # Legacy mode: single semantic search
        results = retrieve_semantic_results(query, top_k=top_k, repository=repository)
        logger.info(f"✅ Returning {len(results)} results (semantic only)")
        return results
    
    # Multi-strategy approach
    all_results = {}
    
    # Strategy 1: Semantic search on summaries (primary)
    logger.debug("📌 Strategy 1: Semantic search on summaries")
    semantic_results = retrieve_semantic_results(query, top_k=top_k, use_code_index=False, repository=repository)
    for result in semantic_results:
        key = (result['type'], result['name'])
        all_results[key] = result
        all_results[key]['score'] = result['score'] * 1.0  # Weight: 100%
    
    # Strategy 2: Graph-based search (keyword matching)
    logger.debug("📌 Strategy 2: Graph-based keyword search")
    graph_results = retrieve_graph_based_results(query, top_k=top_k, repository=repository)
    for result in graph_results:
        key = (result['type'], result['name'])
        if key in all_results:
            # Boost score if found in multiple strategies
            all_results[key]['score'] = min(1.0, all_results[key]['score'] + result['score'] * 0.3)
            all_results[key]['search_type'] = 'hybrid'
        else:
            all_results[key] = result
            all_results[key]['score'] = result['score'] * 0.6  # Weight: 60%
    
    # Strategy 3: Code embedding search (for technical queries)
    logger.debug("📌 Strategy 3: Code embedding search")
    code_results = retrieve_semantic_results(query, top_k=top_k // 2, use_code_index=True, repository=repository)
    for result in code_results:
        key = (result['type'], result['name'])
        if key in all_results:
            all_results[key]['score'] = min(1.0, all_results[key]['score'] + result['score'] * 0.2)
            all_results[key]['search_type'] = 'hybrid'
        else:
            all_results[key] = result
            all_results[key]['score'] = result['score'] * 0.4  # Weight: 40%
    
    # Convert to list and sort
    final_results = list(all_results.values())
    final_results.sort(key=lambda x: x['score'], reverse=True)
    final_results = final_results[:top_k]
    
    # Add related nodes for top results
    logger.debug("📌 Strategy 4: Enriching with related nodes")
    enriched_results = []
    for i, result in enumerate(final_results):
        enriched_results.append(result)
        if i < 3:  # Only for top 3 results
            related = retrieve_related_nodes(result['name'], result['type'], depth=1, repository=repository)
            enriched_results.extend(related[:2])  # Add top 2 related nodes
    
    # Final deduplication and sorting
    seen = set()
    deduplicated = []
    for result in enriched_results:
        key = (result['type'], result['name'])
        if key not in seen:
            seen.add(key)
            deduplicated.append(result)
    
    deduplicated.sort(key=lambda x: x['score'], reverse=True)
    final_results = deduplicated[:top_k]
    
    logger.info(f"✅ Returning {len(final_results)} results (multi-strategy)")
    return final_results
