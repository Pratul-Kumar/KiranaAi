"""
scripts/setup.py — One-time setup script to initialize static project directories.
Run from the root of the project: python scripts/setup.py
"""
from pathlib import Path

def setup():
    root_dir = Path(__file__).resolve().parent.parent
    
    # runtime directories
    directories = [
        root_dir / "logs",
        root_dir / "backend" / "logs"
    ]
    
    print("Initializing static layout for ZnShop...")
    for d in directories:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            print(f"Created: {d}")
        else:
            print(f"Already exists: {d}")

    print("\nSetup complete. The system will no longer dynamically generate files at runtime.")

if __name__ == "__main__":
    setup()
