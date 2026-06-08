import sqlite3
import sys

sys.path.append(r"c:\Users\dravi\OneDrive\Desktop\CodeValidResearchAssistant\backend")
from api.auth_utils import get_password_hash

conn = sqlite3.connect(r"c:\Users\dravi\OneDrive\Desktop\CodeValidResearchAssistant\backend\research_assistant.db")
cursor = conn.cursor()

new_pw_hash = get_password_hash("Dravid@reddy")

try:
    cursor.execute("UPDATE users SET hashed_password = ? WHERE email = ?", (new_pw_hash, "Dravid@reddy"))
    conn.commit()
    print("Successfully updated password hash for Dravid@reddy")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
