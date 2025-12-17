# query_processor.py - Advanced Query Processing and Prompt Engineering
"""
Comprehensive query processing system for the CodeChat chatbot.
Handles query understanding, context building, and LLM prompt engineering.
"""

import os
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from logger_config import setup_logger
import re

load_dotenv()
logger = setup_logger(__name__)

# Initialize LLM with configurable model
llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
    google_api_key=os.getenv("GOOGLE_API_KEY", ""),
    temperature=0.3,  # Slightly higher for better explanations
)


class QueryAnalyzer:
    """Analyzes user queries to understand intent and extract key information."""
    
    QUERY_TYPES = {
        'overview': ['overview', 'summary', 'what is', 'explain', 'describe', 'tell me about'],
        'functionality': ['function', 'how does', 'what does', 'purpose', 'does it'],
        'architecture': ['architecture', 'structure', 'design', 'how is it organized', 'components'],
        'implementation': ['implement', 'how to', 'example', 'usage', 'code'],
        'relationships': ['relationship', 'related', 'connects', 'calls', 'depends'],
        'comparison': ['difference', 'compare', 'vs', 'versus', 'similar'],
        'debugging': ['bug', 'error', 'issue', 'problem', 'fix', 'debug'],
        'technical': ['flask', 'django', 'react', 'node', 'python', 'javascript', 'typescript', 'sql', 'nosql', 'rest', 'graphql', 'api', 'database', 'framework', 'library', 'package', 'module', 'protocol', 'architecture pattern', 'design pattern'],
    }
    
    # Technical frameworks and libraries that should trigger technical explanations
    TECHNICAL_KEYWORDS = {
        'flask', 'django', 'fastapi', 'express', 'react', 'vue', 'angular', 'svelte',
        'node', 'python', 'javascript', 'typescript', 'java', 'golang', 'rust', 'c++',
        'sql', 'nosql', 'mongodb', 'postgresql', 'mysql', 'redis', 'elasticsearch',
        'rest', 'graphql', 'grpc', 'websocket', 'http', 'https', 'tcp', 'udp',
        'docker', 'kubernetes', 'aws', 'gcp', 'azure', 'ci/cd', 'jenkins', 'github',
        'git', 'npm', 'pip', 'maven', 'gradle', 'webpack', 'babel', 'eslint',
        'testing', 'jest', 'pytest', 'unittest', 'mocha', 'chai',
        'authentication', 'oauth', 'jwt', 'session', 'cookie',
        'caching', 'redis', 'memcached', 'cdn', 'cache',
        'microservices', 'monolith', 'serverless', 'lambda', 'function',
        'machine learning', 'ai', 'neural network', 'deep learning', 'nlp',
    }
    
    # Greetings and off-topic patterns
    GREETINGS = {
        'hello', 'hi', 'hey', 'greetings', 'howdy', 'what\'s up', 'yo', 'sup',
        'good morning', 'good afternoon', 'good evening', 'good night'
    }
    
    FAREWELLS = {
        'bye', 'goodbye', 'see you', 'farewell', 'take care', 'cya', 'later',
        'adios', 'cheerio', 'catch you', 'ttyl', 'gotta go', 'have to go'
    }
    
    OFF_TOPIC_PATTERNS = [
        'how are you', 'how are u', 'how\'s it going', 'what\'s up',
        'tell me a joke', 'joke', 'funny', 'meme',
        'weather', 'time', 'date', 'what time is it',
        'who are you', 'what are you', 'your name', 'who made you',
        'thank you', 'thanks', 'thank', 'appreciate',
        'sorry', 'my bad', 'oops', 'excuse me',
        'help', 'assist', 'support', 'can you help',
        'love', 'hate', 'like', 'dislike', 'feel',
        'music', 'movie', 'game', 'sport', 'food', 'recipe',
        'politics', 'religion', 'opinion', 'believe',
    ]
    
    def __init__(self, query: str):
        self.query = query
        self.query_lower = query.lower().strip()
        self.is_greeting = self._detect_greeting()
        self.is_farewell = self._detect_farewell()
        self.is_off_topic = self._detect_off_topic()
        self.query_type = self._detect_query_type()
        self.keywords = self._extract_keywords()
        self.is_multi_part = self._detect_multi_part()
    
    def _detect_greeting(self) -> bool:
        """Detect if query is a greeting"""
        # Check exact matches
        if self.query_lower in self.GREETINGS:
            return True
        # Check if query starts with greeting
        for greeting in self.GREETINGS:
            if self.query_lower.startswith(greeting):
                return True
        return False
    
    def _detect_farewell(self) -> bool:
        """Detect if query is a farewell"""
        # Check exact matches
        if self.query_lower in self.FAREWELLS:
            return True
        # Check if query starts with farewell
        for farewell in self.FAREWELLS:
            if self.query_lower.startswith(farewell):
                return True
        return False
    
    def _detect_off_topic(self) -> bool:
        """Detect if query is off-topic (not code-related)"""
        # If it's a greeting or farewell, it's off-topic
        if self.is_greeting or self.is_farewell:
            return True
        
        # Check for off-topic patterns
        for pattern in self.OFF_TOPIC_PATTERNS:
            if pattern in self.query_lower:
                return True
        
        return False
    
    def _detect_query_type(self) -> str:
        """Detect the type of query (overview, functionality, etc.)"""
        # First check if it's a technical question (general knowledge question)
        for keyword in self.TECHNICAL_KEYWORDS:
            if keyword in self.query_lower:
                return 'technical'
        
        # Then check for code-specific query types
        for qtype, keywords in self.QUERY_TYPES.items():
            if qtype != 'technical' and any(kw in self.query_lower for kw in keywords):
                return qtype
        return 'general'
    
    def _extract_keywords(self) -> List[str]:
        """Extract important keywords from query"""
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'is', 'are', 'in', 'on', 'at', 'to', 'for', 'of', 'this', 'that'}
        words = self.query_lower.split()
        keywords = [w.strip('?,!.;:') for w in words if w.lower() not in stop_words and len(w) > 2]
        return keywords
    
    def _detect_multi_part(self) -> bool:
        """Detect if query has multiple parts (e.g., "What is X and how does Y work?")"""
        return any(sep in self.query_lower for sep in [' and ', ' also ', ' plus ', ' additionally '])


class ContextBuilder:
    """Builds comprehensive context from retrieved nodes."""
    
    def __init__(self, retrieved_nodes: List[Dict[str, Any]]):
        self.nodes = retrieved_nodes
        self.organized_nodes = self._organize_nodes()
    
    def _organize_nodes(self) -> Dict[str, List[Dict]]:
        """Organize nodes by type for better context building"""
        organized = {
            'FileNode': [],
            'ClassNode': [],
            'FunctionNode': [],
            'related': []
        }
        
        for node in self.nodes:
            node_type = node.get('type', 'unknown')
            if node.get('search_type') == 'related':
                organized['related'].append(node)
            elif node_type in organized:
                organized[node_type].append(node)
        
        return organized
    
    def build_context_string(self, include_code: bool = False, max_length: int = 3000) -> str:
        """
        Build a formatted context string for the LLM.
        
        Args:
            include_code: Whether to include full code snippets
            max_length: Maximum length of context string
        
        Returns:
            Formatted context string
        """
        context_parts = []
        current_length = 0
        
        # Add organized context by type
        for node_type in ['FileNode', 'ClassNode', 'FunctionNode']:
            nodes = self.organized_nodes.get(node_type, [])
            if not nodes:
                continue
            
            type_label = node_type.replace('Node', '')
            context_parts.append(f"\n## {type_label}s ({len(nodes)} found):")
            
            for i, node in enumerate(nodes, 1):
                node_info = self._format_node(node, include_code)
                context_parts.append(node_info)
                current_length += len(node_info)
                
                if current_length > max_length:
                    context_parts.append(f"\n... ({len(nodes) - i} more {type_label}s not shown due to length)")
                    break
        
        # Add related nodes if space allows
        related = self.organized_nodes.get('related', [])
        if related and current_length < max_length * 0.8:
            context_parts.append(f"\n## Related Components ({len(related)} found):")
            for node in related[:3]:  # Limit related nodes
                node_info = self._format_node(node, include_code=False)
                context_parts.append(node_info)
        
        return "".join(context_parts)
    
    def _format_node(self, node: Dict[str, Any], include_code: bool = False) -> str:
        """Format a single node for display"""
        node_type = node.get('type', 'Unknown')
        name = node.get('name', 'Unknown')
        summary = node.get('summary', 'No summary available')
        score = node.get('score', 0)
        search_type = node.get('search_type', 'unknown')
        relation = node.get('relation', '')
        
        formatted = f"\n[{node_type}] **{name}**"
        if relation:
            formatted += f" ({relation})"
        formatted += f"\n  Summary: {summary[:200]}..."
        formatted += f"\n  Relevance: {score:.1%} ({search_type})"
        
        if include_code and node.get('code'):
            code = node.get('code', '')
            if len(code) > 500:
                code = code[:500] + "\n  ..."
            formatted += f"\n  Code:\n  {code}"
        
        return formatted
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get statistics about the retrieved nodes"""
        return {
            'total_nodes': len(self.nodes),
            'file_nodes': len(self.organized_nodes['FileNode']),
            'class_nodes': len(self.organized_nodes['ClassNode']),
            'function_nodes': len(self.organized_nodes['FunctionNode']),
            'related_nodes': len(self.organized_nodes['related']),
            'avg_score': sum(n.get('score', 0) for n in self.nodes) / len(self.nodes) if self.nodes else 0
        }


class PromptEngineer:
    """Generates optimized prompts for different query types."""
    
    @staticmethod
    def build_system_prompt(query_type: str, context: str, stats: Dict[str, Any]) -> SystemMessage:
        """
        Build a system prompt tailored to the query type.
        
        Args:
            query_type: Type of query (overview, functionality, etc.)
            context: Formatted context string
            stats: Statistics about retrieved nodes
        
        Returns:
            SystemMessage for the LLM
        """
        
        base_instructions = """You are an expert AI code assistant with deep knowledge of software architecture, design patterns, implementation details, and modern technologies. Your role is to provide comprehensive, accurate, and helpful explanations of code repositories and technical concepts.

CORE PRINCIPLES:
1. **Accuracy**: Use information from the provided context when available. For general technical questions, provide accurate information based on your knowledge.
2. **Clarity**: Explain complex concepts in simple, understandable terms suitable for developers.
3. **Completeness**: Provide thorough answers that address all aspects of the question.
4. **Citations**: Always cite the source nodes (e.g., "FunctionNode: function_name") when referencing specific code from the codebase.
5. **Structure**: Organize answers logically with clear sections and bullet points.
6. **Technical Depth**: Include technical details, parameters, return types, dependencies, and practical examples where relevant.
7. **Context-Aware**: When answering technical questions, relate them to the provided codebase when applicable.

CONTEXT STATISTICS:
- Total nodes analyzed: {total_nodes}
- Files: {file_nodes} | Classes: {class_nodes} | Functions: {function_nodes}
- Average relevance score: {avg_score:.1%}

PROVIDED CODEBASE CONTEXT:
{context}

---"""
        
        # Query-type specific instructions
        type_instructions = {
            'overview': """
TASK: Provide a comprehensive overview of the codebase.
APPROACH:
1. Start with the main purpose and high-level architecture
2. Describe the key components and their roles
3. Explain how components interact
4. Summarize the overall design philosophy
TONE: Informative and structured""",
            
            'functionality': """
TASK: Explain what specific functions or components do.
APPROACH:
1. Describe the primary purpose
2. Explain inputs, outputs, and parameters
3. Detail the step-by-step process
4. Mention any important side effects or dependencies
TONE: Technical and precise""",
            
            'architecture': """
TASK: Explain the architectural design and structure.
APPROACH:
1. Describe the overall architecture pattern
2. Explain the organization of components
3. Detail the relationships and dependencies
4. Discuss design decisions and trade-offs
TONE: Architectural and strategic""",
            
            'implementation': """
TASK: Provide implementation details and examples.
APPROACH:
1. Show relevant code snippets
2. Explain the implementation approach
3. Provide usage examples
4. Highlight important implementation details
TONE: Practical and code-focused""",
            
            'relationships': """
TASK: Explain how components relate to each other.
APPROACH:
1. Identify direct relationships (calls, inheritance, composition)
2. Explain the purpose of each relationship
3. Describe data flow between components
4. Mention any circular dependencies or important patterns
TONE: Relational and structural""",
            
            'debugging': """
TASK: Help identify and understand issues or bugs.
APPROACH:
1. Analyze the problematic code
2. Identify potential issues
3. Suggest debugging approaches
4. Recommend fixes or improvements
TONE: Analytical and solution-oriented""",
            
            'technical': """
TASK: Provide comprehensive technical explanation about frameworks, libraries, or technologies.
APPROACH:
1. Explain what the technology is and its primary purpose
2. Describe key features and capabilities
3. Explain how it relates to the codebase (if applicable)
4. Provide practical use cases and examples
5. Mention advantages and when to use it
6. If relevant, show how it's used in the provided codebase
TONE: Educational and technical, suitable for developers""",
            
            'general': """
TASK: Answer the question comprehensively based on the provided context.
APPROACH:
1. Address the specific question directly
2. Provide relevant supporting information
3. Use examples where helpful
4. Cite sources appropriately
TONE: Helpful and informative"""
        }
        
        instructions = type_instructions.get(query_type, type_instructions['general'])
        
        full_prompt = base_instructions.format(
            total_nodes=stats['total_nodes'],
            file_nodes=stats['file_nodes'],
            class_nodes=stats['class_nodes'],
            function_nodes=stats['function_nodes'],
            avg_score=stats['avg_score'],
            context=context
        ) + instructions
        
        return SystemMessage(content=full_prompt)
    
    @staticmethod
    def build_user_message(query: str, analyzer: QueryAnalyzer) -> HumanMessage:
        """Build a user message with query context."""
        
        message_content = query
        
        # Add query type hint if not obvious
        if analyzer.query_type != 'general':
            message_content += f"\n\n[Query Type: {analyzer.query_type.title()}]"
        
        # Add keywords hint for better context
        if analyzer.keywords:
            message_content += f"\n[Key Topics: {', '.join(analyzer.keywords[:5])}]"
        
        return HumanMessage(content=message_content)


class QueryProcessor:
    """Main query processor that orchestrates the entire pipeline."""
    
    def __init__(self):
        self.analyzer = None
        self.context_builder = None
        self.prompt_engineer = PromptEngineer()
    
    def process_query(self, query: str, retrieved_nodes: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
        """
        Process a query and generate an answer.
        
        Args:
            query: User query string
            retrieved_nodes: List of retrieved code nodes
        
        Returns:
            Tuple of (answer, metadata)
        """
        logger.info(f"🔄 Processing query: {query[:50]}...")
        
        # Step 1: Analyze query
        self.analyzer = QueryAnalyzer(query)
        logger.debug(f"Query type: {self.analyzer.query_type}, Keywords: {self.analyzer.keywords}")
        
        # Step 1.5: Check if query is off-topic (greeting, farewell, or unrelated)
        if self.analyzer.is_off_topic:
            logger.info(f"📝 Off-topic query detected: {query[:50]}...")
            answer = self._generate_off_topic_response(query)
            metadata = {
                'query_type': 'off-topic',
                'is_greeting': self.analyzer.is_greeting,
                'is_farewell': self.analyzer.is_farewell,
                'is_off_topic': True,
                'answer_length': len(answer)
            }
            return answer, metadata
        
        # Step 2: Build context
        self.context_builder = ContextBuilder(retrieved_nodes)
        context_string = self.context_builder.build_context_string(include_code=True)
        stats = self.context_builder.get_summary_stats()
        
        logger.debug(f"Context built: {len(context_string)} chars, {stats['total_nodes']} nodes")
        
        # Step 3: Build prompt
        system_message = self.prompt_engineer.build_system_prompt(
            self.analyzer.query_type,
            context_string,
            stats
        )
        user_message = self.prompt_engineer.build_user_message(query, self.analyzer)
        
        # Step 4: Get LLM response
        logger.debug("Invoking LLM...")
        try:
            response = llm.invoke([system_message, user_message])
            answer = response.content
            logger.info(f"✅ Generated answer ({len(answer)} chars)")
        except Exception as e:
            logger.error(f"❌ Error invoking LLM: {e}")
            answer = f"Error generating answer: {str(e)}"
        
        # Step 5: Prepare metadata
        metadata = {
            'query_type': self.analyzer.query_type,
            'keywords': self.analyzer.keywords,
            'is_multi_part': self.analyzer.is_multi_part,
            'context_stats': stats,
            'retrieved_nodes_count': len(retrieved_nodes),
            'answer_length': len(answer)
        }
        
        return answer, metadata
    
    def _generate_off_topic_response(self, query: str) -> str:
        """Generate a friendly response for off-topic queries."""
        query_lower = query.lower().strip()
        
        # Greeting responses
        if self.analyzer.is_greeting:
            greetings = [
                "👋 Hello! I'm CodeChat, your AI assistant for code analysis. How can I help you understand your codebase today?",
                "Hey there! 👋 I'm here to help you explore and understand your code. What would you like to know?",
                "Hi! 👋 Ready to dive into your code? Ask me anything about your repository!",
                "Greetings! 👋 I'm CodeChat. Feel free to ask me questions about your codebase.",
            ]
            import random
            return random.choice(greetings)
        
        # Farewell responses
        if self.analyzer.is_farewell:
            farewells = [
                "👋 Goodbye! Feel free to come back anytime you need help with your code. Happy coding!",
                "See you later! 👋 Don't hesitate to reach out if you have more questions about your codebase.",
                "Take care! 👋 Looking forward to helping you analyze more code next time!",
                "Bye! 👋 Thanks for using CodeChat. Keep coding!",
            ]
            import random
            return random.choice(farewells)
        
        # Generic off-topic response
        off_topic_responses = [
            "I appreciate the question, but I'm specifically designed to help you understand and analyze your codebase. 💻 Is there anything about your code I can help you with?",
            "That's an interesting question, but I'm focused on code analysis and understanding your repository. 📚 Do you have any questions about your code?",
            "I'm here to help you explore your code! 🔍 While I can't help with that, I'd love to answer any questions about your codebase.",
            "I'm CodeChat, your code analysis assistant. 🤖 I'm best at helping you understand code. What would you like to know about your repository?",
        ]
        import random
        return random.choice(off_topic_responses)


# Global processor instance
_processor = None

def get_processor() -> QueryProcessor:
    """Get or create the global query processor."""
    global _processor
    if _processor is None:
        _processor = QueryProcessor()
    return _processor
