"""
BLS Spain CAPTCHA Scraper
=========================
Scrapes the CAPTCHA page at egypt.blsspainglobal.com and saves:
  - allimages.json        : All 100+ images as base64
  - visible_images_only.json : The 9 currently visible grid images as base64
  - visible_text_instructions.json : All visible text / instructions on the page

Requirements:
    pip install selenium webdriver-manager

Usage:
    python captcha_scraper.py [--url "YOUR_CAPTCHA_URL"]

The URL contains a time-sensitive token, so replace it with a fresh one if needed.
"""

import json
import argparse
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WDM = True
except ImportError:
    USE_WDM = False


# ── Default URL (replace with a fresh one if it has expired) ──────────────────
DEFAULT_URL = (
    "https://egypt.blsspainglobal.com/Global/CaptchaPublic/GenerateCaptcha"
    "?data=4CDiA9odF2%2b%2bsWCkAU8htqZkgDyUa5SR6waINtJfg1ThGb6rPIIpxNjefP9Uk"
    "AaSp%2fGsNNuJJi5Zt1nbVACkDRusgqfb418%2bScFkcoa1F0I%3d"
)


# ── Browser setup ─────────────────────────────────────────────────────────────
def build_driver(headless: bool = True) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")

    if USE_WDM:
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    else:
        return webdriver.Chrome(options=options)


# ── Image scraping ────────────────────────────────────────────────────────────
EXTRACT_IMAGES_JS = """
return (function() {
    try {
        const allImgs = document.querySelectorAll('.captcha-img');
        const results = [];

        if (allImgs.length === 0) {
            console.warn('No .captcha-img elements found');
            return [];
        }

        allImgs.forEach((img, idx) => {
            try {
                const rect   = img.getBoundingClientRect();
                const parent = img.parentElement;
                const pStyle = parent ? window.getComputedStyle(parent) : null;
                const shown  = pStyle && pStyle.display !== 'none' && rect.width > 0 && rect.height > 0;

                results.push({
                    index:       idx,
                    base64:      img.src || '',          // already "data:image/gif;base64,..."
                    width:       img.naturalWidth  || img.width || 0,
                    height:      img.naturalHeight || img.height || 0,
                    isDisplayed: shown,
                    posTop:      Math.round(rect.top),
                    posLeft:     Math.round(rect.left)
                });
            } catch (err) {
                console.error('Error processing image at index', idx, err);
            }
        });

        return results;
    } catch (error) {
        console.error('Error in EXTRACT_IMAGES_JS:', error);
        return [];
    }
})();
"""


def scrape_images(driver):
    # First, verify the page is ready and elements exist
    try:
        element_count = driver.execute_script("return document.querySelectorAll('.captcha-img').length;")
        print(f"  → Found {element_count} .captcha-img elements in DOM")
        
        if element_count == 0:
            # Try alternative selectors
            alt_selectors = [
                ("img.captcha-img", "img.captcha-img"),
                ("[class*='captcha']", "[class*='captcha']"),
                ("img", "all img elements"),
            ]
            
            for selector, desc in alt_selectors:
                count = driver.execute_script(f"return document.querySelectorAll('{selector}').length;")
                print(f"  → Found {count} {desc}")
            
            # Check if page has loaded
            ready_state = driver.execute_script("return document.readyState;")
            print(f"  → Document ready state: {ready_state}")
            
            raise RuntimeError("No .captcha-img elements found on the page. Page may not have loaded correctly.")
    except Exception as e:
        print(f"  ⚠  Error checking for elements: {e}")
    
    # Now try to extract images
    try:
        images = driver.execute_script(EXTRACT_IMAGES_JS)
    except Exception as js_error:
        print(f"  ⚠  JavaScript execution error: {js_error}")
        # Try a simpler version
        print("  → Trying simpler extraction...")
        images = driver.execute_script("""
           return Array.from(document.querySelectorAll('.captcha-img')).map((img, idx) => ({
                index: idx,
                base64: img.src || '',
                width: img.naturalWidth || img.width || 0,
                height: img.naturalHeight || img.height || 0,
                isDisplayed: img.offsetParent !== null,
                posTop: Math.round(img.getBoundingClientRect().top),
                posLeft: Math.round(img.getBoundingClientRect().left)
            }));
        """)
    # Check if JavaScript returned None or empty result
    if images is None:
        raise RuntimeError("Failed to extract images. JavaScript returned None. Check if page loaded correctly.")
    
    if not isinstance(images, list):
        raise RuntimeError(f"JavaScript returned unexpected type: {type(images)}, expected list")
    
    if len(images) == 0:
        print("  ⚠  Warning: No images found. Page may not have loaded correctly.")
        return [], []
    
    print(f"  → Total .captcha-img elements found : {len(images)}")

    # ── All images ────────────────────────────────────────────────────────────
    all_images = [
        {
            "index":       img["index"],
            "base64":      img["base64"],
            "width":       img["width"],
            "height":      img["height"],
            "isDisplayed": img["isDisplayed"],
            "position":    {"top": img["posTop"], "left": img["posLeft"]},
        }
        for img in images
    ]

    # ── 9 visible grid images (unique positions, parent display=block) ────────
    grid_cells: dict[str, dict] = {}
    for img in images:
        if img["isDisplayed"]:
            key = f"{img['posTop']}_{img['posLeft']}"
            if key not in grid_cells:
                grid_cells[key] = img

    sorted_cells = sorted(grid_cells.values(), key=lambda x: (x["posTop"], x["posLeft"]))
    print(f"  → Unique visible grid cells        : {len(sorted_cells)}")

    visible_images = []
    for i, img in enumerate(sorted_cells):
        row = i // 3 + 1
        col = i % 3 + 1
        visible_images.append(
            {
                "grid_position":  f"row{row}_col{col}",
                "index_in_all":   img["index"],
                "base64":         img["base64"],
                "width":          img["width"],
                "height":         img["height"],
                "position":       {"top": img["posTop"], "left": img["posLeft"]},
            }
        )

    return all_images, visible_images


# ── Text scraping ─────────────────────────────────────────────────────────────
# EXTRACT_TEXT_JS = """
# return (() => {
#     // ── Active box-label (z-index based) ─────────────────────────────────────
#     let activeLabel = null;
#     let highestZ    = -Infinity;
#     const boxLabelTexts = new Set();

#     document.querySelectorAll('.box-label').forEach(el => {
#         const z = parseInt(window.getComputedStyle(el).zIndex) || 0;
#         boxLabelTexts.add(el.textContent.trim());
#         if (z > highestZ) {
#             highestZ    = z;
#             activeLabel = el.textContent.trim();
#         }
#     });

#     // ── All text + visible text ───────────────────────────────────────────────
#     const walker      = document.createTreeWalker(
#         document.body, NodeFilter.SHOW_TEXT, null, false
#     );
#     const allText     = [];
#     const visibleText = [];
#     let node;

#     while ((node = walker.nextNode())) {
#         const text = node.textContent.trim();
#         if (!text || text.length < 2) continue;

#         const parent  = node.parentElement;
#         const style   = window.getComputedStyle(parent);
#         const rect    = parent.getBoundingClientRect();

#         // Skip box-label texts — handled by z-index logic
#         if (boxLabelTexts.has(text)) continue;

#         const visible = style.display    !== 'none'
#                      && style.visibility !== 'hidden'
#                      && style.opacity    !== '0'
#                      && rect.width        > 0
#                      && rect.height       > 0
#                      && rect.top          < window.innerHeight
#                      && rect.bottom       > 0;

#         allText.push({ text, visible });

#         // ← only non-box-label visible text goes here
#         if (visible) visibleText.push(text);
#     }

#     // ── Inject activeLabel into both lists ────────────────────────────────────
#     if (activeLabel) {
#         allText.unshift({ text: activeLabel, visible: true });   // all text ✓
#         visibleText.unshift(activeLabel);                         // visible only ✓
#     }

#     return { allText, visibleText, activeLabel };
# })();
# """

EXTRACT_TEXT_JS = """
return (() => {

    // ── Active box-label (z-index based) ─────────────────────────────────────
    let activeLabel = null;
    let highestZ    = -Infinity;
    const boxLabelTexts = new Set();

    document.querySelectorAll('.box-label').forEach(el => {
        const z = parseInt(window.getComputedStyle(el).zIndex) || 0;
        boxLabelTexts.add(el.textContent.trim());
        if (z > highestZ) {
            highestZ    = z;
            activeLabel = el.textContent.trim();
        }
    });
    const walker = document.createTreeWalker(
        document.body, NodeFilter.SHOW_TEXT, null, false
    );
    const allText    = [];
    const visibleText = [];
    let node;

    while ((node = walker.nextNode())) {
        const text   = node.textContent.trim();
        if (!text || text.length < 2) continue;

        const parent = node.parentElement;
        const style  = window.getComputedStyle(parent);
        const rect   = parent.getBoundingClientRect();
        const visible = style.display !== 'none'
                     && style.visibility !== 'hidden'
                     && rect.width > 0
                     && rect.height > 0;

        allText.push({ text, visible });
        if (visible) visibleText.push(text);
    }

    return { allText, visibleText, activeLabel};
})();
"""


def scrape_text(driver):
    result = driver.execute_script(EXTRACT_TEXT_JS)
    # print(result)

    all_texts     = [t["text"] for t in result["allText"]]
    # visible_texts = result["visibleText"]
    active_instruction   = result['activeLabel']

    # The active instruction is the one that looks like
    # "Please select all boxes with number NNN" and whose parent is visible.
    # active_instruction = next(
    #     (t for t in visible_texts if t.startswith("Please select all boxes")),
    #     None,
    # )
    print(f"  → Active CAPTCHA instruction : {active_instruction}")
    # print(f"  → Visible text items         : {len(visible_texts)}")
    print(f"  → Total text items (all)     : {len(all_texts)}")

    return {
        "active_instruction":          active_instruction,
        # "all_visible_text":            visible_texts,
        "all_text_including_hidden":   all_texts,
        "note": (
            "active_instruction is the CAPTCHA prompt currently shown to the user. "
            "all_visible_text includes all rendered text (instructions, button labels, etc.). "
            "all_text_including_hidden also includes hidden variants pre-loaded in the DOM."
        ),
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="BLS Spain CAPTCHA scraper")
    parser.add_argument("--url",       default=DEFAULT_URL, help="CAPTCHA page URL")
    parser.add_argument("--no-headless", action="store_true",
                        help="Show the browser window (useful for debugging)")
    parser.add_argument("--out-all",     default="allimages.json")
    parser.add_argument("--out-visible", default="visible_images_only.json")
    parser.add_argument("--out-text",    default="visible_text_instructions.json")
    args = parser.parse_args()

    headless = not args.no_headless
    print(f"\n{'='*60}")
    print("BLS Spain CAPTCHA Scraper")
    print(f"{'='*60}")
    print(f"URL      : {args.url[:80]}...")
    print(f"Headless : {headless}\n")

    driver = build_driver(headless=headless)
    try:
        # ── Load page ─────────────────────────────────────────────────────────
        print("[1/4] Loading page …")
        driver.get(args.url)

        # Wait until at least one .captcha-img is present
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".captcha-img"))
            )
        except Exception as e:
            print(f"      ⚠  Warning: Could not find .captcha-img elements: {e}")
            # Check what images are actually on the page
            img_count = driver.execute_script("return document.querySelectorAll('img').length;")
            captcha_count = driver.execute_script("return document.querySelectorAll('.captcha-img').length;")
            print(f"      Total img elements: {img_count}, .captcha-img elements: {captcha_count}")
        
        time.sleep(2.0)   # allow lazy images to settle and load
        print("      Page loaded ✓")

        # ── Scrape images ─────────────────────────────────────────────────────
        print("\n[2/4] Scraping images …")
        all_images, visible_images = scrape_images(driver)

        # ── Scrape text ───────────────────────────────────────────────────────
        print("\n[3/4] Scraping text instructions …")
        text_data = scrape_text(driver)

        # ── Save outputs ──────────────────────────────────────────────────────
        print("\n[4/4] Saving JSON files …")

        with open(args.out_all, "w", encoding="utf-8") as f:
            json.dump(all_images, f, indent=2)
        size_all = len(json.dumps(all_images)) / 1024
        print(f"  → {args.out_all:<35} ({len(all_images)} images, {size_all:.1f} KB)")

        with open(args.out_visible, "w", encoding="utf-8") as f:
            json.dump(visible_images, f, indent=2)
        size_vis = len(json.dumps(visible_images)) / 1024
        print(f"  → {args.out_visible:<35} ({len(visible_images)} images, {size_vis:.1f} KB)")

        with open(args.out_text, "w", encoding="utf-8") as f:
            json.dump(text_data, f, indent=2, ensure_ascii=False)
        print(f"  → {args.out_text:<35} (text instructions)")

        print("\n✅  Done! All files saved successfully.")

    finally:
        print("Window will close in 5 Seconds")
        time.sleep(5.0) 
        driver.quit()


if __name__ == "__main__":
    main()