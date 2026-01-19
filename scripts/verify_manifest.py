import json
from pathlib import Path

def verify_manifest():
    root = Path(__file__).resolve().parents[1] / "assets" / "references"
    manifest_path = root / "manifest.json"
    
    if not manifest_path.exists():
        print(f"FAILED: {manifest_path} not found")
        return
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    all_paths_in_manifest = []
    
    # Collect all paths from manifest
    for entry in manifest.get("global_references", []):
        all_paths_in_manifest.append(entry["path"])
    for design_id, entries in manifest.get("designs", {}).items():
        for entry in entries:
            all_paths_in_manifest.append(entry["path"])
            
    print(f"Manifest has {len(all_paths_in_manifest)} entries.")
    
    # 1. Check if all files in manifest exist
    missing_files = []
    for rel_path in all_paths_in_manifest:
        abs_path = root / rel_path
        if not abs_path.exists():
            missing_files.append(rel_path)
    
    if missing_files:
        print("\nFAILED: Some files in manifest are missing on disk:")
        for f in missing_files:
            print(f"  - {f}")
    else:
        print("OK: All files in manifest exist on disk.")
        
    # 2. Check if all image files on disk are in manifest
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.avif'}
    all_image_on_disk = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in image_extensions:
            # Get path relative to references root
            rel = p.relative_to(root)
            all_image_on_disk.append(str(rel))
            
    untracked_files = [f for f in all_image_on_disk if f not in all_paths_in_manifest]
    
    if untracked_files:
        print("\nWARNING: Some image files on disk are not in manifest:")
        for f in untracked_files:
            print(f"  - {f}")
    else:
        print("OK: All image files on disk are tracked in manifest.")

if __name__ == "__main__":
    verify_manifest()
