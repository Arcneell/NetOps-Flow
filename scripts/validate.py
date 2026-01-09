#!/usr/bin/env python3
"""
Inframate Validation Script
Cross-platform validation tool for checking code quality before commits.

Checks:
- Missing translations (i18n)
- Translation key synchronization (EN/FR)
- Python syntax errors
- Vue file structure
- PrimeIcons validity
- Code quality (console.log, TODO/FIXME)
- JSON syntax validation

Usage:
    python scripts/validate.py           # Run all checks
    python scripts/validate.py --quick   # Quick check (syntax only)
    python scripts/validate.py --fix     # Show suggested fixes for translations
    python scripts/validate.py --strict  # Fail on warnings too
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


# Valid PrimeIcons (comprehensive list based on PrimeVue icon library)
VALID_PRIMEICONS = {
    # Files & Folders
    'pi-folder', 'pi-folder-open', 'pi-file', 'pi-file-edit', 'pi-file-pdf', 'pi-file-excel',
    'pi-file-word', 'pi-file-import', 'pi-file-export', 'pi-file-o',
    # Books & Knowledge
    'pi-book', 'pi-question-circle', 'pi-question', 'pi-info-circle', 'pi-info', 'pi-bolt', 'pi-sun', 'pi-moon',
    # Tools & Settings
    'pi-wrench', 'pi-cog', 'pi-cogs', 'pi-sliders-h', 'pi-sliders-v',
    # Technology
    'pi-server', 'pi-database', 'pi-sitemap', 'pi-cloud', 'pi-cloud-upload', 'pi-cloud-download',
    # Security
    'pi-shield', 'pi-lock', 'pi-lock-open', 'pi-unlock', 'pi-key', 'pi-verified',
    # Users
    'pi-users', 'pi-user', 'pi-user-plus', 'pi-user-minus', 'pi-user-edit',
    # Development
    'pi-code', 'pi-desktop', 'pi-mobile', 'pi-tablet', 'pi-terminal',
    # Alerts & Status
    'pi-exclamation-triangle', 'pi-exclamation-circle', 'pi-circle', 'pi-circle-fill', 'pi-circle-on', 'pi-circle-off',
    'pi-check', 'pi-check-circle', 'pi-check-square', 'pi-times', 'pi-times-circle', 'pi-ban',
    'pi-bell', 'pi-bell-slash',
    # Ratings & Favorites
    'pi-star', 'pi-star-fill', 'pi-star-half', 'pi-star-half-fill', 'pi-heart', 'pi-heart-fill',
    'pi-tag', 'pi-tags', 'pi-bookmark', 'pi-bookmark-fill',
    # Time & Calendar
    'pi-calendar', 'pi-calendar-plus', 'pi-calendar-minus', 'pi-calendar-times', 'pi-clock', 'pi-stopwatch',
    # Communication
    'pi-envelope', 'pi-send', 'pi-phone', 'pi-comment', 'pi-comments', 'pi-inbox', 'pi-paperclip',
    # Navigation & Location
    'pi-globe', 'pi-home', 'pi-arrow-right', 'pi-arrow-left', 'pi-arrow-up', 'pi-arrow-down',
    'pi-arrow-circle-right', 'pi-arrow-circle-left', 'pi-arrow-circle-up', 'pi-arrow-circle-down',
    'pi-arrows-h', 'pi-arrows-v', 'pi-arrows-alt', 'pi-link', 'pi-external-link', 'pi-directions', 'pi-directions-alt', 'pi-compass',
    'pi-map', 'pi-map-marker',
    # Layout & Lists
    'pi-list', 'pi-list-check', 'pi-th-large', 'pi-table', 'pi-chart-bar', 'pi-chart-line', 'pi-chart-pie',
    # Search & Filter
    'pi-search', 'pi-search-plus', 'pi-search-minus', 'pi-filter', 'pi-filter-slash', 'pi-filter-fill',
    # CRUD Operations
    'pi-plus', 'pi-plus-circle', 'pi-minus', 'pi-minus-circle', 'pi-pencil', 'pi-trash',
    'pi-copy', 'pi-clone', 'pi-download', 'pi-upload', 'pi-refresh', 'pi-sync', 'pi-spinner', 'pi-spin',
    # View
    'pi-eye', 'pi-eye-slash', 'pi-power-off', 'pi-sign-in', 'pi-sign-out',
    # Media
    'pi-volume-up', 'pi-volume-down', 'pi-volume-off', 'pi-camera', 'pi-image',
    'pi-images', 'pi-video', 'pi-play', 'pi-pause', 'pi-stop', 'pi-forward', 'pi-backward',
    'pi-step-forward', 'pi-step-backward', 'pi-step-forward-alt', 'pi-step-backward-alt',
    # Connectivity
    'pi-wifi', 'pi-bluetooth', 'pi-microphone', 'pi-microphone-slash',
    # Office
    'pi-print', 'pi-save', 'pi-share-alt',
    # Commerce
    'pi-qrcode', 'pi-barcode', 'pi-money-bill', 'pi-credit-card', 'pi-shopping-cart', 'pi-shopping-bag', 'pi-wallet',
    # Objects
    'pi-box', 'pi-gift', 'pi-palette', 'pi-flag', 'pi-flag-fill',
    'pi-building', 'pi-warehouse', 'pi-car', 'pi-truck', 'pi-plane',
    # Symbols
    'pi-hashtag', 'pi-at', 'pi-percentage', 'pi-dollar', 'pi-euro', 'pi-pound', 'pi-yen',
    # Sorting
    'pi-sort', 'pi-sort-up', 'pi-sort-down', 'pi-sort-alpha-up', 'pi-sort-alpha-down',
    'pi-sort-alpha-up-alt', 'pi-sort-alpha-down-alt',
    'pi-sort-amount-up', 'pi-sort-amount-down', 'pi-sort-amount-up-alt', 'pi-sort-amount-down-alt',
    'pi-sort-numeric-up', 'pi-sort-numeric-down', 'pi-sort-numeric-up-alt', 'pi-sort-numeric-down-alt',
    # Alignment
    'pi-align-left', 'pi-align-center', 'pi-align-right', 'pi-align-justify',
    # Navigation UI
    'pi-ellipsis-h', 'pi-ellipsis-v', 'pi-bars', 'pi-angle-up', 'pi-angle-down',
    'pi-angle-left', 'pi-angle-right', 'pi-angle-double-up', 'pi-angle-double-down',
    'pi-angle-double-left', 'pi-angle-double-right', 'pi-chevron-up', 'pi-chevron-down',
    'pi-chevron-left', 'pi-chevron-right', 'pi-chevron-circle-up', 'pi-chevron-circle-down',
    'pi-chevron-circle-left', 'pi-chevron-circle-right', 'pi-caret-up', 'pi-caret-down',
    'pi-caret-left', 'pi-caret-right',
    # Window
    'pi-id-card', 'pi-ticket', 'pi-window-maximize', 'pi-window-minimize', 'pi-expand', 'pi-compress',
    # Feedback
    'pi-thumbs-up', 'pi-thumbs-down', 'pi-thumbs-up-fill', 'pi-thumbs-down-fill',
    # Actions
    'pi-history', 'pi-undo', 'pi-redo', 'pi-reply', 'pi-forward', 'pi-eject',
    # Brands
    'pi-slack', 'pi-google', 'pi-facebook', 'pi-twitter', 'pi-linkedin', 'pi-github', 'pi-discord',
    'pi-microsoft', 'pi-apple', 'pi-android', 'pi-amazon', 'pi-paypal', 'pi-whatsapp', 'pi-telegram',
    'pi-youtube', 'pi-vimeo', 'pi-instagram', 'pi-reddit', 'pi-twitch', 'pi-tiktok', 'pi-snapchat',
    # Misc
    'pi-prime', 'pi-equals', 'pi-not-equal', 'pi-at',
}


def check_primeicons() -> Tuple[bool, List[str]]:
    """Check for invalid PrimeIcons usage in Vue files."""
    print_header("Checking PrimeIcons")
    warnings = []
    checked_files = 0
    icons_found = set()

    vue_path = PROJECT_ROOT / "frontend" / "src"
    if not vue_path.exists():
        print_warning("Frontend src directory not found")
        return True, []

    # Pattern to match pi pi-xxx or just pi-xxx in icon contexts
    icon_patterns = [
        r'["\']pi\s+(pi-[a-z0-9-]+)["\']',  # 'pi pi-icon'
        r'icon=["\']pi\s+(pi-[a-z0-9-]+)["\']',  # icon="pi pi-icon"
        r':icon=["\']`?pi\s+(pi-[a-z0-9-]+)`?["\']',  # :icon="pi pi-icon"
        r'class="[^"]*\b(pi-[a-z0-9-]+)\b[^"]*"',  # class containing pi-xxx
    ]

    for vue_file in vue_path.rglob("*.vue"):
        checked_files += 1
        try:
            with open(vue_file, 'r', encoding='utf-8') as f:
                content = f.read()

            rel_path = vue_file.relative_to(PROJECT_ROOT)

            for pattern in icon_patterns:
                matches = re.findall(pattern, content)
                for icon in matches:
                    icons_found.add(icon)
                    if icon not in VALID_PRIMEICONS:
                        # Check if it might be a typo
                        similar = [v for v in VALID_PRIMEICONS if icon.replace('pi-', '') in v or v.replace('pi-', '') in icon]
                        suggestion = f" (did you mean: {similar[0]}?)" if similar else ""
                        warnings.append(f"{rel_path}: Invalid icon '{icon}'{suggestion}")

        except Exception as e:
            warnings.append(f"{vue_file.name}: Error reading file: {e}")

    if warnings:
        print_warning(f"Found {len(warnings)} potentially invalid icon(s):")
        for warn in sorted(set(warnings))[:15]:
            print(f"  - {warn}")
        if len(warnings) > 15:
            print(f"  ... and {len(warnings) - 15} more")
    else:
        print_success(f"All icons in {checked_files} Vue files are valid ({len(icons_found)} unique icons)")

    return len(warnings) == 0, warnings


def check_code_quality() -> Tuple[bool, List[str]]:
    """Check for code quality issues like console.log, TODO, FIXME."""
    print_header("Checking Code Quality")
    warnings = []
    issues_by_type = {'console': 0, 'todo': 0, 'fixme': 0, 'debugger': 0}

    vue_path = PROJECT_ROOT / "frontend" / "src"
    if not vue_path.exists():
        return True, []

    # Patterns to check
    patterns = {
        'console': r'\bconsole\.(log|warn|error|info|debug)\s*\(',
        'debugger': r'\bdebugger\b',
        'todo': r'\bTODO\b',
        'fixme': r'\bFIXME\b',
    }

    for ext in ["*.vue", "*.js", "*.ts"]:
        for file_path in vue_path.rglob(ext):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                rel_path = file_path.relative_to(PROJECT_ROOT)

                for line_num, line in enumerate(lines, 1):
                    # Skip commented lines for console/debugger
                    stripped = line.strip()
                    is_comment = stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('/*')

                    for issue_type, pattern in patterns.items():
                        if re.search(pattern, line):
                            # For console/debugger, skip if in comment
                            if issue_type in ['console', 'debugger'] and is_comment:
                                continue
                            issues_by_type[issue_type] += 1
                            if issues_by_type[issue_type] <= 3:  # Limit output
                                warnings.append(f"{rel_path}:{line_num}: {issue_type.upper()} found")

            except Exception:
                pass

    total_issues = sum(issues_by_type.values())

    if total_issues > 0:
        print_warning(f"Code quality issues found:")
        for issue_type, count in issues_by_type.items():
            if count > 0:
                print(f"  - {issue_type.upper()}: {count} occurrence(s)")
    else:
        print_success("No code quality issues found")

    # Code quality issues are warnings, not errors
    return True, warnings


def check_duplicate_translation_keys() -> Tuple[bool, List[str]]:
    """Check for duplicate keys at the same level within translation files."""
    print_header("Checking for Duplicate Translation Keys")
    errors = []

    locales_path = PROJECT_ROOT / "frontend" / "src" / "i18n" / "locales"
    if not locales_path.exists():
        return True, []

    def find_duplicates_in_object(data: dict, path: str = "") -> List[str]:
        """Find duplicate keys at the same level in nested JSON."""
        duplicates = []

        # Check for duplicates at current level
        # This is handled by JSON parsing - duplicate keys at same level would be overwritten

        # Recurse into nested objects
        for key, value in data.items():
            full_path = f"{path}.{key}" if path else key
            if isinstance(value, dict):
                duplicates.extend(find_duplicates_in_object(value, full_path))

        return duplicates

    for json_file in locales_path.glob("*.json"):
        try:
            # Use custom JSON decoder to detect duplicates at same level
            class DuplicateKeyChecker:
                def __init__(self, file_path):
                    self.file_path = file_path
                    self.duplicates = []

                def check_duplicates(self, pairs):
                    keys = [k for k, v in pairs]
                    seen = set()
                    for key in keys:
                        if key in seen:
                            self.duplicates.append(key)
                        seen.add(key)
                    return dict(pairs)

            checker = DuplicateKeyChecker(json_file)

            with open(json_file, 'r', encoding='utf-8') as f:
                json.load(f, object_pairs_hook=checker.check_duplicates)

            if checker.duplicates:
                rel_path = json_file.relative_to(PROJECT_ROOT)
                for dup in checker.duplicates[:5]:
                    errors.append(f"{rel_path}: Duplicate key '{dup}' at same level")

        except json.JSONDecodeError:
            # Already checked in check_json_syntax
            pass
        except Exception as e:
            errors.append(f"{json_file.name}: Error checking: {e}")

    if errors:
        print_error(f"Found duplicate translation keys:")
        for err in errors[:10]:
            print(f"  - {err}")
    else:
        print_success("No duplicate translation keys found")

    return len(errors) == 0, errors


def run_quick_check() -> bool:
    """Run only syntax checks (fast)."""
    results = []
    results.append(check_python_syntax()[0])
    results.append(check_json_syntax()[0])
    return all(results)


def run_full_check(show_fixes: bool = False, strict: bool = False) -> bool:
    """Run all validation checks."""
    results = []
    warnings_count = 0

    results.append(check_python_syntax()[0])
    results.append(check_json_syntax()[0])
    results.append(check_duplicate_translation_keys()[0])
    results.append(check_missing_translations(show_fixes)[0])
    results.append(check_vue_syntax()[0])

    # Icon and code quality checks (warnings)
    icon_ok, icon_warnings = check_primeicons()
    code_ok, code_warnings = check_code_quality()
    warnings_count = len(icon_warnings) + len(code_warnings)

    if strict:
        results.append(icon_ok)
        # code_quality always returns True, but in strict mode we fail if warnings
        if code_warnings:
            results.append(False)

    if warnings_count > 0:
        print(f"\n{Colors.YELLOW}Total warnings: {warnings_count}{Colors.RESET}")

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
  python scripts/validate.py --strict  Fail on warnings (invalid icons, code quality)
  python scripts/validate.py --ci      CI mode with non-zero exit on failure
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
        '--strict', '-s',
        action='store_true',
        help='Strict mode: fail on warnings (invalid icons, code quality issues)'
    )
    parser.add_argument(
        '--ci',
        action='store_true',
        help='CI mode: exit with non-zero code on any failure'
    )

    args = parser.parse_args()

    print("=" * 60)
    print(f"{Colors.BOLD}Inframate Validation Script{Colors.RESET}")
    print(f"Project: {PROJECT_ROOT}")
    mode = "Quick" if args.quick else ("Strict" if args.strict else "Standard")
    print(f"Mode: {mode}")
    print("=" * 60)

    if args.quick:
        all_passed = run_quick_check()
    else:
        all_passed = run_full_check(args.fix, args.strict)

    print("\n" + "=" * 60)
    print(f"{Colors.BOLD}Summary:{Colors.RESET}")
    print("=" * 60)

    if all_passed:
        print(f"\n{Colors.GREEN}{Colors.BOLD}All checks passed!{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}Some checks failed. Please fix the issues above.{Colors.RESET}")
        return 1 if args.ci else 0  # Don't fail in non-CI mode for warnings


if __name__ == "__main__":
    sys.exit(main())
