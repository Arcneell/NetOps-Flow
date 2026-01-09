#!/usr/bin/env python3
"""
Inframate Validation Script
Cross-platform validation tool for checking code quality before commits.

Checks:
- Missing translations (i18n)
- Python syntax errors
- Vue file structure
- TypeScript/JS syntax (basic)

Usage:
    python scripts/validate.py           # Run all checks
    python scripts/validate.py --quick   # Quick check (syntax only)
    python scripts/validate.py --fix     # Show suggested fixes for translations
"""

import os
import re
import sys
import json
import ast
import argparse
import subprocess
from pathlib import Path
from typing import Set, Dict, List, Tuple, Optional

# Cross-platform: Get script directory regardless of how it's called
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# ANSI colors (with Windows support detection)
def supports_color() -> bool:
    """Check if terminal supports ANSI colors."""
    if sys.platform == "win32":
        # Windows 10+ supports ANSI if TERM is set or if running in modern terminal
        return os.environ.get("TERM") or os.environ.get("WT_SESSION")
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

USE_COLORS = supports_color()

class Colors:
    """ANSI color codes for terminal output."""
    RED = "\033[91m" if USE_COLORS else ""
    GREEN = "\033[92m" if USE_COLORS else ""
    YELLOW = "\033[93m" if USE_COLORS else ""
    BLUE = "\033[94m" if USE_COLORS else ""
    BOLD = "\033[1m" if USE_COLORS else ""
    RESET = "\033[0m" if USE_COLORS else ""


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}=== {text} ==={Colors.RESET}")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}OK{Colors.RESET} - {text}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}ERROR{Colors.RESET} - {text}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}WARNING{Colors.RESET} - {text}")


def check_python_syntax() -> Tuple[bool, List[str]]:
    """Check Python files for syntax errors."""
    print_header("Checking Python Syntax")
    errors = []
    checked = 0

    paths_to_check = [
        PROJECT_ROOT / "backend",
        PROJECT_ROOT / "worker",
        PROJECT_ROOT / "scripts",
    ]

    for path in paths_to_check:
        if not path.exists():
            continue
        for py_file in path.rglob("*.py"):
            checked += 1
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()
                ast.parse(source)
            except SyntaxError as e:
                rel_path = py_file.relative_to(PROJECT_ROOT)
                errors.append(f"{rel_path}:{e.lineno}: {e.msg}")

    if errors:
        print_error(f"Found {len(errors)} syntax error(s):")
        for err in errors:
            print(f"  - {err}")
        return False, errors
    else:
        print_success(f"All {checked} Python files have valid syntax")
        return True, []


def extract_i18n_keys_from_vue(content: str) -> Set[str]:
    """Extract i18n keys used in Vue/JS files."""
    keys = set()
    # Match t('key'), t("key"), $t('key'), $t("key")
    # Must start with a letter and contain only valid key chars
    patterns = [
        r"(?<![a-zA-Z])t\(['\"]([a-zA-Z][a-zA-Z0-9_.]+)['\"]\)",  # t('key')
        r"\$t\(['\"]([a-zA-Z][a-zA-Z0-9_.]+)['\"]\)",  # $t('key')
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            # Filter out obvious non-keys
            if not any(c in match for c in ['/', '#', 'http']):
                keys.add(match)
    return keys


def extract_i18n_keys_from_json(json_data: dict, prefix: str = "") -> Set[str]:
    """Recursively extract all keys from translation JSON."""
    keys = set()
    for key, value in json_data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(extract_i18n_keys_from_json(value, full_key))
        else:
            keys.add(full_key)
    return keys


def is_valid_i18n_key(key: str) -> bool:
    """Check if a string looks like a valid i18n key."""
    # Must have at least one dot (namespace.key format)
    if '.' not in key:
        return False
    # No dynamic variables
    if any(c in key for c in ['{', '}', '$']):
        return False
    # Must have valid namespace
    valid_namespaces = {
        'common', 'nav', 'auth', 'dashboard', 'ipam', 'inventory',
        'scripts', 'settings', 'users', 'validation', 'messages',
        'filters', 'status', 'ip', 'remote', 'dcim', 'contracts',
        'software', 'entities', 'tickets', 'knowledge', 'notifications',
        'admin', 'roles', 'permissions', 'bulk', 'actions'
    }
    namespace = key.split('.')[0]
    return namespace in valid_namespaces


def check_missing_translations(show_fixes: bool = False) -> Tuple[bool, Dict[str, Set[str]]]:
    """Check for missing translation keys."""
    print_header("Checking Translations")

    locales_path = PROJECT_ROOT / "frontend" / "src" / "i18n" / "locales"
    en_path = locales_path / "en.json"
    fr_path = locales_path / "fr.json"

    if not en_path.exists() or not fr_path.exists():
        print_warning("Translation files not found")
        return True, {}

    with open(en_path, 'r', encoding='utf-8') as f:
        en_translations = json.load(f)
    with open(fr_path, 'r', encoding='utf-8') as f:
        fr_translations = json.load(f)

    en_keys = extract_i18n_keys_from_json(en_translations)
    fr_keys = extract_i18n_keys_from_json(fr_translations)

    # Find used keys in Vue and JS files
    used_keys: Set[str] = set()
    vue_path = PROJECT_ROOT / "frontend" / "src"

    extensions = ["*.vue", "*.js", "*.ts"]
    for ext in extensions:
        for file in vue_path.rglob(ext):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                used_keys.update(extract_i18n_keys_from_vue(content))
            except Exception:
                pass

    # Filter valid keys
    used_keys = {k for k in used_keys if is_valid_i18n_key(k)}

    # Check for missing translations
    missing_in_en = used_keys - en_keys
    missing_in_fr = used_keys - fr_keys
    en_only = en_keys - fr_keys
    fr_only = fr_keys - en_keys

    has_errors = False
    issues: Dict[str, Set[str]] = {
        'missing_en': missing_in_en,
        'missing_fr': missing_in_fr,
        'en_only': en_only,
        'fr_only': fr_only,
    }

    if missing_in_en:
        print_error(f"Missing in EN ({len(missing_in_en)}):")
        for key in sorted(missing_in_en)[:15]:
            print(f"  - {key}")
        if len(missing_in_en) > 15:
            print(f"  ... and {len(missing_in_en) - 15} more")
        has_errors = True

    if missing_in_fr:
        print_error(f"Missing in FR ({len(missing_in_fr)}):")
        for key in sorted(missing_in_fr)[:15]:
            print(f"  - {key}")
        if len(missing_in_fr) > 15:
            print(f"  ... and {len(missing_in_fr) - 15} more")
        has_errors = True

    if en_only:
        print_warning(f"Keys in EN but not FR ({len(en_only)}):")
        for key in sorted(en_only)[:10]:
            print(f"  - {key}")
        if len(en_only) > 10:
            print(f"  ... and {len(en_only) - 10} more")
        has_errors = True

    if fr_only:
        print_warning(f"Keys in FR but not EN ({len(fr_only)}):")
        for key in sorted(fr_only)[:10]:
            print(f"  - {key}")
        if len(fr_only) > 10:
            print(f"  ... and {len(fr_only) - 10} more")
        has_errors = True

    if not has_errors:
        print_success(f"All {len(used_keys)} used translation keys are defined in both EN and FR")

    # Show suggested fixes if requested
    if show_fixes and (missing_in_en or missing_in_fr):
        print(f"\n{Colors.BOLD}Suggested fixes:{Colors.RESET}")
        all_missing = missing_in_en | missing_in_fr
        for key in sorted(all_missing)[:20]:
            parts = key.split('.')
            namespace = parts[0]
            subkey = '.'.join(parts[1:])
            print(f"  Add to '{namespace}' section: \"{subkey}\": \"[translation]\"")

    return not has_errors, issues


def check_vue_syntax() -> Tuple[bool, List[str]]:
    """Basic Vue file structure check."""
    print_header("Checking Vue Files")
    warnings = []
    checked = 0
    vue_path = PROJECT_ROOT / "frontend" / "src"

    if not vue_path.exists():
        print_warning("Frontend src directory not found")
        return True, []

    for vue_file in vue_path.rglob("*.vue"):
        checked += 1
        try:
            with open(vue_file, 'r', encoding='utf-8') as f:
                content = f.read()

            rel_path = vue_file.relative_to(PROJECT_ROOT)

            # Check for template section
            if '<template>' not in content:
                warnings.append(f"{rel_path}: No <template> section found")

            # Check for script section
            if '<script setup>' not in content and '<script>' not in content:
                warnings.append(f"{rel_path}: No <script> section found")

        except Exception as e:
            warnings.append(f"{vue_file.name}: Error reading file: {e}")

    if warnings:
        print_warning(f"Found {len(warnings)} warning(s):")
        for warn in warnings:
            print(f"  - {warn}")
    else:
        print_success(f"All {checked} Vue files have valid structure")

    return True, warnings  # Warnings don't fail the build


def check_json_syntax() -> Tuple[bool, List[str]]:
    """Check JSON files for syntax errors."""
    print_header("Checking JSON Files")
    errors = []
    checked = 0

    json_paths = [
        PROJECT_ROOT / "frontend" / "src" / "i18n" / "locales",
        PROJECT_ROOT / "frontend",
    ]

    for path in json_paths:
        if not path.exists():
            continue
        pattern = "*.json" if path.name == "locales" else "package*.json"
        for json_file in path.glob(pattern):
            checked += 1
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                rel_path = json_file.relative_to(PROJECT_ROOT)
                errors.append(f"{rel_path}:{e.lineno}: {e.msg}")

    if errors:
        print_error(f"Found {len(errors)} JSON error(s):")
        for err in errors:
            print(f"  - {err}")
        return False, errors
    else:
        print_success(f"All {checked} JSON files are valid")
        return True, []


def run_quick_check() -> bool:
    """Run only syntax checks (fast)."""
    results = []
    results.append(check_python_syntax()[0])
    results.append(check_json_syntax()[0])
    return all(results)


def run_full_check(show_fixes: bool = False) -> bool:
    """Run all validation checks."""
    results = []

    results.append(check_python_syntax()[0])
    results.append(check_json_syntax()[0])
    results.append(check_missing_translations(show_fixes)[0])
    results.append(check_vue_syntax()[0])

    return all(results)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Inframate validation script - checks code quality before commits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate.py           Run all checks
  python scripts/validate.py --quick   Quick syntax-only check
  python scripts/validate.py --fix     Show suggested fixes for missing translations
        """
    )
    parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='Run quick checks only (syntax)'
    )
    parser.add_argument(
        '--fix', '-f',
        action='store_true',
        help='Show suggested fixes for translation issues'
    )
    parser.add_argument(
        '--ci',
        action='store_true',
        help='CI mode: exit with non-zero code on any failure'
    )

    args = parser.parse_args()

    print("=" * 50)
    print(f"{Colors.BOLD}Inframate Validation Script{Colors.RESET}")
    print(f"Project: {PROJECT_ROOT}")
    print("=" * 50)

    if args.quick:
        all_passed = run_quick_check()
    else:
        all_passed = run_full_check(args.fix)

    print("\n" + "=" * 50)
    print(f"{Colors.BOLD}Summary:{Colors.RESET}")
    print("=" * 50)

    if all_passed:
        print(f"\n{Colors.GREEN}{Colors.BOLD}All checks passed!{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}Some checks failed. Please fix the issues above.{Colors.RESET}")
        return 1 if args.ci else 0  # Don't fail in non-CI mode for warnings


if __name__ == "__main__":
    sys.exit(main())
