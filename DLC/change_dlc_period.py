import time
from supabase import create_client
from datetime import datetime

# 🔹 Supabase Setup
SUPABASE_URL = "https://dfckzgwvefprwuythpnl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRmY2t6Z3d2ZWZwcnd1eXRocG5sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkyNjM0MTEsImV4cCI6MjA1NDgzOTQxMX0.5EnzP0Ck3VhxBOVoVX_nsozSU8OYe57aySSCPH2BCWU"  # Use your key!
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_current_dlc():
    """Fetch the current DLC period."""
    response = supabase.table("dlc_settings").select("current_dlc").execute()
    if response.data:
        return response.data[0]["current_dlc"]
    return None

def increment_dlc_id(dlc_id):
    """Increment DLC ID from 'DLC #1' → 'DLC #2'."""
    parts = dlc_id.split("#")
    if len(parts) == 2:
        current_num = int(parts[1].strip())
        next_num = current_num + 1
        return f"DLC #{next_num}"
    else:
        print("⚠️ DLC format not recognized. Defaulting to DLC #1.")
        return "DLC #1"

def archive_table(source_table, archive_table):
    """Move all data from source_table to archive_table, then delete source_table data."""
    print(f"📦 Archiving from {source_table} → {archive_table}...")

    # Fetch all data
    response = supabase.table(source_table).select("*").execute()

    if not response.data:
        print(f"⚠️ No data found in {source_table} to archive.")
        return

    records = response.data

    # ✅ Convert timestamps to ISO 8601 where applicable
    for record in records:
        for key in record.keys():
            if "timestamp" in key or "created_at" in key or "updated_at" in key:
                ts_value = record[key]
                if isinstance(ts_value, (int, float)):
                    record[key] = datetime.utcfromtimestamp(ts_value).isoformat() + "Z"

    # ✅ Insert into archive table
    supabase.table(archive_table).insert(records).execute()

    # ✅ Delete records (use "email" for quiz_results and "id" for other tables)
    if source_table == "quiz_results" or source_table == "quiz_results_engagement":
        supabase.table(source_table).delete().neq("email", "").execute()
    else:
        supabase.table(source_table).delete().neq("id", 0).execute()

    print(f"✅ Archived {len(records)} records from {source_table}.")


def update_dlc_period():
    """Main function to close out the current DLC and move to the next one."""
    # 1️⃣ Get current DLC period
    current_dlc = get_current_dlc()

    if not current_dlc:
        print("⚠️ No current DLC found in settings.")
        return

    print(f"🔐 Closing {current_dlc}...")

    # 2️⃣ Archive data for Player Services
    archive_table("quiz_questions", "quiz_questions_archive")

    # 3️⃣ Archive data for Player Engagement
    archive_table("quiz_questions_engagement", "quiz_questions_engagement_archive")

    # 4️⃣ Archive results
    archive_table("quiz_results", "quiz_results_archive")

    # 5️⃣ Calculate next DLC period
    next_dlc = increment_dlc_id(current_dlc)

    # 6️⃣ Update dlc_settings with new DLC
    supabase.table("dlc_settings").update({"current_dlc": next_dlc}).eq("id", 1).execute()

    print(f"🚀 DLC period updated from {current_dlc} → {next_dlc}")

if __name__ == "__main__":
    print("🔧 Starting DLC period update...")
    update_dlc_period()
    print("✅ DLC period change complete!")
