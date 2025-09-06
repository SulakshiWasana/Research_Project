#!/usr/bin/env python3
"""
Start Flask App Script
Starts the Flask application with proper error handling
"""

import sys
import os
import webbrowser
from threading import Timer

def open_browser():
    """Open browser after a short delay"""
    webbrowser.open('http://127.0.0.1:8080')

def main():
    print("🚀 Starting Flask Application...")
    print("=" * 40)
    
    try:
        # Import and start the Flask app
        from app import app
        
        print("✅ Flask app imported successfully")
        print("🌐 Starting server on http://127.0.0.1:8080")
        print("\n📋 Available Routes:")
        print("   • / - Login page")
        print("   • /admin - Admin dashboard (admin/admin123)")
        print("   • /dashboard - Student dashboard (student1/password1)")
        print("\n🔑 Login Credentials:")
        print("   Admin: admin/admin123")
        print("   Student 1: student1/password1")
        print("   Student 2: student2/password2")
        
        # Open browser after 2 seconds
        Timer(2.0, open_browser).start()
        print("\n🌐 Opening browser in 2 seconds...")
        print("\n⏹️  Press Ctrl+C to stop the server")
        print("=" * 40)
        
        # Start the Flask app
        app.run(debug=True, host='127.0.0.1', port=8080, use_reloader=False)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting Flask app: {e}")
        print("   Please check if port 8080 is available")

if __name__ == "__main__":
    main()
