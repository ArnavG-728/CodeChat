#!/usr/bin/env python3
"""
CodeChat Backend - Main Entry Point

Simply starts the FastAPI server that handles all repository management
through the web UI. No command-line repository loading needed.

Usage:
    python main.py              # Start the API server
    python main.py --port 8000  # Start on specific port
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def print_banner():
    """Print welcome banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║                   🤖CodeChat v2.0 Backend                   ║
    ║           AI-Powered Code Repository Chat System             ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_environment():
    """Check if required environment variables are set"""
    print("🔍 Checking environment configuration...")
    
    load_dotenv()
    
    required_vars = {
        'ACCESS_TOKEN': 'GitHub Personal Access Token',
        'GOOGLE_API_KEY': 'Google Gemini API Key',
        'password': 'Neo4j Database Password'
    }
    
    optional_vars = {
        'NEO4J_CONNECTION_URL': 'Neo4j Connection URL (default: neo4j://127.0.0.1:7687)'
    }
    
    missing = []
    configured = []
    
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing.append(f"  ❌ {var}")
        else:
            configured.append(f"  ✅ {var}")
    
    # Check optional variables
    for var, description in optional_vars.items():
        if os.getenv(var):
            configured.append(f"  ✅ {var}")
    
    for item in configured:
        print(item)
    
    if missing:
        print("\n⚠️  Missing environment variables:")
        for item in missing:
            print(item)
        print("\n📝 Configure these in backend/.env file")
        print("⚠️  Some features may not work without proper configuration\n")
        return False
    
    print("\n✅ All environment variables configured!")
    return True

def check_neo4j():
    """Check if Neo4j is running"""
    print("\n🔍 Checking Neo4j connection...")
    try:
        from neo4j import GraphDatabase
        
        # Get connection URL from env or use default
        uri = os.getenv('NEO4J_CONNECTION_URL', 'neo4j://127.0.0.1:7687')
        password = os.getenv('password')
        
        if not password:
            print("⚠️  Neo4j password not configured in .env")
            return False
        
        print(f"   Connecting to: {uri}")
        driver = GraphDatabase.driver(uri, auth=("neo4j", password))
        
        # Test connection with neo4j database
        with driver.session(database="neo4j") as session:
            session.run("RETURN 1")
        
        driver.close()
        print("✅ Neo4j is running and accessible!")
        return True
    except Exception as e:
        print(f"❌ Neo4j connection failed: {str(e)}")
        print(f"📝 Make sure Neo4j is running on {uri}")
        return False

def start_server(port=8000):
    """Start the FastAPI server"""
    print("\n" + "=" * 66)
    print("  STARTING API SERVER")
    print("=" * 66)
    
    print(f"\n🚀 Backend API: http://localhost:{port}")
    print(f"📚 API Documentation: http://localhost:{port}/docs")
    print(f"🔌 WebSocket: ws://localhost:{port}/ws")
    print("\n✨ Features Available:")
    print("  • Dynamic Repository Management")
    print("  • Real-time Processing Updates")
    print("  • Health Monitoring")
    print("  • AI-Powered Code Chat")
    print("\n💡 Next Steps:")
    print("  1. Start frontend: cd frontend && npm run dev")
    print("  2. Open: http://localhost:3000")
    print("  3. Click '+' button to add repositories")
    print("\n⏹️  Press Ctrl+C to stop the server\n")
    
    try:
        # Change to src directory
        src_dir = Path(__file__).parent / "src"
        os.chdir(src_dir)
        
        # Import and run the API
        import uvicorn
        from api import app
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
        return True
    except Exception as e:
        print(f"\n❌ Error starting API server: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point - Simply start the API server"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="CodeChat Backend API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Repository management is done through the web UI:
  1. Start this server: python main.py
  2. Start frontend: cd frontend && npm run dev
  3. Open http://localhost:3000
  4. Add repositories through the UI
        """
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port to run the server on (default: 8000)'
    )
    
    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    # Check environment
    env_ok = check_environment()
    
    # Check Neo4j
    neo4j_ok = check_neo4j()
    
    if not env_ok or not neo4j_ok:
        print("\n⚠️  WARNING: Some checks failed!")
        print("The server will start, but some features may not work properly.")
        print("Please fix the issues above for full functionality.\n")
        
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("\n❌ Startup cancelled.")
            sys.exit(1)
    
    # Start the server
    start_server(args.port)

if __name__ == "__main__":
    main()
