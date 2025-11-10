#!/usr/bin/env python3
"""
OAuth Configuration Verification Script

This script helps verify your Google OAuth configuration is correct.
Run this before testing OAuth login to catch common configuration errors.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:5000/callback')
SECRET_KEY = os.getenv('SECRET_KEY')

print("=" * 60)
print("OAuth Configuration Verification")
print("=" * 60)

issues = []

# Check CLIENT_ID
print("\n1. Checking GOOGLE_CLIENT_ID...")
if not CLIENT_ID:
    print("   ❌ ERROR: GOOGLE_CLIENT_ID is not set in .env file")
    issues.append("Missing GOOGLE_CLIENT_ID")
elif CLIENT_ID == 'your-google-client-id-here.apps.googleusercontent.com':
    print("   ❌ ERROR: GOOGLE_CLIENT_ID is still set to placeholder value")
    issues.append("GOOGLE_CLIENT_ID not configured")
elif not CLIENT_ID.endswith('.apps.googleusercontent.com'):
    print("   ⚠️  WARNING: CLIENT_ID format looks unusual")
    print(f"      Current: {CLIENT_ID[:50]}...")
else:
    print(f"   ✅ Found: {CLIENT_ID[:30]}...{CLIENT_ID[-10:]}")

# Check CLIENT_SECRET
print("\n2. Checking GOOGLE_CLIENT_SECRET...")
if not CLIENT_SECRET:
    print("   ❌ ERROR: GOOGLE_CLIENT_SECRET is not set in .env file")
    issues.append("Missing GOOGLE_CLIENT_SECRET")
elif CLIENT_SECRET == 'your-google-client-secret-here':
    print("   ❌ ERROR: GOOGLE_CLIENT_SECRET is still set to placeholder value")
    issues.append("GOOGLE_CLIENT_SECRET not configured")
else:
    print(f"   ✅ Found: {CLIENT_SECRET[:20]}...")

# Check REDIRECT_URI
print("\n3. Checking REDIRECT_URI...")
if not REDIRECT_URI:
    print("   ❌ ERROR: REDIRECT_URI is not set")
    issues.append("Missing REDIRECT_URI")
else:
    print(f"   ✅ Redirect URI: {REDIRECT_URI}")
    
    # Check for common issues
    if REDIRECT_URI.endswith('/'):
        print("   ⚠️  WARNING: Redirect URI has trailing slash - ensure Google Cloud Console matches exactly")
        issues.append("Redirect URI has trailing slash")
    
    if 'localhost' in REDIRECT_URI and '127.0.0.1' in REDIRECT_URI:
        print("   ⚠️  WARNING: Mixing localhost and 127.0.0.1 can cause issues")
        issues.append("Mixed localhost/127.0.0.1")
    
    if 'http://' not in REDIRECT_URI and 'https://' not in REDIRECT_URI:
        print("   ❌ ERROR: Redirect URI must include protocol (http:// or https://)")
        issues.append("Missing protocol in redirect URI")

# Check SECRET_KEY
print("\n4. Checking SECRET_KEY...")
if not SECRET_KEY or SECRET_KEY == 'dev-secret-key-change-in-production-please':
    print("   ⚠️  WARNING: Using default SECRET_KEY - change this for production")
else:
    print("   ✅ SECRET_KEY is set")

# Summary and instructions
print("\n" + "=" * 60)
print("VERIFICATION SUMMARY")
print("=" * 60)

if not issues:
    print("\n✅ All basic configuration checks passed!")
    print("\nNEXT STEPS:")
    print("   1. Go to Google Cloud Console: https://console.cloud.google.com/apis/credentials")
    print("   2. Find your OAuth 2.0 Client ID")
    print(f"   3. Under 'Authorized redirect URIs', ensure this EXACT URL is listed:")
    print(f"      → {REDIRECT_URI}")
    print("   4. Check that there are NO trailing slashes, and the protocol matches exactly")
    print("   5. If your app is in 'Testing' status, add your email as a test user:")
    print("      - Go to OAuth consent screen")
    print("      - Scroll to 'Test users'")
    print("      - Add your @cloudphysician.net email")
    print("\n   6. Common issues:")
    print("      - http://localhost:5000/callback vs https://localhost:5000/callback")
    print("      - http://localhost:5000/callback vs http://127.0.0.1:5000/callback")
    print("      - http://localhost:5000/callback vs http://localhost:5000/callback/")
    print("      - Missing test user if app is in testing mode")
else:
    print("\n⚠️  ISSUES FOUND:")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")
    print("\nPlease fix these issues before attempting OAuth login.")

print("\n" + "=" * 60)






