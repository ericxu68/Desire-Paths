import requests
import os
import subprocess
import re
from pathlib import Path
import shutil
import stat
import csv

# === SET YOUR GITHUB TOKEN HERE ===
GITHUB_TOKEN = "user real token"  # Replace this with your real token

# === HEADERS ===
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# === SEARCH REPOS ===
def search_repos_using_chrono():
    repos = []
    for page in range(1, 6):  # 5 pages × 100 = 500 repos max
        print(f"🔍 Searching GitHub (page {page})...")
        query = 'chrono language:Rust'
        url = f"https://api.github.com/search/repositories?q={query}&per_page=100&page={page}"
        response = requests.get(url, headers=headers)
        data = response.json()

        if "items" not in data:
            print("❌ Error:", data)
            break

        for item in data["items"]:
            repos.append({
                "name": item["full_name"],
                "clone_url": item["clone_url"],
                "html_url": item["html_url"]
            })
    return repos

# === HANDLE READ-ONLY FILES FOR WINDOWS CLEANUP ===
def handle_remove_readonly(func, path, _):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        print(f"⚠️ Failed to remove {path}: {e}")

# === CHECK CARGO.TOML FOR CHRONO VERSION ===
def check_chrono_version(repo, base_path):
    repo_dir = base_path / repo["name"].replace("/", "__")

    # Delete existing folder if present before cloning
    if repo_dir.exists():
        shutil.rmtree(repo_dir, onerror=handle_remove_readonly)

    try:
        subprocess.run(["git", "clone", "--depth", "1", repo["clone_url"], str(repo_dir)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        cargo_toml = repo_dir / "Cargo.toml"
        if cargo_toml.exists():
            with open(cargo_toml, "r", encoding="utf-8") as f:
                content = f.read()
                match = re.search(r'chrono\s*=\s*["\']0\.4\.(\d{1,2})["\']', content)
                if match:
                    patch = int(match.group(1))
                    if patch <= 24:
                        print(f"✅ {repo['name']} uses chrono = 0.4.{patch}")
                        return repo['html_url'], f"0.4.{patch}"
    except Exception as e:
        print(f"⚠️ Failed to check {repo['name']}: {e}")
    finally:
        if repo_dir.exists():
            shutil.rmtree(repo_dir, onerror=handle_remove_readonly)
    return None, None

# === MAIN ===
def main():
    print("🚀 Starting chrono version scanner...\n")
    base_path = Path("repos")
    base_path.mkdir(exist_ok=True)
    repos = search_repos_using_chrono()

    found = []
    for repo in repos:
        url, version = check_chrono_version(repo, base_path)
        if url:
            found.append((repo["name"], url, version))

    print(f"\n🎉 Found {len(found)} repositories using chrono <= 0.4.24:\n")
    for name, url, version in found:
        print(f"- {name}: {url} (chrono = \"{version}\")")

    # Save results to CSV
    csv_file = "chrono_projects.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Repository", "URL", "Chrono Version"])
        writer.writerows(found)
    print(f"\n💾 Results saved to '{csv_file}'")

if __name__ == "__main__":
    main()
