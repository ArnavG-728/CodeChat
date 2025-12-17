from dotenv import load_dotenv
import os
from neomodel import config
from create_schema import FileNode, ClassNode, FunctionNode
from tqdm import tqdm
from langchain_google_genai import ChatGoogleGenerativeAI,GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from logger_config import setup_logger

# Setup logger
logger = setup_logger(__name__)

def main():
    load_dotenv()
    logger.info("🚀 Starting summary generation")
    password = os.getenv('password', '')
    db_name = os.getenv("NEO4J_DATABASE", "neo4j")  # Fallback to "neo4j" if not set
    neo4j_host = os.getenv('NEO4J_CONNECTION_URL', 'neo4j://127.0.0.1:7687').replace('neo4j://', '')
    config.DATABASE_URL = f"neo4j://neo4j:{password}@{neo4j_host}/{db_name}"
    google_api_key = os.getenv("GOOGLE_API_KEY", "")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

    logger.info("🤖 Initializing Gemini LLM...")
    llm = ChatGoogleGenerativeAI(
        model=gemini_model,
        temperature=0.3,
        google_api_key=google_api_key
    )
    logger.info("🔗 Initializing embedding model...")
    embedding_model = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=google_api_key
    )
    logger.info("✅ Models initialized")

    prompt = ChatPromptTemplate.from_template(
        """You are an expert Python developer and technical writer. You understand everything clearly and give a concise very well explained summary of the code provided.
        Given the following code snippet, write a **descriptive, clear, and non-redundant summary** . 
        Focus on the main purpose, functionality, and any important details that would help someone understand the code without needing to read it in detail.

        Code:
        ```python
        {code}
        ```
        "Docstring summary:"
        """
        )

    #  Follow these instructions carefully:
    #     - Summarize each line or logical block.
    #     - Explain *why* each part exists or what it accomplishes, not just what it does.
    #     - Highlight any function definitions, class definitions, loops, and conditionals with clear purpose.
    #     - Avoid repeating similar phrases.
    #     Now with the above instructions correctly followed, output **only** the below:
    #         Conclude with a concise high-level description of what the entire code does.


    def generate_and_save_summary(nodes, node_type):
        logger.info(f"📝 Processing {node_type}...")
        logger.info(f"Found {len(nodes)} nodes to summarize")
        for node in tqdm(nodes):
            try:
                code_text = node.code
                final_prompt = prompt.format(code=code_text)
                summary = llm.invoke(final_prompt).content

                node.summary = summary

                # Generate embedding
                embedding = embedding_model.embed_query(summary)
                node.summary_embedding = embedding  # make sure you have an ArrayProperty in your model

                node.save()
                logger.debug(f"✅ Saved summary for node: {node.name}")
            except Exception as e:
                logger.error(f"❌ Error summarizing node {node.name}: {e}")

    generate_and_save_summary(FileNode.nodes.all(), "FileNodes")
    generate_and_save_summary(ClassNode.nodes.all(), "ClassNodes")
    generate_and_save_summary(FunctionNode.nodes.all(), "FunctionNodes")

    logger.info("✅ Done! All summaries created and saved.")

if __name__ == "__main__":
    main()