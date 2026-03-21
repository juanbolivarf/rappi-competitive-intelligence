#!/usr/bin/env python3
"""
Quick Cloudflare Browser Rendering verification.
Run this FIRST after setting your API token in .env

Usage:
    python verify_cf_setup.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv()

account_id = os.getenv("CF_ACCOUNT_ID", "")
api_token = os.getenv("CF_API_TOKEN", "")

print("🔍 Cloudflare Browser Rendering — Setup Verification\n")

# Check credentials
if not account_id or account_id == "your_cloudflare_account_id_here":
    print("❌ CF_ACCOUNT_ID not set in .env")
    sys.exit(1)
print(f"✅ Account ID: {account_id[:8]}...{account_id[-4:]}")

if not api_token or api_token == "paste_your_api_token_here":
    print("❌ CF_API_TOKEN not set in .env")
    print("   → Go to https://dash.cloudflare.com/profile/api-tokens")
    print("   → Create Custom Token → Browser Rendering: Edit")
    sys.exit(1)
print(f"✅ API Token: {api_token[:8]}...{api_token[-4:]}")

base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering"
headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json",
}

# Test 1: /content endpoint (simplest)
print("\n--- Test 1: /content (fetch rendered HTML) ---")
try:
    r = httpx.post(
        f"{base_url}/content",
        headers=headers,
        json={"url": "https://example.com"},
        timeout=30,
    )
    if r.status_code == 200:
        data = r.json()
        if data.get("success"):
            html = data.get("result", "")
            print(f"✅ /content works! Got {len(html):,} chars of HTML")
            ms = r.headers.get("X-Browser-Ms-Used", "?")
            print(f"   Browser time used: {ms}ms")
        else:
            print(f"⚠️  Response not successful: {data.get('errors', data)}")
    elif r.status_code == 403:
        print(f"❌ 403 Forbidden — API token lacks Browser Rendering: Edit permission")
        print(f"   Response: {r.text[:200]}")
    else:
        print(f"❌ HTTP {r.status_code}: {r.text[:300]}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: /scrape endpoint
print("\n--- Test 2: /scrape (extract elements) ---")
try:
    r = httpx.post(
        f"{base_url}/scrape",
        headers=headers,
        json={
            "url": "https://example.com",
            "elements": [{"selector": "h1"}, {"selector": "p"}],
        },
        timeout=30,
    )
    if r.status_code == 200:
        data = r.json()
        if data.get("success"):
            results = data.get("result", [])
            for sel in results:
                items = sel.get("results", [])
                print(f"✅ '{sel.get('selector')}': {len(items)} elements found")
                for item in items[:1]:
                    print(f"   → \"{item.get('text', '')[:60]}\"")
        else:
            print(f"⚠️  {data.get('errors')}")
    else:
        print(f"❌ HTTP {r.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: /json endpoint (AI extraction — the key one)
print("\n--- Test 3: /json (AI-powered extraction) ---")
try:
    r = httpx.post(
        f"{base_url}/json",
        headers=headers,
        json={
            "url": "https://example.com",
            "prompt": "Extract the page title and the main paragraph text",
            "gotoOptions": {"waitUntil": "networkidle0"},
        },
        timeout=45,
    )
    if r.status_code == 200:
        data = r.json()
        if data.get("success"):
            result = data.get("result", {})
            print(f"✅ /json works! AI extracted:")
            if isinstance(result, dict):
                for k, v in list(result.items())[:5]:
                    print(f"   {k}: {str(v)[:80]}")
            else:
                print(f"   {str(result)[:200]}")
        else:
            print(f"⚠️  {data.get('errors')}")
    else:
        print(f"❌ HTTP {r.status_code}: {r.text[:200]}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: /screenshot endpoint
print("\n--- Test 4: /screenshot ---")
try:
    r = httpx.post(
        f"{base_url}/screenshot",
        headers=headers,
        json={"url": "https://example.com"},
        timeout=30,
    )
    if r.status_code == 200:
        Path("assets").mkdir(exist_ok=True)
        Path("assets/verification_screenshot.png").write_bytes(r.content)
        print(f"✅ Screenshot captured: {len(r.content):,} bytes → assets/verification_screenshot.png")
    else:
        print(f"❌ HTTP {r.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 50)
print("If all 4 tests passed, you're ready to scrape!")
print("Run: python -m scraper.main --addresses 3 --platform rappi")
print("=" * 50)
