"""
Turnstile Bypass Script
=======================
Uses Playwright (visible browser) + Scrapling to:
  1. Open the page and BLOCK the Turnstile widget from loading
  2. Capture Turnstile details (sitekey, action, cData, pagedata) from the DOM
  3. Use Scrapling's StealthyFetcher (solve_cloudflare=True) to get a fresh valid token
  4. Inject the token into the form and submit
  5. Print the final success message

Requirements:
    pip install playwright scrapling 
    playwright install chromium
    scrapling install-pw  # if scrapling needs its own playwright
"""

import asyncio
import re
# from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from playwright.async_api import async_playwright
from scrapling.fetchers import StealthyFetcher


# ─── CONFIG ───────────────────────────────────────────────────────────────────
TARGET_URL = "https://cd.captchaaiplus.com/turnstile.html"

# JavaScript injected BEFORE the page loads (initScript).
# Intercepts window.turnstile.render to:
#   - Capture sitekey, action, cData, pagedata
#   - BLOCK the widget from rendering (never calls original render)
INTERCEPT_SCRIPT = """
(function () {
    window.__turnstileDetails = {};

    // Intercept the turnstile global when it's first assigned
    let _internal = undefined;
    Object.defineProperty(window, 'turnstile', {
        configurable: true,
        enumerable: true,
        set(val) {
            if (val && typeof val.render === 'function') {
                const _origRender = val.render.bind(val);
                val.render = function (container, params) {
                    // Capture all params
                    window.__turnstileDetails = {
                        sitekey:    params.sitekey    || null,
                        action:     params.action     || null,
                        cData:      params.cData      || null,
                        pagedata:   params.pagedata   || params.chlPageData || null,
                        fullParams: JSON.stringify(params),
                    };
                    console.log('[INTERCEPT] turnstile.render BLOCKED');
                    console.log('[SITEKEY]',  params.sitekey);
                    console.log('[ACTION]',   params.action   || 'N/A');
                    console.log('[CDATA]',    params.cData    || 'N/A');
                    console.log('[PAGEDATA]', params.pagedata || params.chlPageData || 'N/A');

                    // *** DO NOT call _origRender — widget is blocked ***
                    return 'intercepted-widget-id';
                };
            }
            _internal = val;
        },
        get() { return _internal; }
    });
})();
"""


# ─── STEP 1 & 2: Open page in visible Playwright browser, block Turnstile ─────
async def open_and_intercept():
    """
    Launch a visible Chromium browser, inject the intercept script,
    navigate to the target URL, then extract Turnstile details from the DOM.
    Returns: (page, browser, playwright_instance, details_dict)
    """
    print("\n[1/4] Launching visible browser with Turnstile intercept...")

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=False, slow_mo=100)
    context = await browser.new_context()

    # Inject intercept script so it runs BEFORE any page JS
    await context.add_init_script(INTERCEPT_SCRIPT)

    page = await context.new_page()

    # Listen to console messages from the page
    page.on("console", lambda msg: print(f"  [browser console] {msg.text}"))

    await page.goto(TARGET_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)  # let scripts settle

    # ── Capture details from window.__turnstileDetails (set by intercept) ──
    details = await page.evaluate("() => window.__turnstileDetails")

    # Fallback: read sitekey directly from the DOM attribute
    if not details.get("sitekey"):
        sitekey = await page.get_attribute("[data-sitekey]", "data-sitekey")
        details["sitekey"] = sitekey

    # Also read any other data-* attributes from .cf-turnstile element
    dom_attrs = await page.evaluate("""
        () => {
            const el = document.querySelector('.cf-turnstile');
            if (!el) return {};
            const attrs = {};
            for (const a of el.attributes) attrs[a.name] = a.value;
            return attrs;
        }
    """)

    details["dom_attributes"] = dom_attrs

    print("\n" + "═" * 55)
    print("  ✅  TURNSTILE WIDGET BLOCKED — Details Captured:")
    print("═" * 55)
    print(f"  Sitekey  : {details.get('sitekey')}")
    print(f"  Action   : {details.get('action')   or 'N/A (not set)'}")
    print(f"  cData    : {details.get('cData')    or 'N/A (not set)'}")
    print(f"  Pagedata : {details.get('pagedata') or 'N/A (not set)'}")
    print(f"  DOM attrs: {dom_attrs}")
    print("═" * 55 + "\n")

    return page, browser, pw, details


# ─── STEP 3: Use Scrapling StealthyFetcher to solve Turnstile & get token ─────
def solve_and_get_token_sync() -> str:
    """
    Synchronous function to run Scrapling in a separate thread.
    Uses Scrapling's StealthyFetcher with solve_cloudflare=True.
    Returns the HTML content for Playwright to extract the token.
    """
    response = StealthyFetcher.fetch(
        url=TARGET_URL,
        headless=True,
        network_idle=True,
        solve_cloudflare=True,
        wait=3000,
        extraction_type="html",
    )

    # Get HTML content - match task1_scrapling.py approach
    if hasattr(response, "html_content"):
        html = response.html_content
    elif hasattr(response, "html"):
        html = response.html
    else:
        raise RuntimeError(f"❌ Could not access HTML content! Available attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")

    # Ensure html is a string (not a list)
    if isinstance(html, list) and len(html) > 0:
        html = html[0]
    if not isinstance(html, str):
        html = str(html)

    return html


async def solve_and_get_token() -> str:
    """
    Async wrapper that runs Scrapling in a thread pool to avoid sync/async conflict.
    Uses Scrapling's StealthyFetcher with solve_cloudflare=True.
    Uses Playwright to extract the token from HTML (like task1_scrapling.py).
    Returns the token string.
    """
    print("[2/4] Using Scrapling StealthyFetcher to solve Turnstile...")

    # Run Scrapling in a thread pool to avoid blocking the async loop
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        html = await loop.run_in_executor(executor, solve_and_get_token_sync)

    print("  ✔ Page fetched and Turnstile solved by Scrapling")

    # Extract token using Playwright (same approach as task1_scrapling.py)
    print("  [*] Extracting token using Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        pw_page = await context.new_page()

        # Load the HTML content that Scrapling fetched
        await pw_page.set_content(html, wait_until="domcontentloaded")

        # Extract the solved Turnstile token using Playwright
        token = await pw_page.evaluate("""
            () => {
                const el = document.querySelector('input[name="cf-turnstile-response"]');
                return (el && el.value && el.value.length > 20) ? el.value : null;
            }
        """)

        await browser.close()

    if not token:
        raise RuntimeError("❌ Could not extract Turnstile token from Scrapling response!")

    print(f"  ✅ Fresh token obtained! (length: {len(token)})")
    print(f"\n  Token:\n  {token[:80]}...{token[-20:]}\n")
    return token


# ─── STEP 4: Inject token into the Playwright page and submit ─────────────────
async def inject_and_submit(page, token: str):
    """
    Injects the solved token into the form's hidden input and clicks Submit.
    Waits for the result message and prints it.
    """
    print("[3/4] Injecting fresh token into the page form...")

    # Pass token as argument to avoid JavaScript syntax errors with special characters
    inject_result = await page.evaluate("""
        (token) => {
            // Remove any stale injected input
            const old = document.getElementById('cf-turnstile-injected');
            if (old) old.remove();

            // Find the .cf-turnstile container and append hidden input
            const container = document.querySelector('.cf-turnstile');
            if (!container) return 'ERROR: .cf-turnstile not found';

            const input = document.createElement('input');
            input.type  = 'hidden';
            input.name  = 'cf-turnstile-response';
            input.id    = 'cf-turnstile-injected';
            input.value = token;
            container.appendChild(input);

            return `Injected — input name="${input.name}", length=${token.length}`;
        }
    """, token)
    print(f"  {inject_result}")

    print("[4/4] Clicking Submit...")
    await page.click('input[type="submit"], button[type="submit"], #turnstile-form button, button:has-text("Submit")')
    await page.wait_for_timeout(2000)

    # Read the result message
    result_text = await page.evaluate("""
        () => {
            const el = document.getElementById('result');
            return el ? el.innerText.trim() : null;
        }
    """)

    print("\n" + "═" * 55)
    if result_text:
        print(f"  Result: {result_text}")
    else:
        # Fallback — grab any visible result text
        body_text = await page.inner_text("body")
        result_match = re.search(r"(✅|❌)[^\n]+", body_text)
        print(f"  Result: {result_match.group(0) if result_match else 'No result found'}")
    print("═" * 55 + "\n")

    return result_text


# ─── MAIN ─────────────────────────────────────────────────────────────────────
async def main():
    print("=" * 55)
    print("  Turnstile Intercept + Bypass Script")
    print(f"  Target: {TARGET_URL}")
    print("=" * 55)

    # Step 1 & 2: Open page with interception (visible browser)
    page, browser, pw, details = await open_and_intercept()

    # Step 3: Solve captcha via Scrapling (separate headless browser)
    token = await solve_and_get_token()

    # Step 4: Inject + Submit on the visible browser
    result = await inject_and_submit(page, token)

    # Keep browser open so user can see the result
    print("  Browser will stay open for 10 seconds so you can see the result...")
    await page.wait_for_timeout(10_000)

    # Cleanup
    await browser.close()
    await pw.stop()

    print("Done ✅")
    return {
        "sitekey": details.get("sitekey"),
        "action": details.get("action"),
        "cData": details.get("cData"),
        "pagedata": details.get("pagedata"),
        "token": token,
        "result": result,
    }


if __name__ == "__main__":
    asyncio.run(main())