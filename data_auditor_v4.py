"""
╔══════════════════════════════════════════════════════════════╗
║              DATA AUDITOR — COMPLETE UNIFIED ENGINE          ║
║                                                              ║
║  Phase 1 → Audit      (read-only scan, Bill of Health)       ║
║  Phase 2 → Permissions (user approves each fix)              ║
║  Phase 3 → Clean       (only approved ops run)               ║
║  Phase 4 → Report      (before/after + export)               ║
║                                                              ║
║  Every function from DataRefiner is wired in.                ║
╚══════════════════════════════════════════════════════════════╝
"""

import pandas as pd
import numpy as np
from scipy import stats
import re, json, logging, hashlib
from datetime import datetime
from rapidfuzz import process   # pip install rapidfuzz

# ──────────────────────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────────────────────
logging.basicConfig(
    filename="data_auditor.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

class AuditorError(Exception):
    pass


# ══════════════════════════════════════════════════════════════
# PHASE 1 — AUDIT ENGINE  (zero modifications, read-only)
# ══════════════════════════════════════════════════════════════

class DataAuditor:
    """
    Scans every possible data quality dimension.
    Never writes a single cell — pure inspection.
    """

    # ── categories ───────────────────────────────────────────
    # A = auto-detectable & auto-fixable
    # M = needs user-supplied parameters (flagged for review)
    # I = informational only (no auto-fix possible)

    def __init__(self, file_path: str):
        self.file_path      = file_path
        self.df             = self._load(file_path)
        self.original_shape = self.df.shape
        self.report         = {}
        print(f"✅ Loaded: {self.original_shape[0]:,} rows × {self.original_shape[1]} cols")

    # ── Improvement 1: Memory-efficient loader (peer suggestion) ─
    LARGE_FILE_MB = 50   # files above this get dtype optimization

    def _load(self, path):
        """
        Smart loader:
        - Small files  (<50 MB) → load normally.
        - Large files  (≥50 MB) → infer optimal dtypes to cut RAM,
                                   warn user, load in one shot
                                   (chunked reading available via
                                   load_in_chunks() for 500 MB+).
        """
        import os
        ext = path.rsplit(".", 1)[-1].lower()
        if ext not in ("csv","xlsx","xls","json","parquet"):
            raise AuditorError(f"Unsupported format: .{ext}")

        file_mb = os.path.getsize(path) / 1e6

        if ext == "parquet":
            return pd.read_parquet(path)

        if ext in ("xlsx","xls"):
            return pd.read_excel(path)

        if ext == "json":
            return pd.read_json(path)

        # ── CSV path with optional dtype optimisation ──────────
        if file_mb >= self.LARGE_FILE_MB:
            print(f"⚠️  Large file detected ({file_mb:.1f} MB). "
                  f"Applying dtype optimisation…")
            # Pass 1: sniff dtypes on a small sample
            sample = pd.read_csv(path, nrows=5000)
            opt_dtypes = {}
            for col in sample.select_dtypes(include=[np.number]).columns:
                # FIX: always use float32 for numeric columns — never Int32.
                # The sample covers only 5,000 rows; columns that look like
                # integers in the sample may have fractional values further in
                # the file. Casting to Int32 would silently truncate those.
                opt_dtypes[col] = "float32"
            for col in sample.select_dtypes(include="object").columns:
                if sample[col].nunique() / len(sample) < 0.5:
                    opt_dtypes[col] = "category"       # low-cardinality strings
            # Pass 2: full load with inferred dtypes
            df = pd.read_csv(path, dtype=opt_dtypes, low_memory=False)
            saved = file_mb - df.memory_usage(deep=True).sum() / 1e6
            print(f"   RAM saved ≈ {saved:.1f} MB via dtype optimisation.")
            return df

        return pd.read_csv(path)

    # ── helpers ───────────────────────────────────────────────

    def _sev(self, count, high_threshold, mid_threshold=1):
        if count >= high_threshold: return "HIGH"
        if count >= mid_threshold:  return "MEDIUM"
        return "OK"

    # ── individual checks ─────────────────────────────────────

    def _check_duplicates(self):
        n = len(self.df)
        count = int(self.df.duplicated().sum())
        return {
            "label":       "Duplicate Rows",
            "category":    "A",
            "found":       count > 0,
            "count":       count,
            "pct":         round(count / n * 100, 2) if n > 0 else 0.0,
            "severity":    self._sev(count, n * 0.1, 1),
            "fix_key":     "remove_duplicates",
            "suggestion":  f"Remove {count} exact duplicate rows.",
        }

    def _check_empty_rows(self):
        # A row is "empty" if ALL its values are either null or whitespace-only.
        # Using | avoids double-counting rows that satisfy both masks.
        null_mask  = self.df.isnull()
        ws_mask    = self.df.apply(
            lambda col: col.astype(str).str.strip() == ""
        )
        combined   = (null_mask | ws_mask).all(axis=1)
        total      = int(combined.sum())
        return {
            "label":      "Empty / Whitespace-Only Rows",
            "category":   "A",
            "found":      total > 0,
            "count":      total,
            "severity":   self._sev(total, 10, 1),
            "fix_key":    "drop_empty_rows",
            "suggestion": f"Drop {total} rows that contain no useful data.",
        }

    def _check_nulls(self):
        null_counts = self.df.isnull().sum()
        total       = int(null_counts.sum())
        by_col      = {c: {"count": int(null_counts[c]),
                           "pct":   round(float(null_counts[c] / len(self.df) * 100), 2)}
                       for c in self.df.columns if null_counts[c] > 0}
        return {
            "label":      "Missing Values (Nulls)",
            "category":   "A",
            "found":      total > 0,
            "total":      total,
            "by_column":  by_col,
            "severity":   self._sev(total / max(self.df.size, 1), 0.15, 0.05),
            "fix_key":    "smart_impute",
            "suggestion": "Auto-impute: mean (low skew) / median (high skew) / mode (categorical).",
            "alt_fix":    "handle_nulls  — choose strategy manually: mean/median/mode/ffill/bfill/interpolate/constant",
        }

    def _check_outliers(self):
        info, total = {}, 0
        for col in self.df.select_dtypes(include=[np.number]).columns:
            s = self.df[col].dropna().astype(float)   # FIX: cast for nullable dtypes
            if len(s) < 4: continue
            z = np.abs(stats.zscore(s))
            n = int((z > 3).sum())
            if n:
                q1, q3 = s.quantile(.25), s.quantile(.75)
                iqr = q3 - q1
                info[col] = {"zscore_outliers": n,
                             "iqr_lower": round(float(q1 - 1.5*iqr), 4),
                             "iqr_upper": round(float(q3 + 1.5*iqr), 4),
                             "mean": round(float(s.mean()), 4),
                             "std":  round(float(s.std()),  4)}
                total += n
        return {
            "label":      "Statistical Outliers",
            "category":   "A",
            "found":      total > 0,
            "total":      total,
            "by_column":  info,
            "severity":   self._sev(total, 50, 1),
            "fix_key":    "handle_outliers",
            "suggestion": "Cap outliers via IQR or Z-score, or drop rows.",
        }

    def _check_column_names(self):
        def _is_bad(c):
            c = str(c)
            if not c:
                return True
            if re.search(r'[^a-z0-9_]', c.lower()):
                return True
            if c != c.strip():
                return True
            if c[0].isalpha() and c[0].isupper():   # FIX: only check isupper if first char is alpha
                return True
            return False
        bad = [c for c in self.df.columns if _is_bad(c)]
        return {
            "label":      "Non-Standard Column Names",
            "category":   "A",
            "found":      len(bad) > 0,
            "count":      len(bad),
            "bad_names":  bad,
            "severity":   "MEDIUM" if bad else "OK",
            "fix_key":    "clean_column_names",
            "suggestion": "Rename to snake_case (e.g. 'First Name' → 'first_name').",
        }

    def _check_string_quality(self):
        issues = {}
        for col in self.df.select_dtypes(include="object").columns:
            s = self.df[col].dropna().astype(str)
            if s.empty:
                continue
            col_issues = []
            if (s != s.str.strip()).any():
                col_issues.append("leading/trailing whitespace")
            if s.str.contains(r'\s{2,}', regex=True).any():
                col_issues.append("extra internal whitespace")
            if s.str.contains(r"['\";\\]", regex=True).any():
                col_issues.append("SQL-breaking chars")
            if s.str.contains(r'<[^>]+>', regex=True).any():
                col_issues.append("HTML tags")
            # FIX: only check casing on strings that have alphabetic characters —
            # pure numbers/symbols always fail islower/isupper/istitle, causing
            # false positives on ID or code columns
            alpha_s = s[s.str.contains(r'[a-zA-Z]', regex=True)]
            if len(alpha_s) >= 10:   # need enough samples to judge
                if (alpha_s.str.islower().mean() < 0.8 and
                        alpha_s.str.isupper().mean() < 0.8 and
                        alpha_s.str.istitle().mean() < 0.8):
                    col_issues.append("inconsistent casing")
            if col_issues:
                issues[col] = col_issues
        return {
            "label":      "String Quality Issues",
            "category":   "A",
            "found":      bool(issues),
            "count":      len(issues),
            "by_column":  issues,
            "severity":   "MEDIUM" if issues else "OK",
            "fix_key":    "standardize_strings",
            "suggestion": "Strip whitespace, normalize case, remove HTML & SQL chars.",
            "extra_fixes": ["strip_html_tags", "remove_extra_whitespace",
                            "remove_special_characters", "normalize_text_case",
                            "cap_string_length"],
        }

    def _check_date_formats(self):
        date_cols = [c for c in self.df.columns
                     if "date" in c.lower() or "time" in c.lower()]
        bad = {}
        for col in date_cols:
            original_nulls = int(self.df[col].isna().sum())
            parsed         = pd.to_datetime(self.df[col], errors='coerce')
            # FIX: bad_n = new nulls introduced by coerce (can't go negative)
            bad_n    = max(0, int(parsed.isna().sum()) - original_nulls)
            # FIX: only count future dates on rows that parsed successfully
            future_n = int((parsed.dropna() > pd.Timestamp.now()).sum())
            if bad_n or future_n:
                bad[col] = {"unparseable": bad_n, "future_dates": future_n}
        return {
            "label":      "Date Format Issues",
            "category":   "A",
            "found":      bool(bad),
            "by_column":  bad,
            "total_bad":  sum(v["unparseable"] for v in bad.values()),
            "severity":   "MEDIUM" if bad else "OK",
            "fix_key":    "fix_date_formats",
            "suggestion": "Parse to unified datetime; flag future dates.",
            "extra_fixes": ["validate_no_future_dates", "add_datetime_features"],
        }

    def _check_data_types(self):
        BOOL_SETS = [{'true','false'}, {'yes','no'}, {'y','n'}, {'1','0'}]
        issues = {}
        for col in self.df.columns:
            s = self.df[col].dropna().astype(str).head(200)
            if s.empty:
                continue
            found = []
            num = pd.to_numeric(s.str.replace(r'[$,%€£,]','',regex=True), errors='coerce')
            if num.notna().mean() > 0.85 and self.df[col].dtype == object:
                found.append("numeric stored as string")
            uq = set(s.str.lower().unique())
            # FIX: exact match against a known bool pair — issubset wrongly passes
            # mixed sets like {'1','2','0'} since they're subset of the big union
            if uq and any(uq == b for b in BOOL_SETS):
                found.append("boolean stored as string/int")
            if found:
                issues[col] = found
        return {
            "label":      "Wrong Data Types",
            "category":   "A",
            "found":      bool(issues),
            "count":      len(issues),
            "by_column":  issues,
            "severity":   "MEDIUM" if issues else "OK",
            "fix_key":    "fix_numeric_strings",
            "suggestion": "Cast numeric strings → float; booleans → bool.",
            "extra_fixes": ["convert_booleans", "enforce_dtypes"],
        }

    def _check_sparse_columns(self, threshold=0.5):
        ratio = self.df.isnull().mean()
        sparse = {c: round(float(ratio[c])*100,1)
                  for c in self.df.columns if ratio[c] > threshold}
        return {
            "label":      f"Sparse Columns (>{int(threshold*100)}% empty)",
            "category":   "A",
            "found":      bool(sparse),
            "count":      len(sparse),
            "by_column":  sparse,
            "severity":   "HIGH" if sparse else "OK",
            "fix_key":    "drop_sparse_columns",
            "suggestion": f"Drop {len(sparse)} mostly-empty column(s).",
        }

    def _check_constant_columns(self):
        const = {c: int(self.df[c].nunique())
                 for c in self.df.columns if self.df[c].nunique() <= 1}
        return {
            "label":      "Constant / Zero-Variance Columns",
            "category":   "A",
            "found":      bool(const),
            "count":      len(const),
            "by_column":  const,
            "severity":   "MEDIUM" if const else "OK",
            "fix_key":    "drop_constant_columns",
            "suggestion": "Drop columns that carry zero information.",
        }

    def _check_high_correlation(self, threshold=0.95):
        num = self.df.select_dtypes(include=[np.number])
        pairs = []
        if num.shape[1] >= 2:
            corr  = num.corr().abs()
            upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
            # FIX: stack() drops NaN automatically — no double-iteration needed
            for (c1, c2), v in upper.stack().items():
                if v > threshold:
                    pairs.append({"col_a": c1, "col_b": c2,
                                  "correlation": round(float(v), 4)})
        return {
            "label":      f"Highly Correlated Columns (r>{threshold})",
            "category":   "A",
            "found":      bool(pairs),
            "count":      len(pairs),
            "pairs":      pairs,
            "threshold":  threshold,           # ← stored for cleaner to consume
            "severity":   "MEDIUM" if pairs else "OK",
            "fix_key":    "drop_highly_correlated",
            "suggestion": f"Drop one column from each correlated pair (threshold={threshold}).",
            "note":       "Pass corr_threshold= to run_audit() to change sensitivity.",
        }

    def _check_mixed_types(self):
        mixed = {}
        for col in self.df.columns:
            vals      = self.df[col].dropna().astype(str)
            num_pct   = pd.to_numeric(vals, errors='coerce').notna().mean()
            if 0.1 < num_pct < 0.9:
                mixed[col] = {"numeric_pct": round(num_pct*100, 1)}
        return {
            "label":      "Mixed Data Types in Column",
            "category":   "M",
            "found":      bool(mixed),
            "count":      len(mixed),
            "by_column":  mixed,
            "severity":   "MEDIUM" if mixed else "OK",
            "fix_key":    None,
            "suggestion": "Manually inspect — use enforce_dtypes() or replace_values() after reviewing.",
            "manual_fixes": ["enforce_dtypes", "replace_values"],
        }

    def _check_email_format(self):
        pattern   = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
        email_cols = [c for c in self.df.columns if "email" in c.lower() or "mail" in c.lower()]
        bad = {}
        for col in email_cols:
            n = int((~self.df[col].dropna().astype(str).str.match(pattern)).sum())
            if n: bad[col] = n
        return {
            "label":      "Invalid Email Addresses",
            "category":   "A",
            "found":      bool(bad),
            "by_column":  bad,
            "total":      sum(bad.values()),
            "severity":   "HIGH" if bad else "OK",
            "fix_key":    "validate_emails",
            "suggestion": "Flag or drop rows with malformed email addresses.",
        }

    def _check_phone_format(self):
        pattern   = r'^\+?[\d\s\-\(\)]{7,15}$'
        phone_cols = [c for c in self.df.columns
                      if any(k in c.lower() for k in ["phone","mobile","tel","cell"])]
        bad = {}
        for col in phone_cols:
            n = int((~self.df[col].dropna().astype(str).str.match(pattern)).sum())
            if n: bad[col] = n
        return {
            "label":      "Invalid Phone Numbers",
            "category":   "A",
            "found":      bool(bad),
            "by_column":  bad,
            "total":      sum(bad.values()),
            "severity":   "MEDIUM" if bad else "OK",
            "fix_key":    "validate_phones",
            "suggestion": "Flag or drop rows with malformed phone numbers.",
        }

    def _check_test_data(self):
        # FIX: use word boundaries (\b) for ambiguous keywords like 'null' and 'test'
        # to avoid matching 'nullable', 'null island', '1234567', etc.
        keywords = [r'\btest\b', r'\bdummy\b', r'\bfake\b', r'\bsample\b',
                    r'\bxxx\b', r'\bn/a\b', r'\basdf\b', r'\bnull\b', r'\b123\b']
        pattern  = '|'.join(keywords)
        tcols    = self.df.select_dtypes(include="object").columns
        count    = 0
        if len(tcols):
            mask = self.df[tcols].apply(
                lambda c: c.astype(str).str.lower().str.contains(pattern, na=False, regex=True)
            ).any(axis=1)
            count = int(mask.sum())
        return {
            "label":      "Test / Junk Data Rows",
            "category":   "A",
            "found":      count > 0,
            "count":      count,
            "severity":   "MEDIUM" if count else "OK",
            "fix_key":    "flag_test_data",
            "suggestion": f"Flag {count} rows containing junk keywords.",
        }

    def _check_typos(self):
        """Detect columns where fuzzy matching finds near-duplicate values."""
        suspicious = {}
        for col in self.df.select_dtypes(include="object").columns:
            uq = self.df[col].dropna().unique().tolist()
            if len(uq) < 2 or len(uq) > 200:
                continue
            found = []
            seen  = set()
            for val in uq:
                if val in seen: continue
                matches = process.extract(str(val), [str(v) for v in uq], score_cutoff=85)
                if len(matches) > 1:
                    group = [m[0] for m in matches]
                    found.append(group)
                    seen.update(group)
            if found:
                suspicious[col] = found
        return {
            "label":      "Possible Typos / Near-Duplicate Values",
            "category":   "A",
            "found":      bool(suspicious),
            "by_column":  suspicious,
            "severity":   "MEDIUM" if suspicious else "OK",
            "fix_key":    "auto_fix_typos",
            "suggestion": "Replace minority spelling variants with the most-common version.",
            "alt_fix":    "fuzzy_match_column — inspect manually before fixing",
        }

    def _check_pii(self):
        """Heuristically detect columns that may contain PII."""
        pii_keywords = ['email','phone','mobile','ssn','passport','address',
                        'password','dob','birth','credit','card','ip','name']
        found = [c for c in self.df.columns
                 if any(k in c.lower() for k in pii_keywords)]
        return {
            "label":      "Potential PII Columns",
            "category":   "M",
            "found":      bool(found),
            "columns":    found,
            "count":      len(found),
            "severity":   "HIGH" if found else "OK",
            "fix_key":    None,
            "suggestion": "Decide per column: mask_pii() for partial masking, hash_column() for irreversible hashing.",
            "manual_fixes": ["mask_pii", "hash_column"],
        }

    def _check_schema_issues(self):
        return self.detect_schema_issues()

    # ── schema issue detector (used standalone too) ───────────

    def detect_schema_issues(self):
        BOOL_SETS = [{'true','false'}, {'yes','no'}, {'1','0'}, {'y','n'}]
        issues = {}
        for col in self.df.columns:
            col_issues = []
            sample = self.df[col].dropna().astype(str).head(100)
            if sample.empty:
                continue
            num = pd.to_numeric(
                sample.str.replace(r'[$,%€£]','',regex=True).str.replace(',',''),
                errors='coerce')
            if num.notna().mean() > 0.85 and self.df[col].dtype == object:
                col_issues.append("Numeric stored as string")
            try:
                parsed = pd.to_datetime(sample, errors='coerce')
                if parsed.notna().mean() > 0.85 and self.df[col].dtype == object:
                    col_issues.append("Date stored as string")
            except Exception:
                pass
            uq = set(sample.str.lower().unique())
            # FIX: use exact match — issubset gives false positives
            if uq and any(uq == b for b in BOOL_SETS):
                col_issues.append("Boolean stored as string/int")
            if col_issues:
                issues[col] = col_issues
        return issues

    # ── profile (informational) ───────────────────────────────

    def profile_column(self, column):
        if column not in self.df.columns:
            raise AuditorError(f"Column '{column}' not found.")
        col = self.df[column]
        p   = {
            "dtype":        str(col.dtype),
            "total":        len(col),
            "nulls":        int(col.isnull().sum()),
            "null_%":       round(col.isnull().mean()*100, 2),
            "unique_count": int(col.nunique()),
            "top_5":        col.value_counts().head(5).to_dict(),
        }
        if pd.api.types.is_numeric_dtype(col):
            p.update({"min": col.min(), "max": col.max(),
                      "mean": round(col.mean(),4), "std": round(col.std(),4),
                      "skewness": round(col.skew(),4)})
        return p

    # ── health score ──────────────────────────────────────────

    def _health_score(self, checks):
        weights = {
            "duplicates":       {"HIGH":20, "MEDIUM":10},
            "empty_rows":       {"HIGH":10, "MEDIUM": 5},
            "nulls":            {"HIGH":25, "MEDIUM":12},
            "outliers":         {"HIGH":15, "MEDIUM": 7},
            "column_names":     {"MEDIUM": 5},
            "string_quality":   {"MEDIUM": 7},
            "date_formats":     {"MEDIUM": 8},
            "data_types":       {"MEDIUM": 8},
            "sparse_columns":   {"HIGH":15, "MEDIUM": 8},
            "constant_columns": {"MEDIUM": 5},
            "high_correlation": {"MEDIUM": 5},
            "mixed_types":      {"MEDIUM": 7},
            "email_format":     {"HIGH":10, "MEDIUM": 5},
            "phone_format":     {"MEDIUM": 5},
            "test_data":        {"MEDIUM": 5},
            "typos":            {"MEDIUM": 5},
            "pii":              {"HIGH":10},
        }
        score = 100
        for key, check in checks.items():
            sev = check.get("severity","OK")
            score -= weights.get(key, {}).get(sev, 0)
        return max(0, score)

    # ── master audit ──────────────────────────────────────────

    def run_audit(self, corr_threshold: float = 0.95):
        """
        corr_threshold: float (default 0.95)
            Sensitivity for correlation check.
            0.95 = conservative (only near-perfect correlations flagged).
            0.80 = aggressive  (catches more redundant features for ML).
            Peer suggestion: expose this so users can tune for linear vs
            non-linear model use-cases.
        """
        print("\n🔍 Scanning (read-only)…\n")
        checks = {
            "duplicates":       self._check_duplicates(),
            "empty_rows":       self._check_empty_rows(),
            "nulls":            self._check_nulls(),
            "outliers":         self._check_outliers(),
            "column_names":     self._check_column_names(),
            "string_quality":   self._check_string_quality(),
            "date_formats":     self._check_date_formats(),
            "data_types":       self._check_data_types(),
            "sparse_columns":   self._check_sparse_columns(),
            "constant_columns": self._check_constant_columns(),
            "high_correlation": self._check_high_correlation(threshold=corr_threshold),
            "mixed_types":      self._check_mixed_types(),
            "email_format":     self._check_email_format(),
            "phone_format":     self._check_phone_format(),
            "test_data":        self._check_test_data(),
            "typos":            self._check_typos(),
            "pii":              self._check_pii(),
        }
        score = self._health_score(checks)
        self.report = {
            "file":         self.file_path,
            "scanned_at":   datetime.now().isoformat(),
            "shape":        {"rows": self.original_shape[0], "cols": self.original_shape[1]},
            "health_score": score,
            "health_grade": "A" if score>=90 else "B" if score>=75 else "C" if score>=55 else "D",
            "issues_found": sum(1 for c in checks.values() if c.get("found")),
            "checks":       checks,
        }
        self._print_report()
        return self.report

    def _print_report(self):
        r   = self.report
        sep = "─" * 68
        icon = {"HIGH":"🔴","MEDIUM":"🟡","OK":"🟢"}
        cat  = {"A":"[AUTO-FIX]","M":"[MANUAL]  ","I":"[INFO]    "}
        print(sep)
        print(f"  📋  BILL OF HEALTH  —  {r['file']}")
        print(sep)
        print(f"  Rows : {r['shape']['rows']:,}   "
              f"Cols : {r['shape']['cols']}   "
              f"Score : {r['health_score']}%  (Grade {r['health_grade']})   "
              f"Issues : {r['issues_found']}/{len(r['checks'])}")
        print(sep)
        for key, c in r["checks"].items():
            sev = c.get("severity","OK")
            print(f"  {icon[sev]}  {cat.get(c.get('category','I'))}  {c['label']}")
            if c.get("found"):
                print(f"           ↳ {c['suggestion']}")
                if c.get("alt_fix"):
                    print(f"             alt: {c['alt_fix']}")
                if c.get("manual_fixes"):
                    print(f"             manual options: {', '.join(c['manual_fixes'])}")
                if c.get("extra_fixes"):
                    print(f"             extra: {', '.join(c['extra_fixes'])}")
        print(sep + "\n")


# ══════════════════════════════════════════════════════════════
# PHASE 2 — PERMISSION BUILDER
# ══════════════════════════════════════════════════════════════

def build_permissions(report: dict, mode="interactive") -> dict:
    """
    mode:
        'interactive' — CLI Y/N for every fixable issue
        'auto_all'    — approve every auto-fixable issue
        'auto_high'   — approve only HIGH-severity auto-fixable issues
    """
    perms   = {}
    checks  = report["checks"]

    for key, check in checks.items():
        auto_fixable = check.get("category") == "A" and check.get("found") and check.get("fix_key")
        if mode == "auto_all":
            perms[key] = bool(auto_fixable)
        elif mode == "auto_high":
            perms[key] = bool(auto_fixable and check.get("severity") == "HIGH")
        else:
            perms[key] = False   # default off; interactive will override

    if mode == "interactive":
        print("\n" + "═"*68)
        print("  🛂  PERMISSION PANEL — You are the judge")
        print("═"*68 + "\n")
        for key, check in checks.items():
            if not check.get("found") or not check.get("fix_key"):
                continue
            sev  = check["severity"]
            icon = "🔴" if sev=="HIGH" else "🟡"
            print(f"{icon} [{sev}] {check['label']}")
            print(f"   → {check['suggestion']}")
            ans = input("   Apply fix? [Y/n]: ").strip().lower()
            perms[key] = ans in ("","y","yes")
            print()

    approved = sum(1 for v in perms.values() if v)
    print(f"✅ Permissions set: {approved} approved / {len(perms)} total\n")
    return perms


# ══════════════════════════════════════════════════════════════
# PHASE 3 — CLEANING ENGINE
# ══════════════════════════════════════════════════════════════

class DataCleaner:
    """
    Executes ONLY the operations approved in the permissions dict.
    Wraps every function from DataRefiner.
    """

    # Maps every audit check key → cleaner method name
    CLEANER_MAP = {
        "duplicates":       "remove_duplicates",
        "empty_rows":       "drop_empty_rows",
        "nulls":            "smart_impute",
        "outliers":         "handle_outliers",
        "column_names":     "clean_column_names",
        "string_quality":   "standardize_strings",
        "date_formats":     "fix_date_formats",
        "data_types":       "fix_numeric_strings",
        "sparse_columns":   "drop_sparse_columns",
        "constant_columns": "drop_constant_columns",
        "high_correlation": "drop_highly_correlated",
        "email_format":     "validate_emails",
        "phone_format":     "validate_phones",
        "test_data":        "flag_test_data",
        "typos":            "auto_fix_typos",
        # mixed_types / pii are MANUAL — not auto-executed
    }

    def __init__(self, file_path: str, audit_report: dict = None):
        ext     = file_path.rsplit(".",1)[-1].lower()
        loaders = {"csv":pd.read_csv,"xlsx":pd.read_excel,"xls":pd.read_excel,
                   "json":pd.read_json,"parquet":pd.read_parquet}
        self.df                        = loaders[ext](file_path)
        self.original_df               = self.df.copy()
        self.snapshots                 = {}
        self.audit_log                 = []
        self.error_log                 = []
        self.dropped_duplicate_indices = []   # populated by remove_duplicates()
        self._audit_report             = audit_report or {}   # for threshold sharing
        self.stats_before              = self._stats()

    @classmethod
    def from_dataframe(cls, df: "pd.DataFrame", audit_report: dict = None) -> "DataCleaner":
        """
        Create a DataCleaner directly from an in-memory DataFrame, skipping
        all disk I/O. Used by run_auditor() and app.py to share the DataFrame
        already loaded by DataAuditor — no second read, no dtype mismatch,
        no temp-file leak.
        """
        instance = cls.__new__(cls)
        instance.df                        = df.copy()
        instance.original_df               = df.copy()
        instance.snapshots                 = {}
        instance.audit_log                 = []
        instance.error_log                 = []
        instance.dropped_duplicate_indices = []
        instance._audit_report             = audit_report or {}
        instance.stats_before              = instance._stats()
        return instance

    def _stats(self):
        return {"rows": len(self.df), "cols": len(self.df.columns),
                "nulls": int(self.df.isnull().sum().sum()),
                "duplicates": int(self.df.duplicated().sum())}

    def _log(self, msg):
        entry = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        self.audit_log.append(entry)
        logging.info(msg)

    def _err(self, fn, e):
        msg = f"⚠️  {fn}: {e}"
        self.error_log.append(msg)
        logging.warning(msg)
        print(msg)

    def _validate(self, col):
        if col not in self.df.columns:
            raise AuditorError(f"Column '{col}' not found. Available: {list(self.df.columns)}")

    # ── snapshots ─────────────────────────────────────────────

    def take_snapshot(self, name: str):
        self.snapshots[name] = self.df.copy()
        self._log(f"Snapshot saved: '{name}'.")
        print(f"📸 Snapshot '{name}' saved.")

    def restore_snapshot(self, name: str):
        if name not in self.snapshots:
            raise AuditorError(f"Snapshot '{name}' not found. Available: {list(self.snapshots)}")
        self.df = self.snapshots[name].copy()
        self._log(f"Restored snapshot '{name}'.")

    def rollback(self):
        self.df = self.original_df.copy()
        self._log("Rolled back to original.")
        print("✅ Rollback complete.")

    # ══════════════════════════════════════════════════════════
    # ALL CLEANING FUNCTIONS  (every method from DataRefiner)
    # ══════════════════════════════════════════════════════════

    # ── row / column management ───────────────────────────────

    def remove_duplicates(self, subset=None, keep='first'):
        """
        FIX: if subset is None (default), we build a safe subset automatically:
        - Exclude datetime columns — their string representation can vary
          by format even when the actual value is identical, causing false
          non-duplicates.
        - Use only object + numeric columns for the comparison.
        """
        if subset is None:
            # ── FIX: exclude datetime cols from duplicate comparison
            safe_cols = [
                c for c in self.df.columns
                if not pd.api.types.is_datetime64_any_dtype(self.df[c])
            ]
            subset = safe_cols if safe_cols else None

        dup_mask    = self.df.duplicated(subset=subset, keep=keep)
        dropped_idx = self.df[dup_mask].index.tolist()
        count       = len(dropped_idx)
        self.df.drop_duplicates(subset=subset, keep=keep, inplace=True)
        self.dropped_duplicate_indices = dropped_idx
        self._log(
            f"remove_duplicates → removed {count} rows "
            f"(compared on {len(subset) if subset else 'all'} columns, datetime cols excluded). "
            f"Indices (first 100): {dropped_idx[:100]}"
        )
        # NOTE: full index list is stored in self.dropped_duplicate_indices
        # and written to a separate trail file by FinalReport.generate() if
        # len > 1,000. We do NOT log it here to avoid bloating the log file.

    def drop_empty_rows(self):
        before = len(self.df)
        self.df.replace(r'^\s*$', np.nan, regex=True, inplace=True)
        self.df.dropna(how='all', inplace=True)
        self._log(f"drop_empty_rows → removed {before - len(self.df)} rows.")

    def drop_sparse_columns(self, threshold=0.5):
        ratio   = self.df.isnull().mean()
        to_drop = ratio[ratio > threshold].index.tolist()
        self.df.drop(columns=to_drop, inplace=True)
        self._log(f"drop_sparse_columns → dropped {to_drop}")

    def drop_constant_columns(self):
        to_drop = [c for c in self.df.columns if self.df[c].nunique() <= 1]
        self.df.drop(columns=to_drop, inplace=True)
        self._log(f"drop_constant_columns → dropped {to_drop}")

    def drop_highly_correlated(self, threshold=None):
        # ── reads threshold from the audit report if not explicitly passed ──
        # This ensures the cleaner uses the exact same value the user set
        # when calling run_audit(corr_threshold=...).
        if threshold is None:
            threshold = (self._audit_report.get("checks", {})
                         .get("high_correlation", {})
                         .get("threshold", 0.95))
        num   = self.df.select_dtypes(include=[np.number])
        if num.shape[1] < 2: return
        corr  = num.corr().abs()
        upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
        drop  = [c for c in upper.columns if any(upper[c] > threshold)]
        self.df.drop(columns=drop, inplace=True)
        self._log(f"drop_highly_correlated (threshold={threshold}) → dropped {drop}")

    def clean_column_names(self):
        mapping = {c: re.sub(r'\W+','_',c).strip('_').lower()
                   for c in self.df.columns if re.sub(r'\W+','_',c).strip('_').lower() != c}
        self.df.rename(columns=mapping, inplace=True)
        self._log(f"clean_column_names → renamed {len(mapping)} cols: {mapping}")

    def rename_columns(self, mapping: dict):
        self.df.rename(columns=mapping, inplace=True)
        self._log(f"rename_columns → {mapping}")

    def reorder_columns(self, order: list):
        remaining = [c for c in self.df.columns if c not in order]
        self.df    = self.df[order + remaining]
        self._log("reorder_columns applied.")

    def split_column(self, column, delimiter, new_columns: list):
        self._validate(column)
        split = self.df[column].astype(str).str.split(delimiter, expand=True)
        for i, nc in enumerate(new_columns):
            if i < split.shape[1]:
                self.df[nc] = split[i]
        self._log(f"split_column '{column}' → {new_columns}")

    def merge_columns(self, columns: list, new_column: str, separator=" "):
        for c in columns: self._validate(c)
        self.df[new_column] = self.df[columns].astype(str).agg(separator.join, axis=1)
        self._log(f"merge_columns {columns} → '{new_column}'")

    def replace_values(self, column, mapping: dict):
        self._validate(column)
        self.df[column] = self.df[column].replace(mapping)
        self._log(f"replace_values '{column}': {mapping}")

    # ── null handling ─────────────────────────────────────────

    def handle_nulls(self, strategy="median", fill_value=None, columns=None):
        num_cols = columns or self.df.select_dtypes(include=[np.number]).columns.tolist()
        for col in num_cols:
            if col not in self.df.columns: continue
            try:
                if strategy == "ffill":
                    self.df[col] = self.df[col].ffill()
                elif strategy == "bfill":
                    self.df[col] = self.df[col].bfill()
                elif strategy == "interpolate":
                    self.df[col] = self.df[col].interpolate(limit_direction='both')
                else:
                    # FIX: compute fill value lazily — avoids crash on empty column
                    if strategy == "mean":
                        val = self.df[col].mean()
                    elif strategy == "median":
                        val = self.df[col].median()
                    elif strategy == "mode":
                        m = self.df[col].mode()
                        val = m[0] if not m.empty else np.nan
                    elif strategy == "constant":
                        val = fill_value if fill_value is not None else 0
                    else:
                        val = self.df[col].median()
                    self.df[col] = self.df[col].fillna(val)
            except Exception as e:
                self._err(f"handle_nulls[{col}]", e)
        # FIX: only fill object cols that weren't in the user-specified columns list
        if not columns:
            tcols = self.df.select_dtypes(include="object").columns
            self.df[tcols] = self.df[tcols].fillna("Unknown")
        self._log(f"handle_nulls strategy='{strategy}'")

    def smart_impute(self, skew_threshold: float = 1.0):
        """
        skew_threshold: float (default 1.0)
            If |skew| > threshold → use median, else mean.
            Lower = use median more often (safer for financial data).
        """
        for col in self.df.columns:
            if self.df[col].isnull().sum() == 0:
                continue
            try:
                if pd.api.types.is_numeric_dtype(self.df[col]):
                    # ── FIX: cast nullable Int32/Int64 to float first
                    # so .skew() / .mean() / .median() don't fail silently
                    s = self.df[col].astype(float)
                    skew = abs(s.skew())
                    fill = s.mean() if skew <= skew_threshold else s.median()
                    self.df[col] = self.df[col].fillna(fill)
                else:
                    # categorical / object — use mode of non-null values only
                    non_null = self.df[col].dropna()
                    if non_null.empty:
                        self.df[col] = self.df[col].fillna("Unknown")
                    else:
                        mode = non_null.mode()
                        self.df[col] = self.df[col].fillna(
                            mode[0] if not mode.empty else "Unknown"
                        )
            except Exception as e:
                self._err(f"smart_impute[{col}]", e)
        self._log(f"smart_impute applied (skew_threshold={skew_threshold}).")

    # ── type enforcement ──────────────────────────────────────

    def enforce_dtypes(self, schema: dict):
        for col, dtype in schema.items():
            if col not in self.df.columns:
                self._err("enforce_dtypes", f"Column '{col}' not found."); continue
            try:
                self.df[col] = self.df[col].astype(dtype)
            except Exception as e:
                self._err(f"enforce_dtypes[{col}]", e)
        self._log(f"enforce_dtypes: {schema}")

    def fix_numeric_strings(self, columns=None):
        cols      = columns or self.df.select_dtypes(include="object").columns.tolist()
        converted = []
        for col in cols:
            cleaned = (self.df[col].astype(str)
                       .str.replace(r'[$,%€£,]', '', regex=True).str.strip())
            # FIX: use errors='coerce' — never raises; then only convert if
            # 85%+ of non-null values parsed successfully (avoid partial columns)
            numeric = pd.to_numeric(cleaned, errors='coerce')
            if numeric.notna().mean() > 0.85:
                self.df[col] = numeric
                converted.append(col)
        self._log(f"fix_numeric_strings: {converted}")

    def fix_date_formats(self, columns=None):
        target = columns or [c for c in self.df.columns if 'date' in c.lower() or 'time' in c.lower()]
        for col in target:
            self.df[col] = pd.to_datetime(self.df[col], errors='coerce')
        self._log(f"fix_date_formats: {target}")

    def convert_booleans(self, columns=None):
        bmap = {'true':True,'false':False,'yes':True,'no':False,'1':True,'0':False,'y':True,'n':False}
        cols = columns or self.df.select_dtypes(include="object").columns.tolist()
        conv = []
        for col in cols:
            uq = set(self.df[col].dropna().astype(str).str.lower().unique())
            if uq.issubset(set(bmap)):
                self.df[col] = self.df[col].astype(str).str.lower().map(bmap)
                conv.append(col)
        self._log(f"convert_booleans: {conv}")

    # ── text cleaning ─────────────────────────────────────────

    def standardize_strings(self):
        for col in self.df.select_dtypes(include="object").columns:
            try:
                # FIX: preserve NaN — work only on non-null values, then put them back
                null_mask = self.df[col].isna()
                cleaned = (self.df[col].fillna("__NULL__").astype(str)
                           .str.strip()
                           .str.replace(r'\s+', ' ', regex=True)
                           .apply(lambda x: re.sub(r'<[^>]+>', '', x))
                           .apply(lambda x: re.sub(r"['\";\\]", "", x))
                           .str.capitalize())
                self.df[col] = cleaned.where(~null_mask, other=np.nan)
            except Exception as e:
                self._err(f"standardize_strings[{col}]", e)
        self._log("standardize_strings applied.")

    def normalize_text_case(self, columns=None, case="lower"):
        cols = columns or self.df.select_dtypes(include="object").columns.tolist()
        fn   = {"lower": str.lower, "upper": str.upper, "title": str.title}[case]
        for col in cols:
            self.df[col] = self.df[col].astype(str).apply(fn)
        self._log(f"normalize_text_case → '{case}'")

    def strip_html_tags(self, columns=None):
        cols = columns or self.df.select_dtypes(include="object").columns.tolist()
        for col in cols:
            self.df[col] = self.df[col].astype(str).apply(
                lambda x: re.sub(r'<[^>]+>','',x).strip())
        self._log(f"strip_html_tags: {cols}")

    def remove_special_characters(self, columns=None, keep_spaces=True):
        pattern = r'[^a-zA-Z0-9\s]' if keep_spaces else r'[^a-zA-Z0-9]'
        cols    = columns or self.df.select_dtypes(include="object").columns.tolist()
        for col in cols:
            self.df[col] = self.df[col].astype(str).apply(
                lambda x: re.sub(pattern,'',x).strip())
        self._log(f"remove_special_characters: {cols}")

    def cap_string_length(self, max_length=255, columns=None):
        cols = columns or self.df.select_dtypes(include="object").columns.tolist()
        for col in cols:
            self.df[col] = self.df[col].astype(str).str[:max_length]
        self._log(f"cap_string_length → {max_length}")

    def remove_extra_whitespace(self, columns=None):
        cols = columns or self.df.select_dtypes(include="object").columns.tolist()
        for col in cols:
            self.df[col] = self.df[col].astype(str).str.replace(r'\s+',' ',regex=True).str.strip()
        self._log("remove_extra_whitespace applied.")

    # ── outlier handling ──────────────────────────────────────

    def handle_outliers(self, method="iqr", threshold=3, columns=None):
        cols = columns or self.df.select_dtypes(include=[np.number]).columns.tolist()
        if method == "drop":
            # FIX: compute a combined mask across ALL numeric cols at once,
            # then drop once — avoids index mismatch from iterative drops
            keep_mask = pd.Series(True, index=self.df.index)
            for col in cols:
                try:
                    s    = self.df[col].astype(float)
                    fill = s.mean()
                    z    = np.abs(stats.zscore(s.fillna(fill)))
                    keep_mask &= (z < threshold)
                except Exception as e:
                    self._err(f"handle_outliers[{col}]", e)
            before = len(self.df)
            self.df = self.df[keep_mask]
            self._log(f"handle_outliers method='drop' → removed {before - len(self.df)} rows")
            return

        for col in cols:
            try:
                if method == "iqr":
                    q1, q3 = self.df[col].quantile(.25), self.df[col].quantile(.75)
                    iqr    = q3 - q1
                    # FIX: skip constant columns (iqr==0) — clip would do nothing but may warn
                    if iqr == 0:
                        continue
                    self.df[col] = self.df[col].clip(q1 - 1.5*iqr, q3 + 1.5*iqr)
                elif method == "zscore":
                    m, s = self.df[col].mean(), self.df[col].std()
                    if s == 0:
                        continue
                    self.df[col] = self.df[col].clip(m - threshold*s, m + threshold*s)
            except Exception as e:
                self._err(f"handle_outliers[{col}]", e)
        self._log(f"handle_outliers method='{method}'")

    # ── validation ────────────────────────────────────────────

    def validate_emails(self, action="flag"):
        pattern    = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
        email_cols = [c for c in self.df.columns if "email" in c.lower()]
        for col in email_cols:
            mask = self.df[col].astype(str).str.match(pattern)
            if action == "flag":
                self.df[f"{col}_valid"] = mask
            elif action == "drop":
                before = len(self.df)
                # FIX: reset_index after drop — avoids stale index on next column's mask
                self.df = self.df[mask].reset_index(drop=True)
                self._log(f"validate_emails '{col}' drop → removed {before - len(self.df)}")
        self._log("validate_emails applied.")

    def validate_phones(self, action="flag"):
        pattern    = r'^\+?[\d\s\-\(\)]{7,15}$'
        phone_cols = [c for c in self.df.columns
                      if any(k in c.lower() for k in ["phone","mobile","tel","cell"])]
        for col in phone_cols:
            mask = self.df[col].astype(str).str.match(pattern)
            if action == "flag":
                self.df[f"{col}_valid"] = mask
            elif action == "drop":
                before = len(self.df)
                # FIX: reset_index after drop
                self.df = self.df[mask].reset_index(drop=True)
                self._log(f"validate_phones '{col}' drop → removed {before - len(self.df)}")
        self._log("validate_phones applied.")

    def validate_ranges(self, rules: dict):
        violations = pd.DataFrame()
        for col, (lo, hi) in rules.items():
            if col in self.df.columns:
                mask       = (self.df[col] < lo) | (self.df[col] > hi)
                violations = pd.concat([violations, self.df[mask]])
        self._log(f"validate_ranges checked: {list(rules.keys())}")
        return violations.drop_duplicates()

    def validate_no_future_dates(self, column):
        self._validate(column)
        self.df[column] = pd.to_datetime(self.df[column], errors='coerce')
        self.df[f"{column}_is_future"] = self.df[column] > pd.Timestamp.now()
        self._log(f"validate_no_future_dates: '{column}'")

    def validate_foreign_keys(self, column, valid_values: list, action="flag"):
        self._validate(column)
        mask = self.df[column].isin(valid_values)
        if action == "flag":
            self.df[f"{column}_valid_fk"] = mask
        elif action == "drop":
            before = len(self.df)
            self.df = self.df[mask].reset_index(drop=True)
            self._log(f"validate_foreign_keys drop → removed {before - len(self.df)}")
        self._log(f"validate_foreign_keys: '{column}'")

    def check_referential_integrity(self, col1, col2):
        self._validate(col1); self._validate(col2)
        missing = set(self.df[col2].dropna()) - set(self.df[col1].dropna())
        self._log(f"check_referential_integrity '{col2}'→'{col1}': {len(missing)} missing")
        return missing

    # ── ml preparation ────────────────────────────────────────

    def normalize_columns(self, method="minmax", columns=None):
        cols = columns or self.df.select_dtypes(include=[np.number]).columns.tolist()
        for col in cols:
            try:
                if method == "minmax":
                    lo,hi = self.df[col].min(), self.df[col].max()
                    if hi != lo:
                        self.df[col] = (self.df[col]-lo)/(hi-lo)
                elif method == "zscore":
                    s = self.df[col].std()
                    if s:
                        self.df[col] = (self.df[col]-self.df[col].mean())/s
            except Exception as e:
                self._err(f"normalize_columns[{col}]", e)
        self._log(f"normalize_columns method='{method}'")

    def encode_categoricals(self, method="label", columns=None):
        cols = columns or self.df.select_dtypes(include="object").columns.tolist()
        if method == "label":
            for col in cols:
                # FIX: pd.Categorical().codes maps NaN → -1 which is wrong.
                # Use a mapping from unique non-null values to preserve NaN.
                cat    = pd.Categorical(self.df[col])
                mapper = {v: i for i, v in enumerate(cat.categories)}
                self.df[col] = self.df[col].map(mapper)   # NaN stays NaN
        elif method == "onehot":
            self.df = pd.get_dummies(self.df, columns=cols)
        elif method == "frequency":
            for col in cols:
                self.df[col] = self.df[col].map(self.df[col].value_counts(normalize=True))
        self._log(f"encode_categoricals method='{method}'")

    def add_datetime_features(self, column):
        self._validate(column)
        self.df[column] = pd.to_datetime(self.df[column], errors='coerce')
        # FIX: day_name() is a method — call it explicitly, not via getattr attribute access
        features = {
            "year":    self.df[column].dt.year,
            "month":   self.df[column].dt.month,
            "day":     self.df[column].dt.day,
            "weekday": self.df[column].dt.day_name(),
            "quarter": self.df[column].dt.quarter,
        }
        for name, values in features.items():
            self.df[f"{column}_{name}"] = values
        self._log(f"add_datetime_features: '{column}'")

    # ── privacy & security ────────────────────────────────────

    def mask_pii(self, columns: list, mask_char="*"):
        for col in columns:
            if col in self.df.columns:
                self.df[col] = self.df[col].astype(str).apply(
                    lambda x: x[:2]+mask_char*(len(x)-4)+x[-2:] if len(x)>4 else mask_char*len(x))
        self._log(f"mask_pii: {columns}")

    def hash_column(self, column, algorithm="sha256"):
        self._validate(column)
        fn = hashlib.sha256 if algorithm=="sha256" else hashlib.md5
        self.df[column] = self.df[column].astype(str).apply(
            lambda x: fn(x.encode()).hexdigest())
        self._log(f"hash_column '{column}' ({algorithm})")

    def flag_test_data(self):
        # Keep this list in sync with DataAuditor._check_test_data()
        keywords = [r'\btest\b', r'\bdummy\b', r'\bfake\b', r'\bsample\b',
                    r'\bxxx\b', r'\bn/a\b', r'\bnull\b', r'\basdf\b', r'\b123\b']
        pattern  = '|'.join(keywords)
        tcols    = self.df.select_dtypes(include="object").columns
        mask     = self.df[tcols].apply(
            lambda c: c.astype(str).str.lower().str.contains(pattern, na=False, regex=True)
        ).any(axis=1)
        self.df["is_test_data"] = mask
        self._log(f"flag_test_data → {mask.sum()} rows flagged.")

    # ── fuzzy / intelligence ──────────────────────────────────

    def fuzzy_match_column(self, column, threshold=90):
        self._validate(column)
        uq, suggestions = self.df[column].unique(), []
        for val in uq:
            matches = process.extract(val, uq, score_cutoff=threshold)
            if len(matches) > 1:
                suggestions.append([m[0] for m in matches])
        return suggestions

    def auto_fix_typos(self, column=None, threshold=94):
        """
        Fuzzy-matches near-duplicate values and merges minorities into the
        most-frequent spelling.

        threshold: int (default 94, was 90)
            Higher = stricter matching, fewer false positives.
            90 was too aggressive — merged distinct values like
            'Cairo' and 'Cairo 2', or 'Ahmed' and 'Ahmet'.

        Columns with > 50 unique values are skipped automatically:
            high-cardinality columns (names, IDs, free text) are almost
            never typo candidates and are expensive to process.
        """
        cols = [column] if column else self.df.select_dtypes(include="object").columns.tolist()
        for col in cols:
            try:
                vc  = self.df[col].value_counts()
                uq  = list(vc.index)

                # ── FIX: skip high-cardinality columns (IDs, names, free text)
                if len(uq) > 50:
                    continue

                fix_map = {}
                for val in uq:
                    if val in fix_map:
                        continue
                    matches = process.extract(
                        str(val), [str(v) for v in uq], score_cutoff=threshold
                    )
                    if len(matches) > 1:
                        sorted_by_freq = sorted(
                            matches, key=lambda m: vc.get(m[0], 0), reverse=True
                        )
                        best       = sorted_by_freq[0][0]
                        second     = sorted_by_freq[1][0]
                        best_freq  = vc.get(best,   0)
                        second_freq= vc.get(second, 0)

                        # ── FIX: warn when frequencies are too close
                        # (both variants likely real values, not a typo)
                        if best_freq > 0 and second_freq / best_freq >= 0.80:
                            warn_msg = (
                                f"auto_fix_typos '{col}': AMBIGUOUS — "
                                f"'{best}' (n={best_freq}) vs '{second}' (n={second_freq}). "
                                f"Skipping merge — verify manually."
                            )
                            logging.warning(warn_msg)
                            print(f"  ⚠️  {warn_msg}")
                            continue   # ← skip this group entirely

                        for m in sorted_by_freq[1:]:
                            if m[0] != best:
                                fix_map[m[0]] = best

                self.df[col] = self.df[col].replace(fix_map)
                if fix_map:
                    self._log(f"auto_fix_typos '{col}': {fix_map}")
            except Exception as e:
                self._err(f"auto_fix_typos[{col}]", e)

    # ── reporting helpers ─────────────────────────────────────

    def diff_report(self):
        after = self._stats()
        return {
            "rows_removed":       self.stats_before["rows"]       - after["rows"],
            "cols_removed":       self.stats_before["cols"]       - after["cols"],
            "nulls_fixed":        self.stats_before["nulls"]      - after["nulls"],
            "duplicates_removed": self.stats_before["duplicates"] - after["duplicates"],
            "before": self.stats_before,
            "after":  after,
        }

    def get_audit_log(self):  return self.audit_log
    def get_error_log(self):  return self.error_log

    # ── output ────────────────────────────────────────────────

    def save(self, path="cleaned_data.csv"):
        ext = path.rsplit(".",1)[-1].lower()
        {"csv":     lambda: self.df.to_csv(path, index=False),
         "xlsx":    lambda: self.df.to_excel(path, index=False),
         "json":    lambda: self.df.to_json(path, orient="records", indent=2),
         "parquet": lambda: self.df.to_parquet(path, index=False)
        }.get(ext, lambda: self.df.to_csv(path, index=False))()
        self._log(f"Saved → {path}")
        return path

    # ══════════════════════════════════════════════════════════
    # CORE: run approved operations from permission dict
    # ══════════════════════════════════════════════════════════

    def run(self, permissions: dict, skew_threshold: float = 1.0):
        """
        skew_threshold is forwarded to smart_impute() directly here —
        no more monkey-patching needed from app.py.
        """
        print("\n⚙️  Executing approved operations…\n")
        executed, skipped = [], []
        for key, method_name in self.CLEANER_MAP.items():
            if permissions.get(key, False):
                try:
                    # ── FIX: pass skew_threshold to smart_impute properly
                    if method_name == "smart_impute":
                        self.smart_impute(skew_threshold=skew_threshold)
                    else:
                        getattr(self, method_name)()
                    executed.append(key)
                    print(f"  ✅  {key:25s} → {method_name}()")
                except Exception as e:
                    self._err(f"run[{key}]", e)
            else:
                skipped.append(key)
                print(f"  ⏭️   {key:25s} — skipped")
        print(f"\n  {len(executed)} executed · {len(skipped)} skipped\n")
        return self


# ══════════════════════════════════════════════════════════════
# PHASE 4 — FINAL REPORT & EXPORT
# ══════════════════════════════════════════════════════════════

class FinalReport:

    def __init__(self, auditor: DataAuditor, cleaner: DataCleaner, permissions: dict):
        self.auditor     = auditor
        self.cleaner     = cleaner
        self.permissions = permissions

    def _rescore(self):
        # BUG FIX: DataAuditor.__new__ skips __init__ so we must set all
        # instance attributes manually to avoid AttributeError in checks.
        temp               = DataAuditor.__new__(DataAuditor)
        temp.df            = self.cleaner.df.copy()
        temp.file_path     = "cleaned"
        temp.original_shape = self.cleaner.df.shape
        temp.report        = {}   # required by _print_report / _health_score

        # FIX: read back the threshold used in the original audit so the
        # rescore uses the exact same sensitivity — avoids before/after drift.
        corr_threshold = (
            self.auditor.report.get("checks", {})
            .get("high_correlation", {})
            .get("threshold", 0.95)
        )

        checks = {
            "duplicates":       temp._check_duplicates(),
            "empty_rows":       temp._check_empty_rows(),
            "nulls":            temp._check_nulls(),
            "outliers":         temp._check_outliers(),
            "column_names":     temp._check_column_names(),
            "string_quality":   temp._check_string_quality(),
            "date_formats":     temp._check_date_formats(),
            "data_types":       temp._check_data_types(),
            "sparse_columns":   temp._check_sparse_columns(),
            "constant_columns": temp._check_constant_columns(),
            "high_correlation": temp._check_high_correlation(threshold=corr_threshold),
            "email_format":     temp._check_email_format(),
            "phone_format":     temp._check_phone_format(),
            "test_data":        temp._check_test_data(),
            "typos":            temp._check_typos(),
            "pii":              temp._check_pii(),
            "mixed_types":      temp._check_mixed_types(),
        }
        return temp._health_score(checks)

    def generate(self, output_path="cleaned_output.csv") -> dict:
        before_score = self.auditor.report["health_score"]
        after_score  = self._rescore()
        diff         = self.cleaner.diff_report()
        all_indices  = getattr(self.cleaner, "dropped_duplicate_indices", [])

        # FIX: cap JSON to 1000 indices — write full list to a separate trail file
        indices_note = None
        if len(all_indices) > 1000:
            trail_path = output_path.rsplit(".", 1)[0] + "_dropped_indices.txt"
            with open(trail_path, "w") as f:
                f.write(f"# Full dropped duplicate index list — {len(all_indices)} rows\n")
                f.write("\n".join(str(i) for i in all_indices))
            indices_note = (
                f"{len(all_indices)} total — first 1,000 stored here; "
                f"full list in {trail_path}"
            )

        summary = {
            "output_file":    output_path,
            "generated_at":   datetime.now().isoformat(),
            "health_before":  before_score,
            "health_after":   after_score,
            "improvement":    after_score - before_score,
            "grade_before":   self.auditor.report["health_grade"],
            "grade_after":    "A" if after_score>=90 else "B" if after_score>=75 else "C" if after_score>=55 else "D",
            "diff":           diff,
            "operations_log": self.cleaner.audit_log,
            "errors":         self.cleaner.error_log,
            "permissions":    self.permissions,
            "dropped_duplicate_indices":       all_indices[:1000],
            "dropped_duplicate_indices_total": len(all_indices),
            "dropped_duplicate_indices_note":  indices_note,
            # BUG FIX: also expose diff keys at top level so callers
            # don't need to drill into ["diff"] to get common metrics.
            "rows_removed":    diff.get("rows_removed", 0),
            "cols_removed":    diff.get("cols_removed", 0),
            "nulls_fixed":     diff.get("nulls_fixed",  0),
            "duplicates_removed": diff.get("duplicates_removed", 0),
        }

        self.cleaner.save(output_path)
        report_path = output_path.rsplit(".", 1)[0] + "_audit_report.json"
        with open(report_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        self._print(summary, report_path)
        return summary

    def _print(self, s, report_path):
        sep = "═" * 68
        print(sep)
        print("  📊  FINAL REPORT")
        print(sep)
        print(f"  Health Score  : {s['health_before']}%  →  {s['health_after']}%  "
              f"(+{s['improvement']} pts)")
        print(f"  Grade         : {s['grade_before']}  →  {s['grade_after']}")
        print(f"  Rows          : {s['diff']['before']['rows']:,}  →  "
              f"{s['diff']['after']['rows']:,}  (-{s['diff']['rows_removed']})")
        print(f"  Columns       : {s['diff']['before']['cols']}  →  "
              f"{s['diff']['after']['cols']}  (-{s['diff']['cols_removed']})")
        print(f"  Nulls fixed   : {s['diff']['nulls_fixed']}")
        print(sep)
        print(f"  Operations    : {len(s['operations_log'])}")
        for op in s["operations_log"]:
            print(f"    ✅ {op}")
        if s["errors"]:
            print(f"\n  Errors ({len(s['errors'])}):")
            for e in s["errors"]: print(f"    ⚠️  {e}")
        print(sep)
        print(f"  💾 Cleaned file  : {s['output_file']}")
        print(f"  📄 Audit report  : {report_path}")
        print(sep + "\n")


# ══════════════════════════════════════════════════════════════
# MASTER RUNNER
# ══════════════════════════════════════════════════════════════

def run_auditor(
    file_path:      str,
    output_path:    str   = "cleaned_output.csv",
    mode:           str   = "interactive",
    corr_threshold: float = 0.95,
    skew_threshold: float = 1.0,
) -> dict:
    """
    One-call full pipeline: Audit → Permissions → Clean → Report
    """
    print("\n" + "█"*68)
    print("  DATA AUDITOR  —  Scan · Approve · Clean · Export")
    print("█"*68 + "\n")

    auditor     = DataAuditor(file_path)
    report      = auditor.run_audit(corr_threshold=corr_threshold)
    permissions = build_permissions(report, mode=mode)

    # FIX: create cleaner then inject auditor's df directly
    # so both work on the exact same in-memory state
    # BUG FIX: use from_dataframe() so the cleaner works on the same
    # already-loaded DataFrame — no second disk read, no dtype mismatch.
    cleaner = DataCleaner.from_dataframe(auditor.df, audit_report=report)
    cleaner.run(permissions, skew_threshold=skew_threshold)
    summary = FinalReport(auditor, cleaner, permissions).generate(output_path)
    return summary


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":

    # ── Option A: Interactive — asks Y/N for every issue ─────
    # run_auditor("your_data.csv", mode="interactive")

    # ── Option B: Fix everything automatically ───────────────
    # run_auditor("your_data.csv", mode="auto_all")

    # ── Option C: Only fix HIGH severity ────────────────────
    # run_auditor("your_data.csv", mode="auto_high")

    # ── Option D: Full manual control ───────────────────────
    #
    # auditor     = DataAuditor("your_data.csv")
    # report      = auditor.run_audit()
    # print(auditor.profile_column("age"))        # deep column inspect
    # print(auditor.detect_schema_issues())       # schema-only report
    #
    # permissions = {
    #     "duplicates":       True,
    #     "empty_rows":       True,
    #     "nulls":            True,
    #     "outliers":         False,   # ← user chose to keep outliers
    #     "column_names":     True,
    #     "string_quality":   True,
    #     "date_formats":     True,
    #     "data_types":       True,
    #     "sparse_columns":   True,
    #     "constant_columns": True,
    #     "high_correlation": False,
    #     "email_format":     True,
    #     "phone_format":     True,
    #     "test_data":        True,
    #     "typos":            True,
    #     # mixed_types / pii → handled manually below
    # }
    #
    # cleaner = DataCleaner("your_data.csv")
    # cleaner.take_snapshot("raw")
    # cleaner.run(permissions)
    #
    # # Manual operations (param-required functions)
    # cleaner.mask_pii(["email", "phone"])
    # cleaner.hash_column("password")
    # cleaner.validate_ranges({"age": (0,120), "score": (0,100)})
    # cleaner.validate_no_future_dates("signup_date")
    # cleaner.validate_foreign_keys("country", ["EG","US","UK"])
    # cleaner.split_column("full_name", " ", ["first_name", "last_name"])
    # cleaner.merge_columns(["city","country"], "location", separator=", ")
    # cleaner.replace_values("gender", {"M":"Male","F":"Female"})
    # cleaner.enforce_dtypes({"age":"int","price":"float"})
    # cleaner.normalize_columns(method="minmax")
    # cleaner.encode_categoricals(method="label")
    # cleaner.add_datetime_features("signup_date")
    # cleaner.cap_string_length(max_length=255)
    # cleaner.normalize_text_case(case="title")
    # cleaner.remove_special_characters()
    # cleaner.convert_booleans()
    # cleaner.check_referential_integrity("user_id","order_user_id")
    # cleaner.reorder_columns(["id","name","email","signup_date"])
    # cleaner.rename_columns({"signup_date":"created_at"})
    #
    # cleaner.take_snapshot("cleaned")
    # # cleaner.rollback()                    # undo everything
    # # cleaner.restore_snapshot("raw")       # back to named checkpoint
    #
    # summary = FinalReport(auditor, cleaner, permissions).generate("output.csv")
    # print(cleaner.get_audit_log())
    # print(cleaner.get_error_log())

    print("Uncomment one of the options above and point it at your file.")
