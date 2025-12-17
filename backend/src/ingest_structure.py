from .create_schema import FileNode, ClassNode, FunctionNode, RepositoryNode
from neomodel import config
from dotenv import load_dotenv
from neo4j import GraphDatabase
import os
import re
from .logger_config import setup_logger

from .extract_structure import extract_codebase_structure

# Load Neo4j credentials from .env
load_dotenv()

# Setup logger
logger = setup_logger(__name__)
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME', 'neo4j')
# Get environment variables with defaults
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', '')
NEO4J_URI = os.getenv('NEO4J_URI', 'neo4j://127.0.0.1:7687')
# Extract host and port from URI for bolt connection
uri_without_protocol = NEO4J_URI.replace('neo4j://', '').replace('neo4j+s://', '').replace('bolt://', '')
if ':' in uri_without_protocol and uri_without_protocol.count(':') >= 1:
    parts = uri_without_protocol.split(':')
    NEO4J_HOST = parts[0]
    # Extract port, handling potential path after port
    port_part = parts[1].split('/')[0] if '/' in parts[1] else parts[1]
    NEO4J_PORT = port_part if port_part else '7687'
else:
    NEO4J_HOST = uri_without_protocol.split('/')[0]
    NEO4J_PORT = '7687'

NODE_TYPE_MAP = {
    "file": FileNode,
    "class": ClassNode,
    "function": FunctionNode,
    "async_function": FunctionNode,
}

# 🔒 Global variable to hold the created DB name
created_db_name = None

class IngestStructure:
    def __init__(self, repo_name: str):
        global created_db_name
        self.repo_name = repo_name
        self.repo_node = None

        # Use default 'neo4j' database (Community Edition doesn't support multiple databases)
        self.db_name = "neo4j"
        created_db_name = self.db_name

        logger.info(f"⚙️ Using Neo4j database: {self.db_name} (repository: {repo_name})")

        # Validate Neo4j credentials
        if not NEO4J_PASSWORD:
            logger.error("❌ NEO4J_PASSWORD is not set!")
            logger.error("💡 Set NEO4J_PASSWORD in backend/.env")
            raise ValueError("NEO4J_PASSWORD is required for database operations")
        
        try:
            # Set DATABASE_URL for neomodel
            neo4j_host = NEO4J_URI.replace('neo4j://', '').replace('neo4j+s://', '').replace('bolt://', '')
            config.DATABASE_URL = f"neo4j://{NEO4J_USERNAME}:{NEO4J_PASSWORD}@{neo4j_host}/{self.db_name}"
            logger.debug(f"🔗 Database URL configured for {neo4j_host}")
        except Exception as e:
            logger.error(f"❌ Failed to configure database URL: {e}")
            logger.error("💡 Check NEO4J_URI format in backend/.env")
            raise


    def create_repository_node(self):
        try:
            self.repo_node = RepositoryNode.nodes.get_or_none(name=self.repo_name)
            if not self.repo_node:
                self.repo_node = RepositoryNode(name=self.repo_name)
                self.repo_node.save()
                logger.info(f"📁 Created repository node: {self.repo_node.name}")
            else:
                logger.info(f"📁 Repository already exists: {self.repo_node.name}")
        except Exception as e:
            logger.error(f"❌ Failed to create or fetch repository node: {e}")

    def ingest(self, structure: dict):
        """Ingest a file structure and all its children into Neo4j.
        Ensures all nodes are connected in a hierarchy under the repository."""
        
        def recursive_create(node_data, parent_node_obj=None, depth=0, is_file_node=False):
            """Recursively create nodes and connect them to their parents.
            
            Args:
                node_data: Dictionary containing node information
                parent_node_obj: Parent node object to connect to
                depth: Current depth in the tree (for logging)
                is_file_node: Whether this is a file node (top-level)
            """
            node_type = node_data.get("type", "unknown").lower()
            NodeClass = NODE_TYPE_MAP.get(node_type)
            
            if not NodeClass:
                logger.warning(f"⚠️ Skipping unknown node type: {node_type} at depth {depth}")
                return None

            parent_identifier = node_data.get("parent")
            children_identifiers = [
                child.get("name") for child in node_data.get("children", [])
                if isinstance(child, dict) and child.get("name")
            ]

            # Create the node
            try:
                node = NodeClass(
                    name=node_data["name"],
                    lineno=node_data["lineno"],
                    code=node_data["code"],
                    parameters=node_data.get("parameters", []),
                    code_embedding=[],
                    summary="N/A",
                    summary_embedding=[],
                    parent_source_identifier=parent_identifier,
                    children_source_identifiers=children_identifiers,
                )
                node.save()
                logger.debug(f"{'  ' * depth}💾 Saved {node_type} node: {node.name}")
            except Exception as e:
                logger.error(f"❌ Error saving {node_type} node {node_data.get('name')}: {e}")
                return None

            # Connect to parent (if exists)
            if parent_node_obj:
                try:
                    parent_node_obj.children.connect(node)
                    logger.info(f"{'  ' * depth}🔗 Connected {parent_node_obj.name} → {node.name}")
                except Exception as e:
                    logger.error(f"❌ Could not connect {parent_node_obj.name} → {node.name}: {e}")
                    # Even if connection fails, continue processing children
            elif not is_file_node and depth > 0:
                # Only warn for non-file nodes at depth > 0 that should have parents
                logger.warning(f"⚠️ Node {node.name} has no parent at depth {depth}")

            # Recursively process children
            children = node_data.get("children", [])
            if children:
                logger.debug(f"{'  ' * depth}📦 Processing {len(children)} children of {node.name}")
                for child in children:
                    if child:
                        recursive_create(child, node, depth + 1, is_file_node=False)

            return node

        file_node_data = {
            "type": "file",
            "name": structure.get("file", "unknown_file.py"),
            "lineno": 0,
            "code": structure.get("code", ""),
            "children": structure.get("children", []),
            "parameters": [],
        }

        # Create the file node and its entire subtree, passing repository as parent
        file_node = recursive_create(file_node_data, parent_node_obj=self.repo_node, depth=0, is_file_node=True)
        
        # Verify file node was created
        if not file_node:
            logger.error(f"❌ File node creation failed for structure: {structure.get('file', 'unknown')}")
            return
        
        logger.info(f"📂 Linked repository → file: {file_node.name}")
    
    def validate_repository_structure(self):
        """Validate that all nodes are connected to the repository.
        Returns statistics about the repository structure."""
        if not self.repo_node:
            logger.error("❌ Cannot validate: repository node not initialized")
            return None
        
        try:
            # Use raw Neo4j driver for validation queries
            logger.debug(f"🔍 Validating repository structure for {self.repo_name}...")
            driver = GraphDatabase.driver(
                f"bolt://{NEO4J_HOST}:{NEO4J_PORT}",
                auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
            )
            
            with driver.session(database=self.db_name) as session:
                # Count nodes connected to repository
                connected_result = session.run("""
                    MATCH (r:RepositoryNode {name: $repo_name})-[:CHILD*]->(n)
                    RETURN count(DISTINCT n) as count
                """, repo_name=self.repo_name)
                connected_count = connected_result.single()["count"]
                
                # Count orphaned nodes (not connected to any repository)
                orphaned_result = session.run("""
                    MATCH (n)
                    WHERE NOT (n:RepositoryNode)
                    AND NOT (:RepositoryNode)-[:CHILD*]->(n)
                    RETURN count(n) as count, labels(n) as labels
                """)
                orphaned_count = sum(record["count"] for record in orphaned_result)
                
                logger.info(f"✅ Repository validation: {connected_count} nodes connected, {orphaned_count} orphaned")
                
                if orphaned_count > 0:
                    logger.warning(f"⚠️  Found {orphaned_count} orphaned nodes not connected to repository!")
                
                return {
                    "connected": connected_count,
                    "orphaned": orphaned_count
                }
            
        except Exception as e:
            error_msg = str(e).lower()
            if "authentication" in error_msg or "unauthorized" in error_msg:
                logger.error("❌ Authentication failed during validation")
                logger.error("💡 Check NEO4J_USERNAME and NEO4J_PASSWORD in backend/.env")
            elif "connection" in error_msg:
                logger.error("❌ Connection failed during validation")
                logger.error("💡 Verify Neo4j is running and accessible")
            else:
                logger.error(f"❌ Error validating repository structure: {e}")
            return None
        finally:
            driver.close()

if __name__ == "__main__":
    # This script is now called from api.py with dynamic loader
    # Example usage:
    # from load_codebase_dynamic import DynamicGithubLoader
    # loader = DynamicGithubLoader(repo="owner/repo", branch="main")
    # documents = loader.load()
    # structures = extract_codebase_structure(documents)
    # ingestor = IngestStructure(repo_name)
    # ingestor.create_repository_node()
    # for structure in structures:
    #     ingestor.ingest(structure)
    
    print("⚠️  This module should be imported and used from api.py")
    print("   It no longer has a standalone main execution mode.")