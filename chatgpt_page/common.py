from selenium.webdriver.common.by import By


def get_prompt_input_selectors():
    return [
        '#prompt-textarea',
        'textarea[data-testid="prompt-textarea"]',
        'textarea',
        'div[contenteditable="true"][id="prompt-textarea"]',
        'div[contenteditable="true"]',
    ]


def get_composer_root(driver):
    selectors = [
        'form',
        'main form',
        '[data-testid="composer"]',
        'div:has(#prompt-textarea)',
    ]

    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)

            for element in reversed(elements):
                if element.is_displayed():
                    return element
        except Exception:
            continue

    return None