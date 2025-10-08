# Main.py Updates - LLM Research App

## Summary of Changes

The `main.py` file has been successfully updated to integrate with the new prompt rendering system (Jinja2 templates + product YAML files). All critical issues have been resolved.

## Changes Made

### 1. Fixed OpenAI API Parameter Issue ✓
- **Location**: `main.py:130`
- **Change**: Updated `max_tokens=` to `max_completion_tokens=` in the OpenAI API call
- **Reason**: OpenAI's newer models (gpt-4.1, gpt-5) require `max_completion_tokens` instead of `max_tokens`

### 2. Added Prompt Loading System ✓
- **New Functions**:
  - `load_prompt_index()`: Loads prompt index CSV from `results/prompts_index.csv`
  - `load_prompt_text()`: Loads actual prompt text from files in `outputs/prompts/`
- **Location**: Lines 74-112
- **Purpose**: Integrate with the new Jinja2 template-based prompt system

### 3. Updated `run_new_conversation()` Function ✓
- **Location**: Lines 373-513
- **Major Changes**:
  - Removed dependency on `config.STANDARDIZED_PROMPTS`
  - Now loads prompts from filesystem using prompt index
  - Displays prompts with metadata: `run_id | product_id | template | trap_flag`
  - Loads actual prompt text from `.txt` files
  - Stores additional metadata in database: `product_id`, `template`, `trap_flag`

### 4. Updated Database Schema ✓
- **File**: `core/storage.py`
- **New Fields Added**:
  - `product_id TEXT` - Product identifier (e.g., "supplement_melatonin")
  - `template TEXT` - Template name (e.g., "faq.j2")
  - `trap_flag TEXT` - Whether people-pleasing trap is enabled
- **Purpose**: Track experiment metadata from the new prompt system

### 5. Updated Section Numbers
- Renumbered comment sections to reflect new structure:
  - Section 2: Prompt Loading from New System
  - Section 3: User Interaction and Menus
  - Section 4: LLM API Integration
  - Section 5: Data Collection and Saving

## How the New System Works

1. **Prompt Generation** (done once):
   ```bash
   python -m runner.generate_matrix
   ```
   - Generates prompts from templates + product YAML files
   - Creates files in `outputs/prompts/`
   - Creates index CSV in `results/prompts_index.csv`

2. **Runtime Flow**:
   - App loads prompt index on startup
   - User selects from available prompts with rich metadata
   - Prompt text is loaded from file
   - Experiment results saved with full metadata tracking

3. **Prompt Selection UI**:
   ```
   [1] c1667084 | supplement_melatonin | digital_ad | trap=False
   [2] 122f06dc | supplement_melatonin | faq | trap=False
   [3] 2bc2ad38 | cryptocurrency_corecoin | digital_ad | trap=True
   ```

## Validation Results

✓ Prompt index loads successfully (30 prompts found)
✓ Prompt text files load correctly
✓ All imports and functions working
✓ Database schema updated
✓ OpenAI API parameter issue resolved

## Next Steps for Users

1. **Ensure prompts are generated**:
   ```bash
   python -m runner.generate_matrix
   ```

2. **Run the application**:
   ```bash
   python main.py
   ```

3. **Select prompts**: Choose from the new prompt list showing product/template metadata

## Breaking Changes

- Old `STANDARDIZED_PROMPTS` in `config.py` is no longer used by main.py
- Database schema changed (new columns added - backwards compatible)
- Prompt selection UI changed to show new metadata format

## Files Modified

1. `main.py` - Main application logic updated
2. `core/storage.py` - Database schema extended with new fields

