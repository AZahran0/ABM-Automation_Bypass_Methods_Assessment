import asyncio
import random
import httpx
from concurrent.futures import ThreadPoolExecutor
from scrapling.fetchers import StealthyFetcher
from playwright.async_api import async_playwright

TARGET_URL = "https://cd.captchaaiplus.com/turnstile.html"
VERIFY_URL = "https://cd.captchaaiplus.com/turnstile-verify.php"
TOTAL_RUNS = 10  # Number of attempts to make


def fetch_with_scrapling():
    """Synchronous function to run Scrapling in a separate thread"""
    page = StealthyFetcher.fetch(
        url=TARGET_URL,
        headless=False,          # visible browser
        solve_cloudflare=True,   # auto-solve Turnstile
        network_idle=True,       # wait until network is idle
        wait=5000,               # extra 5 s for the token to populate
        extraction_type="html",
        # main_content_only=False,
    )
    return page.html_content


async def run_one_attempt(attempt_number: int) -> dict:
    """
    Runs one complete attempt: fetch with Scrapling, extract token with Playwright, submit form.
    Returns a dict with keys: success (bool), token (str), message (str)
    """
    print(f"\n{'='*55}")
    print(f"  Attempt #{attempt_number}")
    print(f"{'='*55}")

    result = {"success": False, "token": None, "message": ""}

    try:
        # ── Step 1: Fetch the page and solve the Cloudflare Turnstile with Scrapling ──
        print("[*] Fetching page and solving Turnstile with Scrapling StealthyFetcher...")

        # Run Scrapling in a thread pool to avoid blocking the async loop
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            html = await loop.run_in_executor(executor, fetch_with_scrapling)

        print("  ✔ Page fetched and Turnstile solved by Scrapling")

        # ── Step 2: Use Playwright to extract token from the HTML ──────────────────────
        print("[*] Extracting token using Playwright...")

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

            if not token:
                result["message"] = "Turnstile token not found"
                print("  ❌ Token not found")
                await browser.close()
                return result

            print(f"[+] Turnstile token obtained ({len(token)} chars):")
            print(f"    {token[:80]}...")
            result["token"] = token

            # ── Step 3: Extract form fields using Playwright ────────────────────────────
            first_name = await pw_page.input_value('input[name="first_name"]')
            last_name = await pw_page.input_value('input[name="last_name"]')

            await browser.close()

        print(f"\n[*] Submitting form as: {first_name} {last_name}")

        # ── Step 4: Submit the form ───────────────────────────────────────────────
        async with httpx.AsyncClient() as client:
            response = await client.post(
                VERIFY_URL,
                data={
                    "first_name":           first_name,
                    "last_name":            last_name,
                    "cf-turnstile-response": token,
                },
            )

        # ── Step 5: Check the result ───────────────────────────────────────────────
        response_text = response.text.strip()
        print(f"\n[+] Server response ({response.status_code}):")
        print(f"    {response_text}")

        if response.status_code == 200 and "success" in response_text.lower():
            result["success"] = True
            result["message"] = response_text
            print("  🎉 SUCCESS!")
        else:
            result["message"] = response_text
            print("  ❌ FAIL")

    except Exception as e:
        result["message"] = f"Exception: {e}"
        print(f"  ❌ Exception: {e}")
        import traceback
        traceback.print_exc()

    return result


async def main():
    print("\n" + "█"*55)
    print("  CLOUDFLARE TURNSTILE BYPASS — 10-attempt test")
    print("  Using Scrapling + Playwright")
    print("█"*55)
    print(f"  URL  : {TARGET_URL}")
    print(f"  Runs : {TOTAL_RUNS}")

    results = []

    for i in range(1, TOTAL_RUNS + 1):
        res = await run_one_attempt(i)
        results.append(res)

        # Small gap between runs so we don't hammer the server
        if i < TOTAL_RUNS:
            gap = random.uniform(2, 4)
            print(f"\n  ⏳ Waiting {gap:.1f}s before next attempt …")
            await asyncio.sleep(gap)

    # ── Final report ──────────────────────────────
    successes = sum(1 for r in results if r["success"])
    rate = (successes / TOTAL_RUNS) * 100

    print("\n" + "═"*55)
    print("  FINAL REPORT")
    print("═"*55)
    for idx, r in enumerate(results, 1):
        status = "✅ PASS" if r["success"] else "❌ FAIL"
        token_preview = (r["token"][:40] + "…") if r["token"] else "N/A"
        print(f"  Attempt {idx:2d}: {status}  | token: {token_preview}")
    print("─"*55)
    print(f"  Successes : {successes} / {TOTAL_RUNS}")
    print(f"  Success % : {rate:.0f}%  {'✅ PASSED (≥60%)' if rate >= 60 else '❌ BELOW TARGET'}")
    print("═"*55)


if __name__ == "__main__":
    asyncio.run(main())