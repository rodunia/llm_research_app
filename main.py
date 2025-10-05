# main.py
# This is the main script to run the LLM Research Application.

import os
import csv
import datetime
from dotenv import load_dotenv
import uuid
import openai
import google.generativeai as genai

# Import configurations from the config.py file
import config

# --- 1. INITIALIZATION AND SETUP ---

def initialize_app():
    """
    Loads environment variables and prepares the application to run.
    """
    print("Initializing application...")
    load_dotenv()
    # Check for API keys (configure what is available)
    openai_api_key = os.getenv("OPENAI_API_KEY")
    google_api_key = os.getenv("GOOGLE_API_KEY")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    any_key = False
    if openai_api_key:
        openai.api_key = openai_api_key
        any_key = True
    if google_api_key:
        genai.configure(api_key=google_api_key)
        any_key = True
    if anthropic_api_key:
        # Anthropic client is instantiated when used to avoid hard dependency at import time
        any_key = True

    if not any_key:
        print("ERROR: No API keys found. Set OPENAI_API_KEY, GOOGLE_API_KEY, or ANTHROPIC_API_KEY in your .env.")
        exit()

    loaded = [name for name, val in (
        ("OpenAI", openai_api_key),
        ("Google", google_api_key),
        ("Anthropic", anthropic_api_key),
    ) if val]
    print(f"API keys loaded for: {', '.join(loaded)}")


def setup_results_file(filename="data/results.csv"):
    """
    Creates the CSV results file with the correct headers if it doesn't exist.
    """
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    headers = [
        "session_id", "account_id", "run_timestamp", "repetition_id",
        "prompt_id", "prompt_text", "system_prompt", "conversation_id",
        "model_name", "model_version", "temperature", "max_tokens",
        "top_p", "frequency_penalty", "presence_penalty", "seed",
        "output_text", "finish_reason", "prompt_tokens",
        "completion_tokens", "total_tokens", "tags", "researcher_notes"
    ]
    if not os.path.exists(filename):
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        print(f"Results file '{filename}' created.")
    else:
        print(f"Results file '{filename}' already exists.")
    return filename


# --- 2. USER INTERACTION AND MENUS ---

def select_from_list(items_list, prompt_message, display_key=None):
    """
    Generic function to display a numbered list and get user selection.
    """
    print(prompt_message)
    for i, item in enumerate(items_list, 1):
        if display_key and isinstance(item, dict):
            print(f"[{i}] {item[display_key]}")
        else:
            print(f"[{i}] {item}")

    while True:
        try:
            choice = int(input("Enter number: "))
            if 1 <= choice <= len(items_list):
                return items_list[choice - 1]
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def get_session_info():
    """
    Prompts the researcher to enter a session ID and select a user account.
    """
    session_id = input("Enter a unique Session ID (e.g., evening_run_day1_gpt4): ")
    account_id = select_from_list(config.USER_ACCOUNTS, "\nSelect a User Account:")
    print("-" * 20)
    print(f"Session Started: session_id='{session_id}', account_id='{account_id}'")
    print("-" * 20)
    return session_id, account_id

# --- 3. LLM API INTEGRATION ---

def query_openai(model_config, prompt_config):
    """
    Sends a request to the OpenAI API and returns the parsed response.
    """
    try:
        messages = [
            {"role": "system", "content": prompt_config.get("system_prompt", "")},
            {"role": "user", "content": prompt_config["prompt_text"]}
        ]
        response = openai.chat.completions.create(
            model=model_config["model_name"],
            messages=messages,
            temperature=model_config["temperature"],
            top_p=model_config["top_p"],
            frequency_penalty=model_config["frequency_penalty"],
            presence_penalty=model_config["presence_penalty"],
            seed=model_config.get("seed")
        )
        return {
            "output_text": response.choices[0].message.content,
            "finish_reason": response.choices[0].finish_reason,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
    except Exception as e:
        print(f"An error occurred with the OpenAI API: {e}")
        return {"output_text": f"ERROR: {e}", "finish_reason": "error", "total_tokens": 0}


def query_google(model_config, prompt_config):
    """
    Sends a request to the Google Gemini API and returns the parsed response.
    """
    try:
        model = genai.GenerativeModel(model_config['model_name'])
        generation_config = genai.types.GenerationConfig(
            temperature=model_config["temperature"],
            max_output_tokens=model_config["max_tokens"],
            top_p=model_config["top_p"]
        )
        full_prompt = f"{prompt_config.get('system_prompt', '')}\n\n{prompt_config['prompt_text']}"
        response = model.generate_content(full_prompt, generation_config=generation_config)

        # Note: Gemini API v1 doesn't expose token counts in the same way.
        # We can calculate prompt tokens manually for a rough estimate.
        prompt_tokens = model.count_tokens(full_prompt).total_tokens
        completion_tokens = model.count_tokens(response.text).total_tokens

        return {
            "output_text": response.text,
            "finish_reason": str(response.candidates[0].finish_reason) if response.candidates else "unknown",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    except Exception as e:
        print(f"An error occurred with the Google API: {e}")
        return {"output_text": f"ERROR: {e}", "finish_reason": "error", "total_tokens": 0}


def query_anthropic(model_config, prompt_config):
    """
    Sends a request to the Anthropic Claude API and returns the parsed response.
    """
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        system_prompt = prompt_config.get("system_prompt", "")
        user_content = prompt_config["prompt_text"]
        response = client.messages.create(
            model=model_config["model_name"],
            temperature=model_config["temperature"],
            max_tokens=model_config["max_tokens"],
            top_p=model_config.get("top_p", 1.0),
            system=system_prompt if system_prompt else None,
            messages=[{"role": "user", "content": user_content}],
        )

        # Extract text content from response
        parts = []
        for part in response.content or []:
            if getattr(part, "type", None) == "text":
                parts.append(part.text)
            elif isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
        output_text = "".join(parts) if parts else ""

        # Usage tokens
        usage = getattr(response, "usage", None) or {}
        prompt_tokens = getattr(usage, "input_tokens", None) or usage.get("input_tokens", 0)
        completion_tokens = getattr(usage, "output_tokens", None) or usage.get("output_tokens", 0)

        finish = getattr(response, "stop_reason", None) or getattr(response, "stop_sequence", None) or "unknown"

        return {
            "output_text": output_text,
            "finish_reason": str(finish),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": (prompt_tokens or 0) + (completion_tokens or 0),
        }
    except Exception as e:
        print(f"An error occurred with the Anthropic API: {e}")
        return {"output_text": f"ERROR: {e}", "finish_reason": "error", "total_tokens": 0}


def query_llm(model_config, prompt_config):
    """
    Dispatcher function to call the correct LLM API based on the provider.
    """
    provider = model_config.get("provider")
    if provider == "openai":
        return query_openai(model_config, prompt_config)
    elif provider == "google":
        return query_google(model_config, prompt_config)
    elif provider == "anthropic":
        return query_anthropic(model_config, prompt_config)
    else:
        print(f"Unknown provider: {provider}. Please check config.py.")
        return {"output_text": f"ERROR: Unknown provider '{provider}'", "finish_reason": "error", "total_tokens": 0}

# --- 4. DATA COLLECTION AND SAVING ---

def save_to_csv(data_dict, filename):
    """
    Appends a new row of data to the specified CSV file.
    """
    with open(filename, mode='a', newline='', encoding='utf-8') as f:
        # Use the headers from setup_results_file to ensure order
        headers = [
            "session_id", "account_id", "run_timestamp", "repetition_id",
            "prompt_id", "prompt_text", "system_prompt", "conversation_id",
            "model_name", "model_version", "temperature", "max_tokens",
            "top_p", "frequency_penalty", "presence_penalty", "seed",
            "output_text", "finish_reason", "prompt_tokens",
            "completion_tokens", "total_tokens", "tags", "researcher_notes"
        ]
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writerow(data_dict)
    print("--- Data saved successfully ---")


def run_new_conversation(session_state, results_filename):
    """
    Handles the workflow for a new conversation by selecting a full model configuration.
    """
    print("\n--- New Conversation ---")
    session_state["conversation_id"] = str(uuid.uuid4())
    session_state["repetition_id"] = 1

    # Filter available models by API keys present
    available_providers = set()
    if os.getenv("OPENAI_API_KEY"): available_providers.add("openai")
    if os.getenv("GOOGLE_API_KEY"): available_providers.add("google")
    if os.getenv("ANTHROPIC_API_KEY"): available_providers.add("anthropic")
    config_names = [
        name for name, cfg in config.MODEL_CONFIGURATIONS.items()
        if cfg.get("provider") in available_providers
    ] or list(config.MODEL_CONFIGURATIONS.keys())
    chosen_config_name = select_from_list(config_names, "\nSelect a Model Configuration:")

    # --- Mode Temperature --- (override per run immediately after model selection)
    print("\n--- Mode Temperature ---")
    default_temp = config.MODEL_CONFIGURATIONS[chosen_config_name].get("temperature", 0.7)
    print(f"Default temperature: {default_temp}")
    print("Enter a value between 0.0 and 2.0, or press Enter to keep default.")
    while True:
        raw = input("Temperature: ").strip()
        if raw == "":
            chosen_temp = default_temp
            break
        try:
            t = float(raw)
        except ValueError:
            print("Temperature must be a number.")
            continue
        if 0.0 <= t <= 2.0:
            chosen_temp = t
            break
        print("Temperature must be between 0.0 and 2.0.")

    # Build final model config with per-run override using helper
    model_config = config.get_model_config(chosen_config_name, temperature=chosen_temp)

    prompt_config = select_from_list(config.STANDARDIZED_PROMPTS, "\nSelect a Prompt:", display_key='prompt_id')

    print("\n--- READY TO SEND ---")
    print(f"Configuration: {chosen_config_name}")
    print(f"Prompt ID: {prompt_config['prompt_id']} ('{prompt_config['prompt_text'][:40]}...')")
    confirm = input("Press ENTER to confirm and send, or type 'c' to cancel: ").lower()
    if confirm == 'c':
        print("Operation cancelled.")
        return

    print("\nQuerying the LLM...")
    llm_output = query_llm(model_config, prompt_config)

    print("--- RESPONSE ---")
    print(llm_output["output_text"])
    print("--- METRICS ---")
    print(f"Finish Reason: {llm_output['finish_reason']}, Token Usage: {llm_output['total_tokens']}")

    print("\n--- ANNOTATION ---")
    tags = input("Enter comma-separated tags (e.g., pass,induced-error): ")
    researcher_notes = input("Enter researcher notes (optional): ")

    data_to_save = {
        "session_id": session_state["session_id"],
        "account_id": session_state["account_id"],
        "run_timestamp": datetime.datetime.now().isoformat(),
        "repetition_id": session_state["repetition_id"],
        "prompt_id": prompt_config["prompt_id"],
        "prompt_text": prompt_config["prompt_text"],
        "system_prompt": prompt_config.get("system_prompt", ""),
        "conversation_id": session_state["conversation_id"],
        "model_name": model_config["model_name"],
        "model_version": model_config["model_version"],
        "temperature": model_config["temperature"],
        "max_tokens": model_config["max_tokens"],
        "top_p": model_config["top_p"],
        "frequency_penalty": model_config["frequency_penalty"],
        "presence_penalty": model_config["presence_penalty"],
        "seed": model_config.get("seed"),
        **llm_output, # Unpack the entire llm_output dictionary here
        "tags": tags,
        "researcher_notes": researcher_notes,
    }
    save_to_csv(data_to_save, results_filename)


# --- 5. MAIN APPLICATION LOGIC ---

def main():
    """
    The main function that orchestrates the application workflow.
    """
    print("Welcome to the LLM Research App!")
    initialize_app()
    results_filename = setup_results_file()

    session_id, account_id = get_session_info()
    session_state = {
        "session_id": session_id,
        "account_id": account_id,
        "conversation_id": None,
        "repetition_id": 1
    }

    while True:
        print("\nWhat's next?")
        print("[n] New Conversation")
        print("[q] Quit Session")
        choice = input("Enter your choice: ").lower()
        if choice == 'n':
            run_new_conversation(session_state, results_filename)
        elif choice == 'q':
            print("Quitting session. Goodbye!")
            break
        else:
            print("Invalid choice, please try again.")


if __name__ == "__main__":
    main()
