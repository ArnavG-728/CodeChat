from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain_community.document_loaders import GithubFileLoader
from dotenv import load_dotenv
import os
from logger_config import setup_logger

# Load environment variables
load_dotenv()

# Setup logger
logger = setup_logger(__name__)

TEXT_FILE_EXTENSIONS = (
    # Programming/Scripting Languages & Configuration
    ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".htm", ".css", ".scss", ".less",
    ".json", ".xml", ".xsd", ".xslt", ".yml", ".yaml", ".java", ".c", ".cpp", ".h", ".hpp",
    ".sh", ".bash", ".zsh", ".fish", ".rb", ".php", ".go", ".swift", ".kt", ".kts",
    ".scala", ".rs", ".pl", ".lua", ".r", ".fs", ".fsproj", ".ps1", ".psm1", ".bat",
    ".cmd", ".ino", ".sql", ".vue", ".svelte", ".toml", ".ini", ".cfg", ".conf", ".env",
    ".gitignore", ".dockerignore", ".npmignore", ".editorconfig", ".prettierrc",
    ".eslintrc", ".babelrc", ".browserslistrc", ".gitattributes", ".gitmodules", ".lock",
    # Documentation & Plain Text
    ".txt", ".md", ".markdown", ".rst", ".log", ".nfo", ".readme", ".me", ".asciidoc", ".adoc",
    # Data Files
    ".csv", ".tsv", ".geojson", ".graphql", ".gql", ".proto",
    # Markup & Templating
    ".svg", ".ejs", ".pug", ".jade", ".hbs", ".handlebars", ".liquid", ".njk",
    # Miscellaneous
    ".sub", ".srt", ".vtt", ".url", ".webloc", ".bib", ".tex", ".dxf", ".gcode",
    ".gitconfig", ".vimrc", ".bashrc", ".zshrc", ".profile", ".nanorc"
)


class DynamicGithubLoader:
    """Dynamic GitHub repository loader"""
    
    def __init__(self, repo: str, branch: str = "main", access_token: str = None):
        """
        Initialize the loader
        
        Args:
            repo: Repository in format "owner/repo-name"
            branch: Branch name (default: main)
            access_token: GitHub access token
        """
        # Validate repository format
        if not repo or "/" not in repo:
            logger.error(f"❌ Invalid repository format: {repo}")
            raise ValueError(f"Invalid repository format. Expected 'owner/repo', got '{repo}'")
        
        self.repo = repo
        self.branch = branch
        self.access_token = access_token or os.getenv("ACCESS_TOKEN", "")
        
        if not self.access_token:
            logger.error("❌ GitHub access token not found in environment or parameters")
            raise ValueError("GitHub access token not found. Set ACCESS_TOKEN in .env or pass as parameter")
        
        logger.info(f"🔧 Initializing GitHub loader for {repo} (branch: {branch})")
        
        try:
            self.loader = GithubFileLoader(
                repo=self.repo,
                branch=self.branch,
                access_token=self.access_token,
                github_api_url="https://api.github.com",
                file_filter=lambda filename: filename.endswith(TEXT_FILE_EXTENSIONS)
            )
            logger.info(f"✅ GitHub loader initialized successfully for {repo}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize GitHub loader: {e}", exc_info=True)
            raise ValueError(f"Failed to initialize GitHub loader for {repo}: {str(e)}")
    
    def load(self):
        """Load documents from GitHub"""
        logger.info(f"📥 Loading documents from {self.repo} (branch: {self.branch})")
        
        try:
            docs = self.loader.load()
            
            if not docs:
                logger.warning(f"⚠️ No documents found in {self.repo}")
                return []
            
            logger.info(f"✅ Loaded {len(docs)} documents from {self.repo}")
            return docs
        except Exception as e:
            logger.error(f"❌ Failed to load documents from {self.repo}: {e}", exc_info=True)
            
            # Provide user-friendly error messages
            error_msg = str(e).lower()
            if "404" in error_msg or "not found" in error_msg:
                raise ValueError(f"Repository '{self.repo}' not found. Check the repository name and your access permissions.")
            elif "401" in error_msg or "unauthorized" in error_msg:
                raise ValueError(f"Authentication failed. Check your GitHub access token permissions.")
            elif "403" in error_msg or "forbidden" in error_msg:
                raise ValueError(f"Access forbidden to '{self.repo}'. Check repository visibility and token permissions.")
            elif "timeout" in error_msg:
                raise ValueError(f"Connection timeout while loading '{self.repo}'. Check your network connection.")
            else:
                raise ValueError(f"Failed to load repository '{self.repo}': {str(e)}")
    
    def get_file_list(self):
        """Get list of files in the repository"""
        try:
            logger.debug(f"📋 Getting file list from {self.repo}")
            docs = self.load()
            file_list = [doc.metadata.get("source", "") for doc in docs]
            logger.debug(f"✅ Retrieved {len(file_list)} files")
            return file_list
        except Exception as e:
            logger.error(f"❌ Failed to get file list from {self.repo}: {e}", exc_info=True)
            raise


# For backward compatibility
def create_loader(repo: str, branch: str = "main"):
    """Create a GitHub loader instance"""
    try:
        return DynamicGithubLoader(repo, branch)
    except Exception as e:
        logger.error(f"❌ Failed to create loader for {repo}: {e}", exc_info=True)
        raise
