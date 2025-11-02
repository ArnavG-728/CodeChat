from dotenv import load_dotenv
import os
from neo4j import GraphDatabase
from logger_config import setup_logger

load_dotenv()

# Setup logger
logger = setup_logger(__name__)

password = os.getenv('password')
db_name = os.getenv('NEO4J_DATABASE', 'neo4j')
neo4j_uri = os.getenv('NEO4J_CONNECTION_URL', 'neo4j://127.0.0.1:7687')

def create_vector_indexes(dimension=768):
    """Create vector indexes for code and summary embeddings after all embeddings are generated."""
    driver = GraphDatabase.driver(neo4j_uri, auth=("neo4j", password))
    
    with driver.session(database=db_name) as session:
        index_queries = [
            # Code embedding indexes
            f"""
            CREATE VECTOR INDEX fileCodeEmbeddingIndex IF NOT EXISTS
            FOR (n:FileNode)
            ON (n.code_embedding)
            OPTIONS {{
                indexConfig: {{
                    `vector.dimensions`: {dimension},
                    `vector.similarity_function`: 'cosine'
                }}
            }}
            """,
            f"""
            CREATE VECTOR INDEX classCodeEmbeddingIndex IF NOT EXISTS
            FOR (n:ClassNode)
            ON (n.code_embedding)
            OPTIONS {{
                indexConfig: {{
                    `vector.dimensions`: {dimension},
                    `vector.similarity_function`: 'cosine'
                }}
            }}
            """,
            f"""
            CREATE VECTOR INDEX functionCodeEmbeddingIndex IF NOT EXISTS
            FOR (n:FunctionNode)
            ON (n.code_embedding)
            OPTIONS {{
                indexConfig: {{
                    `vector.dimensions`: {dimension},
                    `vector.similarity_function`: 'cosine'
                }}
            }}
            """,
            # Summary embedding indexes
            f"""
            CREATE VECTOR INDEX fileSummaryEmbeddingIndex IF NOT EXISTS
            FOR (n:FileNode)
            ON (n.summary_embedding)
            OPTIONS {{
                indexConfig: {{
                    `vector.dimensions`: {dimension},
                    `vector.similarity_function`: 'cosine'
                }}
            }}
            """,
            f"""
            CREATE VECTOR INDEX classSummaryEmbeddingIndex IF NOT EXISTS
            FOR (n:ClassNode)
            ON (n.summary_embedding)
            OPTIONS {{
                indexConfig: {{
                    `vector.dimensions`: {dimension},
                    `vector.similarity_function`: 'cosine'
                }}
            }}
            """,
            f"""
            CREATE VECTOR INDEX functionSummaryEmbeddingIndex IF NOT EXISTS
            FOR (n:FunctionNode)
            ON (n.summary_embedding)
            OPTIONS {{
                indexConfig: {{
                    `vector.dimensions`: {dimension},
                    `vector.similarity_function`: 'cosine'
                }}
            }}
            """
        ]
        
        for i, query in enumerate(index_queries, 1):
            try:
                session.run(query)
                logger.info(f"✅ Successfully created vector index {i}/6")
            except Exception as e:
                logger.error(f"❌ Failed to create vector index {i}/6: {e}")
    
    driver.close()
    logger.info("✅ All vector indexes created!")

if __name__ == "__main__":
    logger.info("🔧 Creating vector indexes...")
    create_vector_indexes(dimension=768)
