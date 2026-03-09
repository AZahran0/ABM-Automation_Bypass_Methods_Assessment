# ABM - Automation Bypass Methods Assessment

This repository contains three assessment scripts demonstrating different approaches to bypassing web automation detection and CAPTCHA systems.

## Overview

The project consists of three distinct tasks, each focusing on a different technique for handling automated web interactions:

1. **Task 1: Automation - Stealth Assessment** (`Task1.py`)
2. **Task 2: Network Interception** (`Task2.py`)
3. **Task 3: DOM Scraping Assessment** (`Task3.py`)

---

## Development Approach: Claude + Scrapling + MCP

This project was developed using **Claude AI** (Anthropic's AI assistant) in combination with **Scrapling** (stealth browser automation library) and **MCP (Model Context Protocol)** for enhanced development workflow.

### How It Works

**Claude AI** served as the primary development assistant, providing:
- Code generation and refactoring
- Problem-solving and debugging
- Architecture design and implementation guidance
- Documentation writing

**Scrapling** provided:
- Advanced stealth browser automation capabilities
- Cloudflare Turnstile solving (`solve_cloudflare=True`)
- Browser fingerprinting evasion at the C++ level
- Thread-safe execution patterns

**MCP (Model Context Protocol)** enabled:
- Enhanced context awareness for Claude
- Better understanding of project structure and dependencies
- Seamless integration between development tools and AI assistance
- Improved code generation with project-specific context

---

## Video Demonstrations

The following videos demonstrate the implementation and execution of each task:

### Task 1 Using Claude + MCP + Scrapling: Automation - Stealth Assessment

<!-- Replace with your video link -->
[![Task 1 Demo](https://img.youtube.com/vi/zq7joPt4mPc/maxresdefault.jpg)](https://youtu.be/zq7joPt4mPc)

**Description:** Demonstrates the hybrid Scrapling + Playwright approach for bypassing Cloudflare Turnstile with stealth capabilities.

---

### Task 2 Using Claude + MCP + Scrapling: Network Interception

<!-- Replace with your video link -->
[![Task 2 Demo](https://img.youtube.com/vi/VIDEO_ID_2/maxresdefault.jpg)](https://youtu.be/_9LF863FA8E)

**Description:** Shows the JavaScript interception technique to block Turnstile widget rendering and inject solved tokens.

---

### Task 3 Using Claude + MCP + Scrapling: DOM Scraping Assessment

<!-- Replace with your video link -->
[![Task 3 Demo](https://img.youtube.com/vi/VIDEO_ID_3/maxresdefault.jpg)](https://www.youtube.com/watch?v=VIDEO_ID_3)

**Description:** Demonstrates Selenium-based DOM scraping to extract CAPTCHA images and text instructions.

---

## Task 1: Automation - Stealth Assessment

**File:** `Task1.py`  
**Target:** Cloudflare Turnstile CAPTCHA bypass  
**Goal:** Achieve ≥60% success rate across 10 attempts  
**Video:**   
[![Task 1 Demo](https://img.youtube.com/vi/zq7joPt4mPc/maxresdefault.jpg)](https://youtu.be/zq7joPt4mPc)


### Approach

This task uses a **hybrid approach** combining Scrapling's stealth capabilities with Playwright for token extraction:

1. **Scrapling StealthyFetcher** (Thread Pool Execution)
   - Uses `StealthyFetcher.fetch()` with `solve_cloudflare=True` to automatically solve Turnstile
   - Runs in a separate thread pool to avoid sync/async conflicts
   - Handles browser fingerprinting and automation detection at the C++ level

2. **Playwright Token Extraction**
   - Loads the HTML content from Scrapling into a Playwright page
   - Extracts the solved Turnstile token using `page.evaluate()`
   - Extracts form fields (`first_name`, `last_name`) using Playwright's DOM API

3. **Form Submission**
   - Submits the form using `httpx.AsyncClient` with the extracted token
   - Validates success based on HTTP response status and content

### Key Features

- **10-attempt loop** with random delays (2-4 seconds) between attempts
- **Comprehensive error handling** with detailed exception logging
- **Success rate reporting** with pass/fail status for each attempt
- **Thread-safe execution** using `ThreadPoolExecutor` to isolate Scrapling's sync API

### Requirements

```bash
pip install playwright scrapling httpx
playwright install chromium
```

### Usage

```bash
python Task1.py
```

### Expected Output

- Individual attempt results with token previews
- Final report showing success rate (target: ≥60%)
- Detailed error messages for failed attempts

---

## Task 2: Network Interception

**File:** `Task2.py`  
**Target:** Cloudflare Turnstile CAPTCHA bypass via widget interception  
**Goal:** Intercept Turnstile widget initialization and inject a solved token
**Video:**   
[![Task 3 Demo](https://img.youtube.com/vi/VIDEO_ID_3/maxresdefault.jpg)](https://youtu.be/iXQB6R49Q6w)



### Approach

This task demonstrates **JavaScript interception** to block the Turnstile widget from rendering while capturing its parameters:

1. **Widget Interception** (Playwright Init Script)
   - Injects JavaScript **before** page load using `context.add_init_script()`
   - Intercepts `window.turnstile.render()` using `Object.defineProperty()`
   - **Blocks** the widget from rendering (never calls original `render()`)
   - Captures Turnstile parameters: `sitekey`, `action`, `cData`, `pagedata`

2. **Token Acquisition** (Scrapling + Playwright)
   - Uses Scrapling's `StealthyFetcher` in a thread pool to solve Turnstile
   - Extracts token from HTML using Playwright (same approach as Task 1)

3. **Token Injection & Submission**
   - Injects the solved token into the blocked widget's container
   - Creates a hidden input with `name="cf-turnstile-response"`
   - Submits the form and displays the result

### Key Features

- **Visible browser** for debugging and verification
- **Console message logging** to track interception events
- **DOM attribute fallback** if interception misses sitekey
- **10-second browser hold** to allow visual verification

### Technical Details

The interception script uses:
- `Object.defineProperty()` to intercept `window.turnstile` assignment
- Property setter/getter to capture render parameters
- **Never calls** the original `render()` function, effectively blocking widget display

### Requirements

```bash
pip install playwright scrapling beautifulsoup4
playwright install chromium
```

### Usage

```bash
python Task2.py
```

### Expected Output

- Interception confirmation with captured parameters
- Token extraction and injection status
- Final result message from the server

---

## Task 3: DOM Scraping Assessment

**File:** `Task3.py`  
**Target:** BLS Spain CAPTCHA page scraping  
**Goal:** Extract all images, visible grid images, and text instructions from CAPTCHA page  
**Video:**   
[![Task 3 Demo](https://img.youtube.com/vi/VIDEO_ID_3/maxresdefault.jpg)](https://www.youtube.com/watch?v=VIDEO_ID_3)



### Approach

This task uses **Selenium WebDriver** with JavaScript execution to scrape CAPTCHA content:

1. **Image Extraction** (JavaScript DOM Traversal)
   - Uses `document.querySelectorAll('.captcha-img')` to find all CAPTCHA images
   - Extracts base64-encoded image data from `img.src` attributes
   - Determines visibility using `getComputedStyle()` and `getBoundingClientRect()`
   - Identifies unique grid positions (3x3 grid) by position coordinates

2. **Text Extraction** (TreeWalker API)
   - Uses `document.createTreeWalker()` to traverse all text nodes
   - Filters visible text using CSS computed styles
   - Identifies active CAPTCHA instruction (e.g., "Please select all boxes with number NNN")

3. **Data Organization**
   - **All images**: Complete list with metadata (index, dimensions, position, visibility)
   - **Visible images only**: 9 unique grid cells with row/column positions
   - **Text instructions**: Active instruction and all visible text content

### Key Features

- **Robust error handling** with fallback extraction methods
- **Multiple output files**: Separate JSON files for different data types
- **Grid position mapping**: Automatically assigns row/column positions to visible images
- **Comprehensive debugging**: Shows element counts and page state if extraction fails

### Technical Details

- Uses **IIFE (Immediately Invoked Function Expression)** for JavaScript execution
- Handles edge cases: empty results, missing elements, timing issues
- Waits for lazy-loaded images with `time.sleep()` after element detection

### Requirements

```bash
pip install selenium webdriver-manager
```

Or manually install ChromeDriver if `webdriver-manager` is not available.

### Usage

```bash
# Basic usage
python Task3.py

# With custom URL
python Task3.py --url "YOUR_CAPTCHA_URL"

# Show browser window (for debugging)
python Task3.py --no-headless

# Custom output files
python Task3.py --out-all allimages.json --out-visible visible.json --out-text text.json
```

### Output Files

1. **`allimages.json`**: All CAPTCHA images with full metadata
2. **`visible_images_only.json`**: Only the 9 visible grid images with positions
3. **`visible_text_instructions.json`**: Text content including active instruction

### Expected Output

- Page loading confirmation
- Image count statistics
- Active CAPTCHA instruction
- File sizes and save confirmations

---

## Common Patterns & Best Practices

### Thread Pool Execution

Both Task 1 and Task 2 use `ThreadPoolExecutor` to run Scrapling's synchronous API in async contexts:

```python
from concurrent.futures import ThreadPoolExecutor

def sync_function():
    # Scrapling sync code here
    pass

async def async_wrapper():
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, sync_function)
    return result
```

### Error Handling

All tasks include comprehensive error handling:
- Try-except blocks around critical operations
- Detailed error messages with context
- Fallback methods when primary approaches fail
- Traceback printing for debugging

### Browser Configuration

- **Headless mode** for automation (Tasks 1 & 2)
- **Visible browser** for debugging (Task 2, Task 3 with `--no-headless`)
- Anti-detection flags: `--disable-blink-features=AutomationControlled`

---

## Dependencies

### Core Dependencies

```bash
playwright>=1.49.0
scrapling
httpx
selenium
webdriver-manager  # Optional, for automatic ChromeDriver management
 ```

### Installation

```bash
# Install Python packages
pip install playwright scrapling httpx selenium webdriver-manager beautifulsoup4

# Install Playwright browsers
playwright install chromium

# Install Scrapling dependencies (if needed)
scrapling install-pw
```

---

## Project Structure

```
ABM/
├── Task1.py          # Automation - Stealth Assessment
├── Task2.py          # Network Interception
├── Task3.py          # DOM Scraping Assessment
├── README.md         # This file
└── requirements.txt  # Python dependencies (if exists)
```

---

## Success Criteria

- **Task 1**: 100% success rate across 10 attempts

- **Task 2**: Successful token injection and form submission
- **Task 3**: Complete extraction of all images and text from CAPTCHA page

---

## Notes
- **Time-sensitive URLs**: Task 3's default URL contains a token that may expire. Replace with a fresh URL if needed.
- **Browser visibility**: Task 2 runs with visible browser by default for verification purposes.
- **Rate limiting**: Task 1 includes random delays between attempts to avoid server rate limiting.
- **Error recovery**: All tasks include fallback mechanisms and detailed error reporting.

---

## License

This project is for educational and assessment purposes only.
