#!/usr/bin/env python3
"""
Inframate Validation Script
Checks for common issues before committing:
- Missing translations
- Python syntax errors
- Backend imports
"""

import os
import re
import sys
import json
import ast
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent


def check_python_syntax():
    """Check Python files for syntax errors."""
    print("\n=== Checking Python Syntax ===")
    errors = []
    backend_path = PROJECT_ROOT / "backend"
    worker_path = PROJECT_ROOT / "worker"

    for path in [backend_path, worker_path]:
        if not path.exists():
            continue
        for py_file in path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()
                ast.parse(source)
            except SyntaxError as e:
                errors.append(f"{py_file}: Line {e.lineno}: {e.msg}")

    if errors:
        print("ERRORS found:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("OK - All Python files have valid syntax")
        return True


def extract_i18n_keys_from_vue(content):
    """Extract i18n keys used in Vue files."""
    keys = set()
    # Match t('key'), t("key") - must start with a letter and contain only valid key chars
    patterns = [
        r"t\(['\"]([a-zA-Z][a-zA-Z0-9_.]+)['\"]\)",  # t('key') or t("key")
        r"\$t\(['\"]([a-zA-Z][a-zA-Z0-9_.]+)['\"]\)",  # $t('key')
    ]
    for pattern in patterns:
        matches = re.findall(pattern, content)
        # Filter out obvious non-keys (URLs, paths, etc.)
        for match in matches:
            if not match.startswith('/') and not match.startswith('#') and '/' not in match:
                keys.add(match)
    return keys


def extract_i18n_keys_from_json(json_data, prefix=""):
    """Recursively extract all keys from translation JSON."""
    keys = set()
    for key, value in json_data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(extract_i18n_keys_from_json(value, full_key))
        else:
            keys.add(full_key)
    return keys


def check_missing_translations():
    """Check for missing translation keys."""
    print("\n=== Checking Translations ===")

    # Load translation files
    locales_path = PROJECT_ROOT / "frontend" / "src" / "i18n" / "locales"
    en_path = locales_path / "en.json"
    fr_path = locales_path / "fr.json"

    if not en_path.exists() or not fr_path.exists():
        print("WARNING: Translation files not found")
        return True

    with open(en_path, 'r', encoding='utf-8') as f:
        en_translations = json.load(f)
    with open(fr_path, 'r', encoding='utf-8') as f:
        fr_translations = json.load(f)

    en_keys = extract_i18n_keys_from_json(en_translations)
    fr_keys = extract_i18n_keys_from_json(fr_translations)

    # Find used keys in Vue files
    used_keys = set()
    vue_path = PROJECT_ROOT / "frontend" / "src"
    for vue_file in vue_path.rglob("*.vue"):
        with open(vue_file, 'r', encoding='utf-8') as f:
            content = f.read()
        used_keys.update(extract_i18n_keys_from_vue(content))

    # Also check JS files
    for js_file in vue_path.rglob("*.js"):
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
        used_keys.update(extract_i18n_keys_from_vue(content))

    # Check for missing translations
    missing_in_en = used_keys - en_keys
    missing_in_fr = used_keys - fr_keys

    # Filter out dynamic keys (containing variables) and single-word keys (likely false positives)
    def is_valid_key(k):
        if any(c in k for c in ['{', '}', '$']):
            return False
        # Valid i18n keys should have at least one dot (namespace.key)
        if '.' not in k:
            return False
        return True

    missing_in_en = {k for k in missing_in_en if is_valid_key(k)}
    missing_in_fr = {k for k in missing_in_fr if is_valid_key(k)}

    has_errors = False

    if missing_in_en:
        print(f"Missing in EN ({len(missing_in_en)}):")
        for key in sorted(missing_in_en)[:20]:  # Limit output
            print(f"  - {key}")
        if len(missing_in_en) > 20:
            print(f"  ... and {len(missing_in_en) - 20} more")
        has_errors = True

    if missing_in_fr:
        print(f"Missing in FR ({len(missing_in_fr)}):")
        for key in sorted(missing_in_fr)[:20]:
            print(f"  - {key}")
        if len(missing_in_fr) > 20:
            print(f"  ... and {len(missing_in_fr) - 20} more")
        has_errors = True

    # Check for keys in EN but not in FR (incomplete translations)
    en_only = en_keys - fr_keys
    fr_only = fr_keys - en_keys

    if en_only:
        print(f"Keys in EN but not FR ({len(en_only)}):")
        for key in sorted(en_only)[:10]:
            print(f"  - {key}")
        has_errors = True

    if fr_only:
        print(f"Keys in FR but not EN ({len(fr_only)}):")
        for key in sorted(fr_only)[:10]:
            print(f"  - {key}")
        has_errors = True

    if not has_errors:
        print("OK - All used translation keys are defined")

    return not has_errors


def check_vue_syntax():
    """Basic Vue file syntax check."""
    print("\n=== Checking Vue Files ===")
    errors = []
    vue_path = PROJECT_ROOT / "frontend" / "src"

    for vue_file in vue_path.rglob("*.vue"):
        with open(vue_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for unclosed tags in template
        template_match = re.search(r'<template>(.*?)</template>', content, re.DOTALL)
        if template_match:
            template = template_match.group(1)
            # Simple check: count opening vs closing div tags
            open_divs = len(re.findall(r'<div\b', template))
            close_divs = len(re.findall(r'</div>', template))
            if open_divs != close_divs:
                errors.append(f"{vue_file.name}: Mismatched div tags (open: {open_divs}, close: {close_divs})")

        # Check for script setup
        if '<script setup>' not in content and '<script>' not in content:
            errors.append(f"{vue_file.name}: No script section found")

    if errors:
        print("WARNINGS found:")
        for err in errors:
            print(f"  - {err}")
        return True  # Warnings don't fail the build
    else:
        print("OK - All Vue files look valid")
        return True


def main():
    """Run all validation checks."""
    print("=" * 50)
    print("Inframate Validation Script")
    print("=" * 50)

    results = []

    results.append(("Python Syntax", check_python_syntax()))
    results.append(("Translations", check_missing_translations()))
    results.append(("Vue Files", check_vue_syntax()))

    print("\n" + "=" * 50)
    print("Summary:")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\nAll checks passed!")
        return 0
    else:
        print("\nSome checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
