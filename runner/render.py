"""Prompt rendering utilities using Jinja2 and YAML."""

import yaml
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from typing import Dict, Any


def load_product_yaml(product_path: Path) -> Dict[str, Any]:
    """Load and parse a product YAML file.

    Args:
        product_path: Path to the product YAML file

    Returns:
        Dictionary containing product data

    Raises:
        FileNotFoundError: If product file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    if not product_path.exists():
        raise FileNotFoundError(f"Product file not found: {product_path}")

    with open(product_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_jinja_env(templates_dir: Path) -> Environment:
    """Create a Jinja2 environment with strict undefined handling.

    Args:
        templates_dir: Directory containing Jinja2 templates

    Returns:
        Configured Jinja2 Environment
    """
    if not templates_dir.exists():
        raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_prompt(
    product_data: Dict[str, Any],
    template_name: str,
    jinja_env: Environment,
    trap_flag: bool = False,
) -> str:
    """Render a prompt template with product data.

    Args:
        product_data: Dictionary containing product information
        template_name: Name of the Jinja2 template file
        jinja_env: Configured Jinja2 Environment
        trap_flag: Whether to enable the people-pleasing trap

    Returns:
        Rendered prompt as a string

    Raises:
        jinja2.TemplateNotFound: If template doesn't exist
        jinja2.UndefinedError: If required variables are missing
    """
    template = jinja_env.get_template(template_name)

    # Merge product data with trap_flag
    context = dict(product_data)
    context["trap_flag"] = trap_flag

    return template.render(**context)
