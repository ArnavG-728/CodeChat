from dotenv import load_dotenv
import os
from neomodel import config
from .create_schema import FileNode, ClassNode, FunctionNode
from tqdm import tqdm
import torch
from .unixcoder import UniXcoder
from .logger_config import setup_logger

# Step 1: Load env and configure Neo4j
load_dotenv()

# Setup logger
logger = setup_logger(__name__)
password = os.getenv('NEO4J_PASSWORD', '')
username = os.getenv('NEO4J_USERNAME', 'neo4j')
db_name = os.getenv('NEO4J_DATABASE', 'neo4j')
neo4j_host = os.getenv('NEO4J_URI', 'neo4j://127.0.0.1:7687').replace('neo4j://', '').replace('neo4j+s://', '')
config.DATABASE_URL = f"neo4j://{username}:{password}@{neo4j_host}/{db_name}"

# Module-level variables for lazy initialization
_model = None
_device = None

def get_model():
    """Lazy initialization of UniXcoder model"""
    global _model, _device
    
    if _model is None:
        # Initialize device
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"💻 Using device: {_device}")
        
        # Load UniXcoder model
        logger.info("🧠 Loading UniXcoder model...")
        _model = UniXcoder("microsoft/unixcoder-base")
        _model.to(_device)
        logger.info("✅ UniXcoder model loaded")
    
    return _model, _device

# Step 4: Define embedding function
def encode_with_unixcoder(text):
    model, device = get_model()  # Lazy load model
    tokens_ids = model.tokenize([text], max_length=512, mode="<encoder-only>")
    source_ids = torch.tensor(tokens_ids).to(device)

    with torch.no_grad():
        _, pooled_embedding = model(source_ids)
        embedding = pooled_embedding[0].cpu().numpy()
    return embedding

# Step 5: Embed and save nodes
def embed_and_save(nodes):
    for node in tqdm(nodes):
        try:
            code_text = node.code
            embedding = encode_with_unixcoder(code_text)
            node.code_embedding = embedding.tolist()
            node.save()
            logger.debug(f"✅ Embedded and saved for node: {node.name}")
        except Exception as e:
            logger.error(f"❌ Error embedding node {node.name}: {e}")

# Step 6: Combine everything
def run_all():
    logger.info("⚙️ Processing FileNodes...")
    file_nodes = FileNode.nodes.all()
    logger.info(f"Found {len(file_nodes)} file nodes")
    embed_and_save(file_nodes)

    logger.info("⚙️ Processing ClassNodes...")
    class_nodes = ClassNode.nodes.all()
    logger.info(f"Found {len(class_nodes)} class nodes")
    embed_and_save(class_nodes)

    logger.info("⚙️ Processing FunctionNodes...")
    function_nodes = FunctionNode.nodes.all()
    logger.info(f"Found {len(function_nodes)} function nodes")
    embed_and_save(function_nodes)

    logger.info("✅ Done! All code embeddings created.")

# Allow running directly
if __name__ == "__main__":
    run_all()