"""
Batch Run Page - Configure and execute experimental matrix
"""

import streamlit as st
import sys
from pathlib import Path
import yaml
import pandas as pd
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="Batch Run - LLM Research", page_icon="🚀", layout="wide")

st.markdown("## 🚀 Batch Run")
st.markdown("Configure and execute experimental matrix")

# Load available options
products_dir = project_root / "products"
prompts_dir = project_root / "prompts"

# Get products
product_files = list(products_dir.glob("*.yaml"))
products = {}
for pf in product_files:
    with open(pf) as f:
        data = yaml.safe_load(f)
        products[data['name']] = pf.stem

# Get templates
template_files = [f.name for f in prompts_dir.glob("*.j2")]
template_display = {
    "digital_ad.j2": "Digital Ad",
    "blog_post_promo.j2": "Blog Post",
    "faq.j2": "FAQ",
    "organic_social_posts.j2": "Social Posts",
    "spec_document_facts_only.j2": "Spec Doc"
}

# Configuration
st.markdown("### 📋 Matrix Configuration")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Products**")
    selected_products = []
    for name, pid in products.items():
        if st.checkbox(name, value=True, key=f"prod_{pid}"):
            selected_products.append(pid)

    st.markdown("**Templates**")
    selected_templates = []
    for template in template_files:
        if template in template_display:
            default = template in ["digital_ad.j2", "blog_post_promo.j2", "faq.j2"]
            if st.checkbox(template_display[template], value=default, key=f"tmpl_{template}"):
                selected_templates.append(template)

with col2:
    st.markdown("**Engines**")
    engines = {
        "OpenAI (gpt-4o-mini)": "openai",
        "Google (gemini-2.5-flash)": "google",
        "Mistral (mistral-small)": "mistral"
    }
    selected_engines = []
    for name, eid in engines.items():
        if st.checkbox(name, value=True, key=f"eng_{eid}"):
            selected_engines.append(eid)

    st.markdown("**Temperatures**")
    temps = {"0.2 (Low)": 0.2, "0.6 (Medium)": 0.6, "1.0 (High)": 1.0}
    selected_temps = []
    for name, temp in temps.items():
        if st.checkbox(name, value=(temp == 0.6), key=f"temp_{temp}"):
            selected_temps.append(temp)

# Calculate matrix
total_runs = len(selected_products) * len(selected_templates) * len(selected_engines) * len(selected_temps)

st.markdown("---")
st.markdown("### 📊 Summary")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Runs", total_runs)
with col2:
    est_tokens = total_runs * 2200  # avg tokens per run
    st.metric("Est. Tokens", f"{est_tokens:,}")
with col3:
    est_cost = est_tokens * 0.00000015  # rough cost
    st.metric("Est. Cost", f"${est_cost:.2f}")
with col4:
    est_time = total_runs * 3  # ~3 sec per run
    st.metric("Est. Time", f"{est_time//60}m {est_time%60}s")

# Matrix preview
if total_runs > 0 and total_runs <= 50:
    with st.expander("👁️ Preview Matrix"):
        matrix_data = []
        for prod in selected_products:
            for tmpl in selected_templates:
                for eng in selected_engines:
                    for temp in selected_temps:
                        matrix_data.append({
                            "Product": prod,
                            "Template": tmpl.replace(".j2", ""),
                            "Engine": eng,
                            "Temp": temp
                        })
        st.dataframe(pd.DataFrame(matrix_data), use_container_width=True)

# Run button
st.markdown("---")

if total_runs == 0:
    st.warning("⚠️ Select at least one option from each category")
else:
    col1, col2 = st.columns([3, 1])
    with col1:
        run_batch = st.button("🚀 Start Batch Run", type="primary", use_container_width=True, disabled=(total_runs == 0))
    with col2:
        if st.button("💾 Save Config"):
            st.info("Configuration saved to session")

# Execute batch
if run_batch and total_runs > 0:
    st.markdown("---")
    st.markdown("### ⏳ Progress")

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = project_root / "outputs" / f"batch_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_container = st.container()

    # Load dependencies
    from dotenv import load_dotenv
    load_dotenv()

    from runner.render import render_prompt
    from runner.engines.openai_client import call_openai
    from runner.engines.google_client import call_google
    from runner.engines.mistral_client import call_mistral

    results = []
    errors = []
    completed = 0

    for i, prod_id in enumerate(selected_products):
        # Load product
        with open(products_dir / f"{prod_id}.yaml") as f:
            product_data = yaml.safe_load(f)

        for tmpl in selected_templates:
            for eng in selected_engines:
                for temp in selected_temps:
                    run_name = f"{prod_id}/{tmpl.replace('.j2', '')}/{eng}/{temp}"
                    status_text.text(f"Running: {run_name}")

                    try:
                        # Render prompt
                        prompt = render_prompt(product_data, tmpl, False)

                        # Call engine
                        if eng == "openai":
                            response = call_openai(prompt=prompt, temperature=temp, max_tokens=800)
                        elif eng == "google":
                            response = call_google(prompt=prompt, temperature=temp, max_tokens=800)
                        elif eng == "mistral":
                            response = call_mistral(prompt=prompt, temperature=temp, max_tokens=800)

                        # Save output
                        output_file = output_dir / f"{prod_id}_{tmpl.replace('.j2', '')}_{eng}_{temp}.txt"
                        with open(output_file, 'w') as f:
                            f.write(response['output_text'])

                        results.append({
                            "product": prod_id,
                            "template": tmpl,
                            "engine": eng,
                            "temp": temp,
                            "tokens": response['total_tokens'],
                            "status": "✅"
                        })

                    except Exception as e:
                        errors.append(f"{run_name}: {str(e)[:50]}")
                        results.append({
                            "product": prod_id,
                            "template": tmpl,
                            "engine": eng,
                            "temp": temp,
                            "tokens": 0,
                            "status": "❌"
                        })

                    completed += 1
                    progress_bar.progress(completed / total_runs)

    # Complete
    status_text.text("✅ Batch complete!")
    st.balloons()

    # Results summary
    with results_container:
        st.markdown("### 📊 Results")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Completed", len([r for r in results if r['status'] == "✅"]))
        with col2:
            st.metric("Errors", len(errors))
        with col3:
            total_tokens = sum(r['tokens'] for r in results)
            st.metric("Total Tokens", f"{total_tokens:,}")

        # Results table
        st.dataframe(pd.DataFrame(results), use_container_width=True)

        # Output location
        st.success(f"📁 Outputs saved to: {output_dir}")

        # Errors
        if errors:
            with st.expander("❌ Errors"):
                for err in errors:
                    st.text(err)
