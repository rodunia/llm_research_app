# LLM Research App

A comprehensive research application for conducting systematic experiments with multiple LLM providers (OpenAI, Google Gemini, Anthropic Claude, Mistral AI).

## Features

- **Multi-Provider Testing**: Compare outputs from OpenAI GPT-4, Google Gemini 2.0, Claude 3 Opus, and Mistral
- **Product Marketing Generation**: Generate various marketing materials (ads, social posts, FAQs, blog posts)
- **Batch Processing**: Run systematic experiments with controlled parameters
- **Results Tracking**: CSV-based storage for easy analysis

## Setup

### Required API Keys

Set these as environment variables or Hugging Face Secrets:

- `OPENAI_API_KEY` - OpenAI API key
- `GOOGLE_API_KEY` - Google AI Studio API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `MISTRAL_API_KEY` - Mistral API key

### Local Installation

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Usage

The app provides three main interfaces:

1. **Test Run**: Single LLM generation with real-time output
2. **Batch Run**: Execute multiple experiments with different parameters
3. **Results**: View and analyze experimental data

## Product Types

- **Supplement (Melatonin)**: Low-risk health/wellness product
- **Cryptocurrency (CoreCoin)**: High-risk financial product
- **Smartphone**: Medium-risk technology product

Each product has compliance requirements, mandatory statements, and authorized claims.

## Technical Stack

- **Frontend**: Streamlit
- **LLM Providers**: OpenAI, Google, Anthropic, Mistral
- **Template Engine**: Jinja2
- **Storage**: CSV (experiments.csv)
- **Configuration**: YAML + Python config

## License

MIT
