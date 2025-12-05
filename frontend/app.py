"""
LLM Research App - Frontend
Main entry point for Streamlit application
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Page configuration (must be first Streamlit command)
st.set_page_config(
    page_title="LLM Research App",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 1rem;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        border-radius: 0.5rem;
        padding: 1rem;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.5rem;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## 🔬 LLM Research App")
    st.markdown("---")

    # Quick stats (placeholder - will be dynamic)
    st.markdown("### 📈 Quick Stats")

    # Check for experiments.csv
    experiments_file = project_root / "results" / "experiments.csv"
    if experiments_file.exists():
        import pandas as pd
        df = pd.read_csv(experiments_file)
        total_runs = len(df)
        completed = len(df[df['status'] == 'completed'])
        pending = len(df[df['status'] == 'pending'])

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total", total_runs)
            st.metric("Pending", pending)
        with col2:
            st.metric("Done", completed)
            if total_runs > 0:
                st.metric("Progress", f"{completed/total_runs*100:.0f}%")
    else:
        st.info("No experiments yet")

    st.markdown("---")
    st.markdown("### 📚 Resources")
    st.markdown("- [Documentation](https://github.com/rodunia/llm_research_app)")
    st.markdown("- [Report Issue](https://github.com/rodunia/llm_research_app/issues)")

    st.markdown("---")
    st.markdown("### 🔍 Debug Info")
    st.caption(f"Project root: {project_root}")
    st.caption(f"Products dir: {(project_root / 'products').exists()}")
    st.caption(f"Prompts dir: {(project_root / 'prompts').exists()}")
    if (project_root / 'products').exists():
        yaml_files = list((project_root / 'products').glob('*.yaml'))
        st.caption(f"YAML files found: {len(yaml_files)}")
    if (project_root / 'prompts').exists():
        j2_files = list((project_root / 'prompts').glob('*.j2'))
        st.caption(f"Template files found: {len(j2_files)}")

# Main content - this is the home page (Test Run)
st.markdown('<p class="main-header">🧪 Test Run</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Run a single test with your enhanced prompts</p>', unsafe_allow_html=True)

# Load available products and templates
from pathlib import Path
import yaml

products_dir = project_root / "products"
prompts_dir = project_root / "prompts"

# Get product options
product_files = list(products_dir.glob("*.yaml"))
product_options = {}
for pf in product_files:
    with open(pf) as f:
        data = yaml.safe_load(f)
        product_options[data['name']] = pf.stem

# Get template options
template_files = [f.name for f in prompts_dir.glob("*.j2")]
template_display = {
    "digital_ad.j2": "Digital Ad (Facebook)",
    "blog_post_promo.j2": "Blog Post",
    "faq.j2": "FAQ",
    "organic_social_posts.j2": "Organic Social Posts",
    "spec_document_facts_only.j2": "Spec Document"
}

# Configuration section
st.markdown("### ⚙️ Configuration")

col1, col2 = st.columns(2)

with col1:
    # Product selector
    product_keys = list(product_options.keys())
    if not product_keys:
        st.error("No products found! Please ensure YAML files exist in the products/ directory.")
        st.stop()

    selected_product_name = st.selectbox(
        "Product",
        options=product_keys,
        help="Select a product to generate content for"
    )

    if not selected_product_name:
        st.stop()

    selected_product_id = product_options[selected_product_name]

    # Template selector
    available_templates = [t for t in template_files if t in template_display]
    if not available_templates:
        st.error("No templates found! Please ensure .j2 files exist in the prompts/ directory.")
        st.stop()

    selected_template = st.selectbox(
        "Template",
        options=available_templates,
        format_func=lambda x: template_display.get(x, x) if x else "Unknown",
        help="Select the type of marketing material to generate"
    )

with col2:
    # Engine selector
    engine_options = {
        "OpenAI (gpt-4o)": "openai",
        "Google (gemini-2.0-flash-exp)": "google",
        "Mistral (mistral-small-latest)": "mistral",
        "Anthropic (claude-3-opus)": "anthropic"
    }
    selected_engine_name = st.selectbox(
        "Engine",
        options=list(engine_options.keys()),
        help="Select the LLM provider"
    )
    selected_engine = engine_options[selected_engine_name]

    # Temperature
    temp_options = {
        "0.2 (Low - Deterministic)": 0.2,
        "0.6 (Medium - Balanced)": 0.6,
        "1.0 (High - Creative)": 1.0
    }
    selected_temp_name = st.selectbox(
        "Temperature",
        options=list(temp_options.keys()),
        index=1,  # Default to 0.6
        help="Controls randomness in output"
    )
    selected_temp = temp_options[selected_temp_name]

# Advanced options
with st.expander("🔧 Advanced Options"):
    col1, col2 = st.columns(2)
    with col1:
        trap_flag = st.checkbox(
            "Enable Trap Flag",
            value=False,
            help="Test if LLM follows compliance rules when given contradictory instructions"
        )
        max_tokens = st.number_input(
            "Max Tokens",
            min_value=100,
            max_value=2000,
            value=800,
            help="Maximum tokens for completion"
        )
    with col2:
        custom_temp = st.number_input(
            "Custom Temperature",
            min_value=0.0,
            max_value=2.0,
            value=selected_temp,
            step=0.1,
            help="Override temperature with custom value"
        )
        if custom_temp != selected_temp:
            selected_temp = custom_temp

# Estimate display
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Est. Prompt Tokens:** ~1,700")
with col2:
    st.markdown("**Est. Completion:** ~500")
with col3:
    st.markdown("**Est. Cost:** ~$0.003")

# Run button
st.markdown("---")
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    run_button = st.button("🧪 Run Test", type="primary", use_container_width=True)
with col2:
    if st.button("👁️ View Prompt", use_container_width=True):
        st.session_state['show_prompt'] = True
with col3:
    if st.button("📋 View YAML", use_container_width=True):
        st.session_state['show_yaml'] = True

# Show prompt preview
if st.session_state.get('show_prompt', False):
    with st.expander("📄 Prompt Preview", expanded=True):
        from runner.render import render_prompt
        product_path = products_dir / f"{selected_product_id}.yaml"
        with open(product_path) as f:
            product_data = yaml.safe_load(f)
        prompt = render_prompt(product_data, selected_template, trap_flag)
        st.code(prompt[:2000] + "..." if len(prompt) > 2000 else prompt, language="text")
        st.caption(f"Total length: {len(prompt)} characters")

# Show YAML preview
if st.session_state.get('show_yaml', False):
    with st.expander("📋 Product YAML", expanded=True):
        product_path = products_dir / f"{selected_product_id}.yaml"
        with open(product_path) as f:
            yaml_content = f.read()
        st.code(yaml_content, language="yaml")

# Run the test
if run_button:
    st.markdown("---")
    st.markdown("### 📤 Output")

    with st.spinner(f"Generating with {selected_engine_name}..."):
        try:
            # Load product
            product_path = products_dir / f"{selected_product_id}.yaml"
            with open(product_path) as f:
                product_data = yaml.safe_load(f)

            # Render prompt
            from runner.render import render_prompt
            prompt = render_prompt(product_data, selected_template, trap_flag)

            # Call appropriate engine
            from dotenv import load_dotenv
            load_dotenv()

            if selected_engine == "openai":
                from runner.engines.openai_client import call_openai
                response = call_openai(prompt=prompt, temperature=selected_temp, max_tokens=max_tokens)
            elif selected_engine == "google":
                from runner.engines.google_client import call_google
                response = call_google(prompt=prompt, temperature=selected_temp, max_tokens=max_tokens)
            elif selected_engine == "mistral":
                from runner.engines.mistral_client import call_mistral
                response = call_mistral(prompt=prompt, temperature=selected_temp, max_tokens=max_tokens)
            elif selected_engine == "anthropic":
                from runner.engines.anthropic_client import call_anthropic
                response = call_anthropic(prompt=prompt, temperature=selected_temp, max_tokens=max_tokens)

            # Store in session state
            st.session_state['last_output'] = response['output_text']
            st.session_state['last_response'] = response
            st.session_state['last_config'] = {
                'product': selected_product_name,
                'template': selected_template,
                'engine': selected_engine_name,
                'temperature': selected_temp
            }

            # Display success
            st.success(f"✅ Generated successfully in {response.get('finish_reason', 'complete')}")

            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Prompt Tokens", response['prompt_tokens'])
            with col2:
                st.metric("Completion Tokens", response['completion_tokens'])
            with col3:
                st.metric("Total Tokens", response['total_tokens'])
            with col4:
                st.metric("Model", response['model'].split('-')[0])

            # Output display
            st.markdown("#### Generated Content")
            st.markdown(response['output_text'])

            # Validation panel (for digital_ad)
            if selected_template == "digital_ad.j2":
                st.markdown("---")
                st.markdown("#### ✅ Validation")

                from analysis.metrics import validate_ad_format
                validation = validate_ad_format(response['output_text'])

                # Show format validity first
                if not validation['format_valid']:
                    st.warning("⚠️ Output format not recognized. Expected 'Headline:', 'Primary Text:', 'Description:' labels.")

                col1, col2, col3 = st.columns(3)
                with col1:
                    if validation['headline_length'] > 0:
                        hl_status = "✅" if not validation['headline_exceeds_limit'] else "❌"
                        st.markdown(f"**Headline:** {validation['headline_length']}/40 chars {hl_status}")
                    else:
                        st.markdown("**Headline:** Not found ⚠️")

                with col2:
                    if validation['primary_text_length'] > 0:
                        pt_status = "✅" if not validation['primary_text_exceeds_limit'] else "❌"
                        st.markdown(f"**Primary Text:** {validation['primary_text_length']}/125 chars {pt_status}")
                    else:
                        st.markdown("**Primary Text:** Not found ⚠️")

                with col3:
                    if validation['description_length'] > 0:
                        desc_status = "✅" if not validation['description_exceeds_limit'] else "❌"
                        st.markdown(f"**Description:** {validation['description_length']}/30 chars {desc_status}")
                    else:
                        st.markdown("**Description:** Not found ⚠️")

                # Show extracted content in expander for debugging
                with st.expander("🔍 View Extracted Sections"):
                    if validation['headline']:
                        st.markdown(f"**Headline ({validation['headline_length']} chars):** {validation['headline']}")
                    if validation['primary_text']:
                        st.markdown(f"**Primary Text ({validation['primary_text_length']} chars):** {validation['primary_text']}")
                    if validation['description']:
                        st.markdown(f"**Description ({validation['description_length']} chars):** {validation['description']}")

            # Action buttons
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button(
                    "💾 Download Output",
                    response['output_text'],
                    file_name=f"{selected_product_id}_{selected_template.replace('.j2', '')}_{selected_engine}.txt",
                    mime="text/plain"
                )
            with col2:
                if st.button("📋 Copy to Clipboard"):
                    st.code(response['output_text'])
                    st.info("Output displayed above - copy manually")
            with col3:
                # Save to outputs folder
                from datetime import datetime
                output_dir = project_root / "outputs" / "frontend_tests"
                output_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = output_dir / f"{selected_product_id}_{selected_template.replace('.j2', '')}_{timestamp}.txt"

                if st.button("💾 Save to File"):
                    with open(output_file, 'w') as f:
                        f.write(f"# {selected_product_name} - {selected_template}\n")
                        f.write(f"# Engine: {selected_engine_name}\n")
                        f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"# Tokens: {response['total_tokens']}\n")
                        f.write("=" * 70 + "\n\n")
                        f.write(response['output_text'])
                    st.success(f"Saved to: {output_file}")

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.exception(e)

# Display last output if exists
elif st.session_state.get('last_output'):
    st.markdown("---")
    st.markdown("### 📤 Last Output")
    st.info(f"From: {st.session_state['last_config']['product']} / {st.session_state['last_config']['template']} / {st.session_state['last_config']['engine']}")
    st.markdown(st.session_state['last_output'])
