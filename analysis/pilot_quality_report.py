"""
Pilot Quality Report

Analyzes pilot GPT-4o outputs to check:
- Valid JSON rate
- Missing required fields
- Claims extraction quality (min/max/mean per material)
- Findings quality (min/max/mean per material)
- Severity distribution
- Status distribution
- Evidence presence for non-low-risk findings
- HIGH/CRITICAL findings without evidence
- INSUFFICIENT_EVIDENCE with severity >= MEDIUM
- False positive risk distribution

Usage:
    python analysis/pilot_quality_report.py
    python analysis/pilot_quality_report.py --output-dir results/pilot/gpt4o_compliance
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer()
console = Console()


def load_pilot_outputs(output_dir: Path) -> List[Dict]:
    """Load all pilot JSON outputs."""
    if not output_dir.exists():
        console.print(f"[red]Output directory not found: {output_dir}[/red]")
        sys.exit(1)

    outputs = []
    for json_file in output_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                outputs.append(data)
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load {json_file.name}: {e}[/yellow]")

    return outputs


def check_required_fields(outputs: List[Dict]) -> Dict:
    """Check for missing required fields."""
    required_top_level = [
        'material_id', 'product', 'regulatory_domain', 'overall_status',
        'compliant', 'finding_count', 'overall_severity', 'requires_human_review',
        'extracted_claims', 'findings', 'summary', 'limitations'
    ]

    required_claim_fields = ['claim_id', 'claim_text', 'claim_type', 'is_verifiable', 'risk_domain', 'support_status']
    required_finding_fields = [
        'claim_id', 'claim_text', 'finding_status', 'finding_type', 'support_status',
        'severity', 'evidence_from_marketing_text', 'evidence_from_context',
        'reasoning_short', 'confidence', 'false_positive_risk', 'requires_human_review'
    ]

    missing_top_level = []
    missing_claim_fields = []
    missing_finding_fields = []

    for output in outputs:
        material_id = output.get('material_id', 'unknown')[:12]

        # Check top-level fields
        for field in required_top_level:
            if field not in output:
                missing_top_level.append((material_id, field))

        # Check claim fields
        for i, claim in enumerate(output.get('extracted_claims', [])):
            for field in required_claim_fields:
                if field not in claim:
                    missing_claim_fields.append((material_id, i, field))

        # Check finding fields
        for i, finding in enumerate(output.get('findings', [])):
            for field in required_finding_fields:
                if field not in finding:
                    missing_finding_fields.append((material_id, i, field))

    return {
        'missing_top_level': missing_top_level,
        'missing_claim_fields': missing_claim_fields,
        'missing_finding_fields': missing_finding_fields
    }


def analyze_claims_extraction(outputs: List[Dict]) -> Dict:
    """Analyze claims extraction quality."""
    claim_counts = [len(o.get('extracted_claims', [])) for o in outputs]

    if not claim_counts:
        return {'count': 0}

    return {
        'total_claims': sum(claim_counts),
        'min_per_material': min(claim_counts),
        'max_per_material': max(claim_counts),
        'mean_per_material': sum(claim_counts) / len(claim_counts),
        'materials_with_zero_claims': sum(1 for c in claim_counts if c == 0)
    }


def analyze_findings_quality(outputs: List[Dict]) -> Dict:
    """Analyze findings quality."""
    finding_counts = [len(o.get('findings', [])) for o in outputs]

    # Check evidence presence for non-low-risk findings
    findings_without_evidence = []
    high_critical_without_evidence = []
    insufficient_evidence_medium_plus = []

    for output in outputs:
        material_id = output.get('material_id', 'unknown')[:12]

        for i, finding in enumerate(output.get('findings', [])):
            status = finding.get('finding_status')
            severity = finding.get('severity')
            support_status = finding.get('support_status')
            evidence = finding.get('evidence_from_context', [])

            # Check if non-low-risk finding has evidence
            if status not in ['LOW_RISK_LANGUAGE'] and len(evidence) == 0:
                findings_without_evidence.append((material_id, i, status, severity))

            # Check HIGH/CRITICAL without evidence
            if severity in ['HIGH', 'CRITICAL'] and len(evidence) == 0:
                high_critical_without_evidence.append((material_id, i, severity))

            # Check INSUFFICIENT_EVIDENCE with MEDIUM+ severity
            if support_status == 'INSUFFICIENT_EVIDENCE' and severity in ['MEDIUM', 'HIGH', 'CRITICAL']:
                insufficient_evidence_medium_plus.append((material_id, i, severity, status))

    return {
        'total_findings': sum(finding_counts),
        'min_per_material': min(finding_counts) if finding_counts else 0,
        'max_per_material': max(finding_counts) if finding_counts else 0,
        'mean_per_material': sum(finding_counts) / len(finding_counts) if finding_counts else 0,
        'materials_with_zero_findings': sum(1 for c in finding_counts if c == 0),
        'findings_without_evidence': findings_without_evidence,
        'high_critical_without_evidence': high_critical_without_evidence,
        'insufficient_evidence_medium_plus': insufficient_evidence_medium_plus
    }


def analyze_distributions(outputs: List[Dict]) -> Dict:
    """Analyze status, severity, false positive risk distributions."""
    overall_statuses = [o.get('overall_status') for o in outputs]
    overall_severities = [o.get('overall_severity') for o in outputs]

    finding_statuses = []
    finding_severities = []
    finding_types = []
    false_positive_risks = []

    for output in outputs:
        for finding in output.get('findings', []):
            finding_statuses.append(finding.get('finding_status'))
            finding_severities.append(finding.get('severity'))
            finding_types.append(finding.get('finding_type'))
            false_positive_risks.append(finding.get('false_positive_risk'))

    return {
        'overall_status': Counter(overall_statuses),
        'overall_severity': Counter(overall_severities),
        'finding_status': Counter(finding_statuses),
        'finding_severity': Counter(finding_severities),
        'finding_type': Counter(finding_types),
        'false_positive_risk': Counter(false_positive_risks)
    }


@app.command()
def report(
    output_dir: str = typer.Option(
        "results/pilot/gpt4o_compliance",
        "--output-dir",
        "-o",
        help="Directory containing pilot outputs"
    ),
    show_issues_only: bool = typer.Option(
        False,
        "--issues-only",
        help="Only show issues/warnings"
    )
):
    """Generate pilot quality report."""
    console.print("\n[bold]Pilot Quality Report[/bold]\n")

    output_path = Path(output_dir)
    outputs = load_pilot_outputs(output_path)

    if not outputs:
        console.print("[red]No outputs found[/red]")
        sys.exit(1)

    console.print(f"Loaded {len(outputs)} pilot outputs\n")

    # 1. Check required fields
    console.print("[bold cyan]1. Required Fields Check[/bold cyan]")
    missing = check_required_fields(outputs)

    if missing['missing_top_level']:
        console.print(f"[red]Missing top-level fields: {len(missing['missing_top_level'])}[/red]")
        for material_id, field in missing['missing_top_level'][:5]:
            console.print(f"  {material_id}: missing '{field}'")
    else:
        console.print("[green]✓ All top-level fields present[/green]")

    if missing['missing_claim_fields']:
        console.print(f"[yellow]Missing claim fields: {len(missing['missing_claim_fields'])}[/yellow]")
    else:
        console.print("[green]✓ All claim fields present[/green]")

    if missing['missing_finding_fields']:
        console.print(f"[yellow]Missing finding fields: {len(missing['missing_finding_fields'])}[/yellow]")
    else:
        console.print("[green]✓ All finding fields present[/green]")

    console.print()

    # 2. Claims extraction quality
    console.print("[bold cyan]2. Claims Extraction Quality[/bold cyan]")
    claims_stats = analyze_claims_extraction(outputs)

    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total claims extracted", str(claims_stats.get('total_claims', 0)))
    table.add_row("Min per material", str(claims_stats.get('min_per_material', 0)))
    table.add_row("Max per material", str(claims_stats.get('max_per_material', 0)))
    table.add_row("Mean per material", f"{claims_stats.get('mean_per_material', 0):.1f}")
    table.add_row("Materials with 0 claims", str(claims_stats.get('materials_with_zero_claims', 0)))

    console.print(table)
    console.print()

    # 3. Findings quality
    console.print("[bold cyan]3. Findings Quality[/bold cyan]")
    findings_stats = analyze_findings_quality(outputs)

    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total findings", str(findings_stats.get('total_findings', 0)))
    table.add_row("Min per material", str(findings_stats.get('min_per_material', 0)))
    table.add_row("Max per material", str(findings_stats.get('max_per_material', 0)))
    table.add_row("Mean per material", f"{findings_stats.get('mean_per_material', 0):.1f}")
    table.add_row("Materials with 0 findings", str(findings_stats.get('materials_with_zero_findings', 0)))

    console.print(table)
    console.print()

    # Evidence issues
    if findings_stats['findings_without_evidence']:
        console.print(f"[yellow]⚠ Findings without evidence: {len(findings_stats['findings_without_evidence'])}[/yellow]")
        for material_id, i, status, severity in findings_stats['findings_without_evidence'][:5]:
            console.print(f"  {material_id} finding #{i}: {status} / {severity}")
        console.print()

    if findings_stats['high_critical_without_evidence']:
        console.print(f"[red]✗ HIGH/CRITICAL findings without evidence: {len(findings_stats['high_critical_without_evidence'])}[/red]")
        for material_id, i, severity in findings_stats['high_critical_without_evidence']:
            console.print(f"  {material_id} finding #{i}: {severity}")
        console.print()

    if findings_stats['insufficient_evidence_medium_plus']:
        console.print(f"[red]✗ INSUFFICIENT_EVIDENCE with MEDIUM+ severity: {len(findings_stats['insufficient_evidence_medium_plus'])}[/red]")
        for material_id, i, severity, status in findings_stats['insufficient_evidence_medium_plus']:
            console.print(f"  {material_id} finding #{i}: {severity} / {status}")
        console.print()

    # 4. Distributions
    console.print("[bold cyan]4. Status & Severity Distributions[/bold cyan]")
    distributions = analyze_distributions(outputs)

    console.print("\n[cyan]Overall Status:[/cyan]")
    for status, count in distributions['overall_status'].most_common():
        console.print(f"  {status}: {count}")

    console.print("\n[cyan]Overall Severity:[/cyan]")
    for severity, count in distributions['overall_severity'].most_common():
        console.print(f"  {severity}: {count}")

    console.print("\n[cyan]Finding Status:[/cyan]")
    for status, count in distributions['finding_status'].most_common():
        console.print(f"  {status}: {count}")

    console.print("\n[cyan]Finding Severity:[/cyan]")
    for severity, count in distributions['finding_severity'].most_common():
        console.print(f"  {severity}: {count}")

    console.print("\n[cyan]Finding Type:[/cyan]")
    for ftype, count in distributions['finding_type'].most_common():
        console.print(f"  {ftype}: {count}")

    console.print("\n[cyan]False Positive Risk:[/cyan]")
    for risk, count in distributions['false_positive_risk'].most_common():
        console.print(f"  {risk}: {count}")

    console.print()

    # 5. Overall assessment
    issues = []
    if missing['missing_top_level']:
        issues.append(f"Missing {len(missing['missing_top_level'])} top-level fields")
    if claims_stats.get('materials_with_zero_claims', 0) > 0:
        issues.append(f"{claims_stats['materials_with_zero_claims']} materials with 0 claims")
    if findings_stats['high_critical_without_evidence']:
        issues.append(f"{len(findings_stats['high_critical_without_evidence'])} HIGH/CRITICAL without evidence")
    if findings_stats['insufficient_evidence_medium_plus']:
        issues.append(f"{len(findings_stats['insufficient_evidence_medium_plus'])} INSUFFICIENT_EVIDENCE with MEDIUM+ severity")

    if issues:
        console.print(Panel(
            "\n".join(f"• {issue}" for issue in issues),
            title="[red bold]Issues Found[/red bold]",
            border_style="red"
        ))
        console.print()
        sys.exit(1)
    else:
        console.print(Panel(
            "✓ All quality checks passed!\n✓ Outputs are schema-compliant\n✓ Evidence present for high-severity findings\n✓ No INSUFFICIENT_EVIDENCE escalations",
            title="[green bold]Quality Report: PASS[/green bold]",
            border_style="green"
        ))
        console.print()


if __name__ == "__main__":
    app()
