"""
Results Page - View and analyze completed runs
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="Results - LLM Research", page_icon="📊", layout="wide")

st.markdown("## 📊 Results")
st.markdown("View and analyze completed runs")

# Check for results
outputs_dir = project_root / "outputs"
experiments_file = project_root / "results" / "experiments.csv"

# Sidebar filters
st.sidebar.markdown("### 🔍 Filters")

# Find all output directories
output_dirs = [d for d in outputs_dir.iterdir() if d.is_dir()] if outputs_dir.exists() else []
output_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)

if output_dirs:
    dir_options = ["All"] + [d.name for d in output_dirs[:10]]
    selected_dir = st.sidebar.selectbox("Output Directory", dir_options)

    # File type filter
    file_types = st.sidebar.multiselect(
        "Template Types",
        ["digital_ad", "blog_post_promo", "faq", "organic_social_posts", "spec_document"],
        default=["digital_ad", "blog_post_promo", "faq"]
    )

    # Collect outputs
    output_files = []

    if selected_dir == "All":
        for d in output_dirs:
            output_files.extend(list(d.glob("*.txt")))
    else:
        selected_path = outputs_dir / selected_dir
        output_files = list(selected_path.glob("*.txt"))

    # Filter by type
    if file_types:
        filtered_files = []
        for f in output_files:
            for ft in file_types:
                if ft in f.name:
                    filtered_files.append(f)
                    break
        output_files = filtered_files

    # Sort by modification time
    output_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    # Stats
    st.markdown("### 📈 Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Outputs", len(output_files))
    with col2:
        # Count by type
        type_counts = {}
        for f in output_files:
            for ft in ["digital_ad", "blog_post", "faq"]:
                if ft in f.name:
                    type_counts[ft] = type_counts.get(ft, 0) + 1
                    break
        most_common = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else "N/A"
        st.metric("Most Common", most_common)
    with col3:
        if output_files:
            latest = output_files[0]
            latest_time = datetime.fromtimestamp(latest.stat().st_mtime)
            st.metric("Latest", latest_time.strftime("%H:%M"))

    st.markdown("---")

    # Results table
    st.markdown("### 📋 Output Files")

    if output_files:
        # Build table data
        table_data = []
        for f in output_files[:100]:  # Limit to 100
            # Parse filename
            parts = f.stem.split("_")
            product = parts[0] if len(parts) > 0 else "Unknown"
            template = parts[1] if len(parts) > 1 else "Unknown"

            # Get file info
            size = f.stat().st_size
            modified = datetime.fromtimestamp(f.stat().st_mtime)

            # Read word count
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read()
                word_count = len(content.split())

            table_data.append({
                "File": f.name,
                "Product": product,
                "Template": template,
                "Words": word_count,
                "Size": f"{size/1024:.1f} KB",
                "Modified": modified.strftime("%Y-%m-%d %H:%M"),
                "Path": str(f)
            })

        df = pd.DataFrame(table_data)

        # Display table with selection
        st.dataframe(
            df[["File", "Product", "Template", "Words", "Size", "Modified"]],
            use_container_width=True,
            hide_index=True
        )

        # File selector for preview
        st.markdown("---")
        st.markdown("### 👁️ Preview Output")

        selected_file = st.selectbox(
            "Select file to preview",
            options=[f.name for f in output_files[:50]],
            format_func=lambda x: x
        )

        if selected_file:
            # Find the file
            file_path = None
            for f in output_files:
                if f.name == selected_file:
                    file_path = f
                    break

            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Display content
                st.markdown(f"**File:** `{file_path}`")
                st.markdown(f"**Word Count:** {len(content.split())}")

                # Content display
                st.text_area("Content", content, height=400)

                # Actions
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.download_button(
                        "💾 Download",
                        content,
                        file_name=selected_file,
                        mime="text/plain"
                    )
                with col2:
                    if st.button("📋 Copy Path"):
                        st.code(str(file_path))
                with col3:
                    if st.button("🗑️ Delete", type="secondary"):
                        file_path.unlink()
                        st.success("File deleted")
                        st.rerun()

        # Export
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export Results to CSV"):
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    file_name=f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

    else:
        st.info("No output files found matching filters")

else:
    st.info("No output directories found. Run some tests first!")

    # Quick action
    if st.button("🧪 Go to Test Run"):
        st.switch_page("app.py")
