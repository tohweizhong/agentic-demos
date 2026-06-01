import sys
import os
import json
import time
from collections import Counter

# Add sharepoint_eval to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sharepoint_client import (
    load_config,
    get_access_token,
    get_site_id,
    get_default_drive_id,
    get_all_files_recursive,
    get_file_permissions_api
)

def format_bytes(num_bytes: int) -> str:
    """Formats raw bytes into human-readable MB/KB/GB."""
    for unit in ['Bytes', 'KB', 'MB', 'GB']:
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"

def analyze_sharepoint_contents():
    print("Authenticating and connecting to SharePoint Document Library...")
    config = load_config()
    token = get_access_token(config)
    site_id = get_site_id(token, config["SHAREPOINT_SITE_HOST"], config["SHAREPOINT_SITE_PATH"])
    drive_id = get_default_drive_id(token, site_id)
    
    print("Retrieving all files and folders recursively (this might take a moment)...")
    start_time = time.time()
    all_items = get_all_files_recursive(token, drive_id, "root", "")
    end_time = time.time()
    
    print(f"Successfully retrieved {len(all_items)} items in {end_time - start_time:.2f} seconds.")
    
    # Aggregate statistics variables
    total_items = len(all_items)
    folders_count = 0
    files_count = 0
    total_size_bytes = 0
    
    extensions = []
    sensitivity_labels = []
    encrypted_count = 0
    empty_files_count = 0
    long_paths_count = 0
    max_depth = 0
    
    file_sizes = []
    last_modified_times = []
    
    # Permission analysis variables
    principals_list = []
    principal_types = []
    
    duplicates_counter = Counter()
    paths_list = []
    
    for item in all_items:
        is_folder = item.get("type") == "folder"
        name = item.get("name", "")
        path = item.get("path", "")
        paths_list.append(path)
        
        # Path depth calculation
        depth = len(path.split("/")) if path else 0
        if depth > max_depth:
            max_depth = depth
            
        if is_folder:
            folders_count += 1
        else:
            files_count += 1
            size = item.get("size", 0)
            total_size_bytes += size
            file_sizes.append(size)
            
            # Fetch direct file permissions for security audit
            item_id = item.get("id")
            print(f"[{files_count}] Auditing access permissions for: '{name}'...")
            try:
                perms = get_file_permissions_api(item_id=item_id, drive_id=drive_id)
                for p in perms:
                    principals_list.append(p.get("name", "Unknown"))
                    principal_types.append(p.get("type", "Unknown"))
            except Exception as e:
                print(f"Error fetching permissions for {name}: {e}")
            
            # File details
            ext = name.split(".")[-1].lower() if "." in name else "no_extension"
            extensions.append(ext)
            
            # Sensitivity label
            label = item.get("sensitivity_label")
            sensitivity_labels.append(label or "Unclassified (None)")
            
            # Check encryption (Confidential / Highly Confidential)
            if label and any(kw in label.lower() for kw in ["confidential", "restricted"]):
                encrypted_count += 1
                
            # Empty files
            if size == 0:
                empty_files_count += 1
                
            # Path length check (Windows limit standard: 260 chars)
            if len(path) > 260:
                long_paths_count += 1
                
            # Last modified date
            modified = item.get("last_modified")
            if modified:
                last_modified_times.append(modified)
                
            # Track name duplicates
            duplicates_counter[name] += 1

    avg_file_size = total_size_bytes / files_count if files_count > 0 else 0
    median_file_size = sorted(file_sizes)[files_count // 2] if files_count > 0 else 0

    ext_dist = Counter(extensions)
    label_dist = Counter(sensitivity_labels)
    principal_counts = Counter(principals_list)
    principal_type_counts = Counter(principal_types)
    
    # Identify duplicate filenames (count > 1)
    duplicates = {name: count for name, count in duplicates_counter.items() if count > 1}
    total_duplicates_count = sum(duplicates.values()) - len(duplicates)
    
    # Sort modified times
    sorted_modifications = sorted(last_modified_times)
    oldest_modified = sorted_modifications[0] if sorted_modifications else "N/A"
    newest_modified = sorted_modifications[-1] if sorted_modifications else "N/A"
    
    # Collate metrics
    stats = {
        "total_items": total_items,
        "folders_count": folders_count,
        "files_count": files_count,
        "total_size_bytes": total_size_bytes,
        "avg_file_size_bytes": avg_file_size,
        "median_file_size_bytes": median_file_size,
        "max_folder_depth": max_depth,
        "empty_files_count": empty_files_count,
        "long_paths_count_gt_260": long_paths_count,
        "duplicate_files_count": total_duplicates_count,
        "encrypted_files_count": encrypted_count,
        "encrypted_percentage": (encrypted_count / files_count * 100) if files_count > 0 else 0,
        "oldest_modified": oldest_modified,
        "newest_modified": newest_modified,
        "file_type_distribution": dict(ext_dist),
        "sensitivity_label_distribution": dict(label_dist),
        "principal_distribution": dict(principal_counts),
        "principal_type_distribution": dict(principal_type_counts)
    }
    
    stats_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(stats_dir, "sharepoint_contents_stats.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
        
    md_path = os.path.join(stats_dir, "sharepoint_contents_report.md")
    
    # Plot and save the distributions
    plot_last_modified_distribution(last_modified_times, os.path.join(stats_dir, "last_modified_distribution.png"))
    plot_file_types_distribution(stats["file_type_distribution"], os.path.join(stats_dir, "file_types_distribution.png"))
    plot_sensitivity_distribution(stats["sensitivity_label_distribution"], os.path.join(stats_dir, "sensitivity_labels_distribution.png"))
    plot_file_sizes_distribution(file_sizes, os.path.join(stats_dir, "file_sizes_distribution.png"))
    plot_principals_distribution(stats["principal_distribution"], os.path.join(stats_dir, "principals_distribution.png"))
    
    generate_markdown_report(stats, md_path, duplicates, file_sizes)
    
    print("\n========================================")
    print("     SharePoint Analysis Completed!")
    print("========================================")
    print(f"Total Items Analyzed : {total_items}")
    print(f"Total Files          : {files_count}")
    print(f"Total Data Size      : {format_bytes(total_size_bytes)}")
    print(f"Encrypted (RMS) Files: {encrypted_count} ({stats['encrypted_percentage']:.2f}%)")
    print(f"Report generated at  : {md_path}")
    print(f"JSON raw metrics at  : {json_path}")

def generate_markdown_report(stats: dict, output_path: str, duplicates: dict, file_sizes: list):
    """Compiles the detailed metrics into a stunning report."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 📊 SharePoint Contents & Cleanliness Analytics Report\n\n")
        f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n\n")
        
        f.write("This report provides a high-level aggregate view of the documents stored inside your SharePoint site to help evaluate content sizing, migration completeness, and overall security alignment before connecting AI assistants.\n\n")
        
        f.write("## 📈 General Sizing Metrics\n\n")
        f.write("| Metric | Count / Value | Description |\n")
        f.write("| :--- | :--- | :--- |\n")
        f.write(f"| **Total Site Items** | {stats['total_items']} | Combined file and folder assets. |\n")
        f.write(f"| **Total Folders** | {stats['folders_count']} 📁 | Directory organization nodes. |\n")
        f.write(f"| **Total Files** | {stats['files_count']} 📄 | Document content files. |\n")
        f.write(f"| **Combined Data Size** | `{format_bytes(stats['total_size_bytes'])}` 💾 | Aggregate bytes stored. |\n")
        f.write(f"| **Average File Size** | `{format_bytes(int(stats['avg_file_size_bytes']))}` | Metric for context sizing estimates. |\n")
        f.write(f"| **Median File Size** | `{format_bytes(stats['median_file_size_bytes'])}` | Better indicator of typical file sizing. |\n")
        f.write(f"| **Max Folder Recursion Depth** | {stats['max_folder_depth']} | Sibling folder nesting depth. |\n\n")
        
        f.write("### 💾 Graphical Sizing Categories (File Sizes)\n\n")
        f.write("![File Sizes Category Distribution](file_sizes_distribution.png)\n\n")
        
        f.write("## 🔒 Security & Sensitivity Classifications\n\n")
        f.write(f"* **Total Encrypted (RMS-Protected) Files**: `{stats['encrypted_files_count']}` (**{stats['encrypted_percentage']:.2f}%** of all files) 🔒\n")
        f.write("  *Note: Encrypted Confidential files will trigger decryption constraints when directly downloaded as binary envelopes by custom text tools.*\n\n")
        
        f.write("### Sensitivity Label Breakdown:\n")
        for label, count in stats["sensitivity_label_distribution"].items():
            emoji = "🟢" if "general" in label.lower() else "🟡" if "confidential" in label.lower() else "🔴" if "highly" in label.lower() else "⚪"
            f.write(f"- {emoji} **`{label}`**: {count} files\n")
        f.write("\n")
        
        f.write("### 🛡️ Graphical Sensitivity Classifications\n\n")
        f.write("![Sensitivity Labels Distribution](sensitivity_labels_distribution.png)\n\n")
        
        f.write("### 👥 Access Authorization & Principal Distributions\n\n")
        f.write("This section shows which users, groups, or sharing links have direct explicit permissions across your document library.\n\n")
        f.write("| Principal | Access Count |\n")
        f.write("| :--- | :--- |\n")
        # Top 5 authorized
        top_principals = sorted(stats["principal_distribution"].items(), key=lambda x: x[1], reverse=True)[:5]
        for name, count in top_principals:
            f.write(f"| **{name}** | {count} files |\n")
        f.write("\n")
        f.write("![Principals Distribution](principals_distribution.png)\n\n")
        
        f.write("## 📄 File Types & Suffix Distribution\n\n")
        f.write("| Suffix | Count | Percentage |\n")
        f.write("| :--- | :--- | :--- |\n")
        for ext, count in sorted(stats["file_type_distribution"].items(), key=lambda x: x[1], reverse=True):
            pct = (count / stats['files_count'] * 100) if stats['files_count'] > 0 else 0
            f.write(f"| **.{ext.upper()}** | {count} | {pct:.1f}% |\n")
        f.write("\n")
        
        f.write("### 🍰 Graphical Suffix Breakdown\n\n")
        f.write("![File Type Distribution](file_types_distribution.png)\n\n")
        
        f.write("## 🧹 Data Cleanliness & Integrity Warnings\n\n")
        f.write("| Warning Indicator | Count | Status / Recommended Action |\n")
        f.write("| :--- | :--- | :--- |\n")
        
        # Empty files check
        empty_status = "🟢 Clean" if stats['empty_files_count'] == 0 else "⚠️ Review empty placeholders"
        f.write(f"| **Empty Files (0 Bytes)** | {stats['empty_files_count']} | {empty_status} |\n")
        
        # Long path check
        path_status = "🟢 Safe" if stats['long_paths_count_gt_260'] == 0 else "⚠️ Rename to avoid path overflow (>260 chars)"
        f.write(f"| **Long Path Warning** | {stats['long_paths_count_gt_260']} | {path_status} |\n")
        
        # Duplicate name check
        dup_status = "🟢 Clean" if stats['duplicate_files_count'] == 0 else "⚠️ Resolve redundant file naming"
        f.write(f"| **Duplicate Filenames** | {stats['duplicate_files_count']} | {dup_status} |\n\n")
        
        f.write("## 📅 Lifecycle Modifications\n\n")
        f.write(f"* **Oldest File Modified Timestamp**: `{stats['oldest_modified']}`\n")
        f.write(f"* **Newest File Modified Timestamp**: `{stats['newest_modified']}`\n\n")
        f.write("### 📊 Graphical Timeline of File Modifications\n\n")
        f.write("![Last Modified Date Distribution](last_modified_distribution.png)\n")

def plot_last_modified_distribution(last_modified_times: list, output_img_path: str):
    """Plots the distribution of last modified dates and saves it as a PNG image."""
    import matplotlib.pyplot as plt
    from collections import Counter
    from datetime import datetime
    
    dates = []
    for dt_str in last_modified_times:
        try:
            # Extract just the YYYY-MM-DD date part
            dt = datetime.strptime(dt_str.split("T")[0], "%Y-%m-%d")
            dates.append(dt.strftime("%Y-%m-%d"))
        except Exception:
            pass
            
    if not dates:
        return
        
    # Group and sort by date chronologically
    date_counts = Counter(dates)
    sorted_dates = sorted(date_counts.keys())
    counts = [date_counts[d] for d in sorted_dates]
    
    # Plotting
    plt.figure(figsize=(10, 5))
    plt.bar(sorted_dates, counts, color='#3B82F6', edgecolor='#2563EB', alpha=0.85)
    plt.title("Distribution of File Modifications by Date", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Date (YYYY-MM-DD)", fontsize=11, labelpad=10)
    plt.ylabel("Number of Files Modified", fontsize=11, labelpad=10)
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    
    # Save image
    plt.savefig(output_img_path, dpi=150)
    plt.close()

def plot_file_types_distribution(file_type_dist: dict, output_img_path: str):
    """Plots a pie chart of file type distributions."""
    import matplotlib.pyplot as plt
    sorted_types = sorted(file_type_dist.items(), key=lambda x: x[1], reverse=True)
    labels = [f".{k.upper()}" for k, v in sorted_types]
    sizes = [v for k, v in sorted_types]
    
    # Soft curated color palette
    colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#6B7280', '#14B8A6']
    
    plt.figure(figsize=(7, 5.5))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors[:len(labels)], 
            wedgeprops={'edgecolor': 'white', 'linewidth': 1})
    plt.title("File Types (Suffix) Distribution", fontsize=14, fontweight='bold', pad=15)
    plt.tight_layout()
    plt.savefig(output_img_path, dpi=150)
    plt.close()

def plot_sensitivity_distribution(label_dist: dict, output_img_path: str):
    """Plots a horizontal bar chart of sensitivity labels."""
    import matplotlib.pyplot as plt
    
    sorted_labels = sorted(label_dist.items(), key=lambda x: x[1], reverse=False)
    labels = [k for k, v in sorted_labels]
    counts = [v for k, v in sorted_labels]
    
    colors = ['#9CA3AF' if 'unclassified' in l.lower() else '#10B981' if 'general' in l.lower() else '#F59E0B' for l in labels]
    
    plt.figure(figsize=(10, 4.5))
    plt.barh(labels, counts, color=colors, edgecolor='#4B5563', alpha=0.85)
    plt.title("Sensitivity Labels & Classifications", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Number of Files", fontsize=11, labelpad=10)
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(output_img_path, dpi=150)
    plt.close()

def plot_file_sizes_distribution(file_sizes: list, output_img_path: str):
    """Plots a histogram of file size distribution categories."""
    import matplotlib.pyplot as plt
    
    ranges = ["< 100 KB", "100 KB - 500 KB", "500 KB - 1 MB", "1 MB - 5 MB", "> 5 MB"]
    counts = [0, 0, 0, 0, 0]
    
    for s in file_sizes:
        kb = s / 1024.0
        if kb < 100:
            counts[0] += 1
        elif kb < 500:
            counts[1] += 1
        elif kb < 1024:
            counts[2] += 1
        elif kb < 5120:
            counts[3] += 1
        else:
            counts[4] += 1
            
    plt.figure(figsize=(10, 5))
    plt.bar(ranges, counts, color='#8B5CF6', edgecolor='#7C3AED', alpha=0.85)
    plt.title("File Size Distribution Categories", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Size Categories", fontsize=11, labelpad=10)
    plt.ylabel("Number of Files", fontsize=11, labelpad=10)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(output_img_path, dpi=150)
    plt.close()

def plot_principals_distribution(principal_dist: dict, output_img_path: str):
    """Plots a horizontal bar chart of the most highly-authorized principals on the SharePoint site."""
    import matplotlib.pyplot as plt
    sorted_principals = sorted(principal_dist.items(), key=lambda x: x[1], reverse=True)[:10]
    sorted_principals.reverse()
    
    labels = [k for k, v in sorted_principals]
    counts = [v for k, v in sorted_principals]
    
    plt.figure(figsize=(10, 5))
    plt.barh(labels, counts, color='#EAB308', edgecolor='#CA8A04', alpha=0.85)
    plt.title("Top Access-Authorized Principals (Explicit Access count)", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Number of Files with Explicit Access Granted", fontsize=11, labelpad=10)
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(output_img_path, dpi=150)
    plt.close()

if __name__ == "__main__":
    analyze_sharepoint_contents()
