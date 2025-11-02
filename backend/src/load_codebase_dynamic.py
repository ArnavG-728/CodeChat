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
        self.repo = repo
        self.branch = branch
        self.access_token = access_token or os.getenv("ACCESS_TOKEN")
        
        if not self.access_token:
            logger.error("GitHub access token not found")
            raise ValueError("GitHub access token not found. Set ACCESS_TOKEN in .env")
        
        logger.info(f"Initializing GitHub loader for {repo} (branch: {branch})")
        self.loader = GithubFileLoader(
            repo=self.repo,
            branch=self.branch,
            access_token=self.access_token,
            github_api_url="https://api.github.com",
            file_filter=lambda filename: filename.endswith(TEXT_FILE_EXTENSIONS)
        )
    
    def load(self):
        """Load documents from GitHub"""
        logger.info(f"Loading documents from {self.repo}")
        docs = self.loader.load()
        logger.info(f"✅ Loaded {len(docs)} documents from {self.repo}")
        return docs
    
    def get_file_list(self):
        """Get list of files in the repository"""
        docs = self.load()
        return [doc.metadata.get("source", "") for doc in docs]


# For backward compatibility
def create_loader(repo: str, branch: str = "main"):
    """Create a GitHub loader instance"""
    return DynamicGithubLoader(repo, branch)
