import os
import re
import json

def sync_version():
    if not os.path.exists("VERSION"):
        print("VERSION file not found.")
        return

    with open("VERSION", "r") as f:
        version_raw = f.read().strip()

    # Remove _dev postfix if present
    version = version_raw.replace("_dev", "")
    print(f"Syncing version to: {version} (from {version_raw})")

    # 1. Update applug.json
    if os.path.exists("applug.json"):
        with open("applug.json", "r") as f:
            data = json.load(f)
        
        data["version"] = version
        
        with open("applug.json", "w") as f:
            json.dump(data, f, indent=4)
        print("Updated applug.json")

    # 2. Update doc/DEPLOYMENT.md or other MD files if they mention the version
    # EyeRate might have its own documentation
    for md_file in ["README.md", "docs/USER_GUIDE.md"]:
        if os.path.exists(md_file):
            with open(md_file, "r") as f:
                content = f.read()
            
            new_content = re.sub(r'eyerate-\d+\.\d+\.\d+(?:-dev)?', f'eyerate-{version}', content)
            
            with open(md_file, "w") as f:
                f.write(new_content)
            print(f"Updated {md_file}")

if __name__ == "__main__":
    sync_version()
