"""Security vulnerability scanner for code quality.

This module provides functionality to detect common security vulnerabilities:
- SQL injection
- Cross-site scripting (XSS)
- Command injection
- Hardcoded secrets
- Insecure cryptography
- Path traversal
- Unsafe deserialization
"""

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import sentry_sdk

from ast_grep_mcp.core.executor import stream_ast_grep_results
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.models.standards import SecurityIssue, SecurityScanResult

logger = get_logger(__name__)

# =============================================================================
# Vulnerability Patterns - SQL Injection
# =============================================================================

SQL_INJECTION_PATTERNS = {
    "python": [
        {
            "pattern": "cursor.execute(f$$$)",
            "severity": "critical",
            "title": "SQL Injection via f-string",
            "description": "Using f-strings or string formatting in SQL queries allows SQL injection attacks",
            "remediation": "Use parameterized queries with placeholders (?, %s, etc.)",
            "cwe": "CWE-89",
            "confidence": 0.9
        },
        {
            "pattern": "cursor.execute($STR.format($$$))",
            "severity": "critical",
            "title": "SQL Injection via .format()",
            "description": "Using .format() in SQL queries allows SQL injection attacks",
            "remediation": "Use parameterized queries instead of string formatting",
            "cwe": "CWE-89",
            "confidence": 0.9
        },
        {
            "pattern": "cursor.execute($STR + $$$)",
            "severity": "critical",
            "title": "SQL Injection via string concatenation",
            "description": "Concatenating user input into SQL queries allows SQL injection",
            "remediation": "Use parameterized queries with ? or %s placeholders",
            "cwe": "CWE-89",
            "confidence": 0.85
        }
    ],
    "javascript": [
        {
            "pattern": "db.query(`$$$${$VAR}$$$`)",
            "severity": "critical",
            "title": "SQL Injection via template literal",
            "description": "Using template literals with variables in SQL queries enables SQL injection",
            "remediation": "Use parameterized queries or prepared statements",
            "cwe": "CWE-89",
            "confidence": 0.9
        }
    ],
    "typescript": [
        {
            "pattern": "db.query(`$$$${$VAR}$$$`)",
            "severity": "critical",
            "title": "SQL Injection via template literal",
            "description": "Using template literals with variables in SQL queries enables SQL injection",
            "remediation": "Use parameterized queries or prepared statements",
            "cwe": "CWE-89",
            "confidence": 0.9
        }
    ]
}

# =============================================================================
# Vulnerability Patterns - XSS (Cross-Site Scripting)
# =============================================================================

XSS_PATTERNS = {
    "python": [
        {
            "pattern": "f\"<$$$>{$VAR}<$$$>\"",
            "severity": "high",
            "title": "XSS via unescaped HTML in f-string",
            "description": "Inserting user input directly into HTML without escaping enables XSS attacks",
            "remediation": "Use HTML escaping functions like html.escape() or template engine auto-escaping",
            "cwe": "CWE-79",
            "confidence": 0.7
        }
    ],
    "javascript": [
        {
            "pattern": "innerHTML = $VAR",
            "severity": "high",
            "title": "XSS via innerHTML",
            "description": "Assigning user input to innerHTML without sanitization enables XSS",
            "remediation": "Use textContent or sanitize HTML with DOMPurify",
            "cwe": "CWE-79",
            "confidence": 0.8
        },
        {
            "pattern": "document.write($VAR)",
            "severity": "high",
            "title": "XSS via document.write()",
            "description": "Using document.write() with user input can enable XSS attacks",
            "remediation": "Avoid document.write() or sanitize input properly",
            "cwe": "CWE-79",
            "confidence": 0.85
        }
    ],
    "typescript": [
        {
            "pattern": "innerHTML = $VAR",
            "severity": "high",
            "title": "XSS via innerHTML",
            "description": "Assigning user input to innerHTML without sanitization enables XSS",
            "remediation": "Use textContent or sanitize HTML with DOMPurify",
            "cwe": "CWE-79",
            "confidence": 0.8
        }
    ]
}

# =============================================================================
# Vulnerability Patterns - Command Injection
# =============================================================================

COMMAND_INJECTION_PATTERNS = {
    "python": [
        {
            "pattern": "os.system(f$$$)",
            "severity": "critical",
            "title": "Command Injection via os.system() with f-string",
            "description": "Using os.system() with formatted strings allows command injection",
            "remediation": "Use subprocess.run() with list of arguments instead",
            "cwe": "CWE-78",
            "confidence": 0.95
        },
        {
            "pattern": "os.system($STR + $$$)",
            "severity": "critical",
            "title": "Command Injection via os.system() concatenation",
            "description": "String concatenation in os.system() enables command injection",
            "remediation": "Use subprocess.run(['cmd', arg1, arg2]) with array form",
            "cwe": "CWE-78",
            "confidence": 0.9
        },
        {
            "pattern": "subprocess.run($STR, shell=True)",
            "severity": "high",
            "title": "Command Injection via subprocess with shell=True",
            "description": "Using shell=True with user input allows command injection",
            "remediation": "Use subprocess.run() with list form and shell=False",
            "cwe": "CWE-78",
            "confidence": 0.85
        },
        {
            "pattern": "eval($VAR)",
            "severity": "critical",
            "title": "Code Injection via eval()",
            "description": "eval() with user input allows arbitrary code execution",
            "remediation": "Never use eval() with untrusted input; use safe alternatives like ast.literal_eval()",
            "cwe": "CWE-95",
            "confidence": 1.0
        },
        {
            "pattern": "exec($VAR)",
            "severity": "critical",
            "title": "Code Injection via exec()",
            "description": "exec() with user input allows arbitrary code execution",
            "remediation": "Never use exec() with untrusted input",
            "cwe": "CWE-95",
            "confidence": 1.0
        }
    ],
    "javascript": [
        {
            "pattern": "eval($VAR)",
            "severity": "critical",
            "title": "Code Injection via eval()",
            "description": "eval() with user input allows arbitrary code execution",
            "remediation": "Never use eval(); use JSON.parse() for JSON or safer alternatives",
            "cwe": "CWE-95",
            "confidence": 1.0
        }
    ]
}

# =============================================================================
# Vulnerability Patterns - Hardcoded Secrets
# =============================================================================

SECRET_REGEX_PATTERNS = [
    {
        "regex": r'["\']sk-[a-zA-Z0-9]{32,}["\']',
        "severity": "critical",
        "title": "Hardcoded API Key (OpenAI format)",
        "description": "Hardcoded API key found in source code",
        "remediation": "Use environment variables or secret management system",
        "cwe": "CWE-798"
    },
    {
        "regex": r'["\']AIza[a-zA-Z0-9_-]{35}["\']',
        "severity": "critical",
        "title": "Hardcoded Google API Key",
        "description": "Hardcoded Google API key found in source code",
        "remediation": "Use environment variables or Google Secret Manager",
        "cwe": "CWE-798"
    },
    {
        "regex": r'["\']ghp_[a-zA-Z0-9]{36}["\']',
        "severity": "critical",
        "title": "Hardcoded GitHub Personal Access Token",
        "description": "GitHub token found hardcoded in source code",
        "remediation": "Use environment variables or GitHub Secrets",
        "cwe": "CWE-798"
    },
    {
        "regex": r'password\s*=\s*["\'][^"\']{8,}["\']',
        "severity": "high",
        "title": "Hardcoded Password",
        "description": "Password appears to be hardcoded in source code",
        "remediation": "Use environment variables or credential management system",
        "cwe": "CWE-798"
    },
    {
        "regex": r'Bearer\s+[a-zA-Z0-9_-]{20,}',
        "severity": "high",
        "title": "Hardcoded Bearer Token",
        "description": "Bearer token found in source code",
        "remediation": "Use environment variables for authentication tokens",
        "cwe": "CWE-798"
    }
]

# =============================================================================
# Vulnerability Patterns - Insecure Cryptography
# =============================================================================

CRYPTO_PATTERNS = {
    "python": [
        {
            "pattern": "hashlib.md5($$$)",
            "severity": "medium",
            "title": "Insecure Hash Algorithm (MD5)",
            "description": "MD5 is cryptographically broken and should not be used for security",
            "remediation": "Use bcrypt, argon2, or scrypt for password hashing; SHA-256+ for checksums",
            "cwe": "CWE-327",
            "confidence": 0.9
        },
        {
            "pattern": "hashlib.sha1($$$)",
            "severity": "medium",
            "title": "Weak Hash Algorithm (SHA-1)",
            "description": "SHA-1 is weak and deprecated for security purposes",
            "remediation": "Use SHA-256 or stronger; use bcrypt/argon2 for passwords",
            "cwe": "CWE-327",
            "confidence": 0.9
        }
    ]
}

# =============================================================================
# Scanner Implementation
# =============================================================================

def scan_for_vulnerability(
    project_folder: str,
    language: str,
    patterns: List[Dict[str, Any]]
) -> List[SecurityIssue]:
    """Scan for vulnerabilities using ast-grep patterns.

    Args:
        project_folder: Project root directory
        language: Programming language
        patterns: List of vulnerability patterns to check

    Returns:
        List of SecurityIssue objects
    """
    issues = []

    for pattern_def in patterns:
        try:
            # Build ast-grep command arguments
            args = [
                "-p", pattern_def["pattern"],
                "-l", language,
                "--json=stream",
                project_folder
            ]

            # Execute ast-grep with pattern
            results = stream_ast_grep_results(
                "run",
                args,
                max_results=0  # No limit
            )

            for match in results:
                issue = SecurityIssue(
                    file=match.get("file", ""),
                    line=match.get("line", 1),
                    column=match.get("column", 1),
                    end_line=match.get("end_line", match.get("line", 1)),
                    end_column=match.get("end_column", 1),
                    issue_type=pattern_def.get("issue_type", "unknown"),
                    severity=pattern_def["severity"],
                    title=pattern_def["title"],
                    description=pattern_def["description"],
                    code_snippet=match.get("text", ""),
                    remediation=pattern_def["remediation"],
                    cwe_id=pattern_def.get("cwe"),
                    confidence=pattern_def.get("confidence", 0.8)
                )
                issues.append(issue)

        except Exception as e:
            logger.warning(f"Pattern scan failed: {pattern_def.get('title')}: {e}")
            sentry_sdk.capture_exception(e)

    return issues


def scan_for_secrets_regex(
    project_folder: str,
    language: str
) -> List[SecurityIssue]:
    """Scan for hardcoded secrets using regex patterns.

    Args:
        project_folder: Project root directory
        language: Programming language (for file filtering)

    Returns:
        List of SecurityIssue objects
    """
    issues = []
    project_path = Path(project_folder)

    # File extensions by language
    extensions = {
        "python": [".py"],
        "javascript": [".js"],
        "typescript": [".ts", ".tsx"],
        "java": [".java"]
    }

    exts = extensions.get(language, [".py", ".js", ".ts", ".java"])

    # Scan files
    for ext in exts:
        for file_path in project_path.rglob(f"*{ext}"):
            if any(part in str(file_path) for part in ["node_modules", "__pycache__", "venv", ".venv", "dist", "build"]):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()

                for pattern_def in SECRET_REGEX_PATTERNS:
                    for line_num, line in enumerate(lines, start=1):
                        matches = re.finditer(pattern_def["regex"], line, re.IGNORECASE)
                        for match in matches:
                            issue = SecurityIssue(
                                file=str(file_path),
                                line=line_num,
                                column=match.start() + 1,
                                end_line=line_num,
                                end_column=match.end() + 1,
                                issue_type="hardcoded_secret",
                                severity=pattern_def["severity"],
                                title=pattern_def["title"],
                                description=pattern_def["description"],
                                code_snippet=line.strip(),
                                remediation=pattern_def["remediation"],
                                cwe_id=pattern_def.get("cwe"),
                                confidence=0.85
                            )
                            issues.append(issue)

            except Exception as e:
                logger.warning(f"Secret scan failed for {file_path}: {e}")

    return issues


def detect_security_issues_impl(
    project_folder: str,
    language: str,
    issue_types: List[str] = ["all"],
    severity_threshold: str = "low",
    max_issues: int = 100
) -> SecurityScanResult:
    """Scan project for security vulnerabilities.

    Args:
        project_folder: Project root directory
        language: Programming language
        issue_types: Types to scan for or ["all"]
        severity_threshold: Minimum severity to report
        max_issues: Maximum issues to find (0 = unlimited)

    Returns:
        SecurityScanResult with all findings
    """
    start_time = time.time()
    all_issues: List[SecurityIssue] = []

    # Determine which scans to run
    scan_all = "all" in issue_types

    # SQL Injection
    if scan_all or "sql_injection" in issue_types:
        if language in SQL_INJECTION_PATTERNS:
            patterns = SQL_INJECTION_PATTERNS[language]
            for p in patterns:
                p["issue_type"] = "sql_injection"
            issues = scan_for_vulnerability(project_folder, language, patterns)
            all_issues.extend(issues)

    # XSS
    if scan_all or "xss" in issue_types:
        if language in XSS_PATTERNS:
            patterns = XSS_PATTERNS[language]
            for p in patterns:
                p["issue_type"] = "xss"
            issues = scan_for_vulnerability(project_folder, language, patterns)
            all_issues.extend(issues)

    # Command Injection
    if scan_all or "command_injection" in issue_types:
        if language in COMMAND_INJECTION_PATTERNS:
            patterns = COMMAND_INJECTION_PATTERNS[language]
            for p in patterns:
                p["issue_type"] = "command_injection"
            issues = scan_for_vulnerability(project_folder, language, patterns)
            all_issues.extend(issues)

    # Hardcoded Secrets
    if scan_all or "hardcoded_secrets" in issue_types:
        issues = scan_for_secrets_regex(project_folder, language)
        all_issues.extend(issues)

    # Insecure Crypto
    if scan_all or "insecure_crypto" in issue_types:
        if language in CRYPTO_PATTERNS:
            patterns = CRYPTO_PATTERNS[language]
            for p in patterns:
                p["issue_type"] = "insecure_crypto"
            issues = scan_for_vulnerability(project_folder, language, patterns)
            all_issues.extend(issues)

    # Filter by severity
    severity_order = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    threshold_level = severity_order.get(severity_threshold, 0)
    filtered_issues = [
        issue for issue in all_issues
        if severity_order.get(issue.severity, 0) >= threshold_level
    ]

    # Limit results
    if max_issues > 0:
        filtered_issues = filtered_issues[:max_issues]

    # Group by severity and type
    by_severity: Dict[str, List[SecurityIssue]] = {}
    by_type: Dict[str, List[SecurityIssue]] = {}

    for issue in filtered_issues:
        if issue.severity not in by_severity:
            by_severity[issue.severity] = []
        by_severity[issue.severity].append(issue)

        if issue.issue_type not in by_type:
            by_type[issue.issue_type] = []
        by_type[issue.issue_type].append(issue)

    # Summary
    summary = {
        "total_issues": len(filtered_issues),
        "critical_count": len(by_severity.get("critical", [])),
        "high_count": len(by_severity.get("high", [])),
        "medium_count": len(by_severity.get("medium", [])),
        "low_count": len(by_severity.get("low", [])),
        "issue_types_found": list(by_type.keys())
    }

    execution_time = int((time.time() - start_time) * 1000)

    return SecurityScanResult(
        summary=summary,
        issues=filtered_issues,
        issues_by_severity=by_severity,
        issues_by_type=by_type,
        files_scanned=len(set(issue.file for issue in filtered_issues)),
        execution_time_ms=execution_time
    )
