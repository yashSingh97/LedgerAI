import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables once
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL or SUPABASE_KEY not found in environment variables")

print("[Supabase] Initializing Supabase client...")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
