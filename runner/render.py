"""Prompt rendering utilities using Jinja2 and YAML."""

import yaml
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from typing import Dict, Any


def load_product_yaml(path: Path) -> dict:
    """Load and parse a product YAML file.

    Args:
        path: Path to the product YAML file

    Returns:
        Dictionary containing product data

    Raises:
        FileNotFoundError: If product file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    if not path.exists():
        raise FileNotFoundError(f"Product file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def jinja_env(templates_dir: Path = None) -> Environment:
    """Create a Jinja2 environment with strict undefined handling.

    Args:
        templates_dir: Directory containing Jinja2 templates (default: project_root/prompts)

    Returns:
        Configured Jinja2 Environment

    Raises:
        FileNotFoundError: If templates directory doesn't exist
    """
    if templates_dir is None:
        # Use project root to find prompts directory
        project_root = Path(__file__).parent.parent
        templates_dir = project_root / "prompts"

    if not templates_dir.exists():
        raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_prompt(
    product_yaml: dict, template_name: str, trap_flag: bool
) -> str:
    """Render a prompt template with product data.

    Args:
        product_yaml: Dictionary containing product information
        template_name: Name of the Jinja2 template file
        trap_flag: Whether to enable the people-pleasing trap

    Returns:
        Rendered prompt as a string

    Raises:
        KeyError: If required keys are missing from product_yaml
        jinja2.TemplateNotFound: If template doesn't exist
        jinja2.UndefinedError: If required variables are missing in template
    """
    # Validate required keys
    required_keys = ["name", "region", "target_audience", "specs", "authorized_claims", "disclaimers"]
    missing_keys = [key for key in required_keys if key not in product_yaml]

    if missing_keys:
        raise KeyError(
            f"Product YAML missing required keys: {', '.join(missing_keys)}"
        )

    # Create environment and get template
    env = jinja_env()
    template = env.get_template(template_name)

    # Build context with required keys + trap_flag
    context = {
        "name": product_yaml["name"],
        "region": product_yaml["region"],
        "target_audience": product_yaml["target_audience"],
        "specs": product_yaml["specs"],
        "authorized_claims": product_yaml["authorized_claims"],
        "prohibited_or_unsupported_claims": product_yaml.get("prohibited_or_unsupported_claims", []),
        "disclaimers": product_yaml["disclaimers"],
        "trap_flag": trap_flag,
    }

    return template.render(**context)
