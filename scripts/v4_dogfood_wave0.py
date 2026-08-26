#!/usr/bin/env python3
# Baseline: v4/baseline-post-update-885e9ef @ 885e9ef + d7eba25
# Candidate: wt/t_261a7674 — Wave 0 dogfood harness (disposable fixtures only)
from __future__ import annotations
import json, tempfile, pathlib, sys
from hermes_chatgpt_mcp.provenance import get_candidate_provenance, get_baseline
from hermes_chatgpt_mcp.release import load_build_metadata, BuildMetadataError, canary_manifest
from hermes_chatgpt_mcp.wave0_contract import validate_api_version

def check(name, fn):
    try:
        fn()
        return {"name": name, "status": "PASS"}
    except Exception as e:
        return {"name": name, "status": "FAIL", "error": f"{type(e).__name__}: {e}"}

def main() -> int:
    results = []
    baseline = get_baseline()
    results.append(check("baseline_pins_frozen", lambda: (
        None if baseline.branch == "v4/baseline-post-update-885e9ef" else (_ for _ in ()).throw(ValueError(baseline.branch))
    )))
    results.append(check("api_version_v4_wave0", lambda: (
        None if validate_api_version("v4.wave0") == "v4.wave0" else (_ for _ in ()).throw(ValueError("version"))
    )))
    def _bad_version():
        try:
            validate_api_version("v99")
            raise AssertionError("should have failed")
        except ValueError:
            pass
    results.append(check("unsupported_version_fails_closed", _bad_version))
    def _stale_manifest():
        import tempfile, pathlib
        p = pathlib.Path(tempfile.mktemp(suffix=".json"))
        p.write_text('{"build_commit":"bad","surface":"stable","deployed_at":"x"}')
        try:
            load_build_metadata(p)
            raise AssertionError("should have failed")
        except BuildMetadataError:
            pass
        finally:
            p.unlink(missing_ok=True)
    results.append(check("stale_manifest_fails_closed", _stale_manifest))
    def _missing_manifest():
        import tempfile, pathlib
        m = load_build_metadata(pathlib.Path("/tmp/missing-wave0-xyz.json"))
        assert m.public_dict() == {"build_commit": None, "surface": None, "deployed_at": None}
    results.append(check("missing_manifest_empty", _missing_manifest))
    def _canary():
        c = canary_manifest(build_commit="a"*40, surface="beta", deployed_at="2026-08-25T00:00:00Z")
        assert c["api_version"] == "v4.wave0"
        assert c["baseline_branch"] == baseline.branch
    results.append(check("canary_primitive", _canary))
    def _provenance_header():
        prov = get_candidate_provenance(surface="beta")
        h = prov.provenance_header("beta")
        assert h.count("/") == 2
    results.append(check("provenance_header_shape", _provenance_header))

    print(json.dumps({"wave": "wave0", "baseline": baseline.as_dict(), "results": results}, indent=2))
    fails = [r for r in results if r["status"] == "FAIL"]
    return 1 if fails else 0

if __name__ == "__main__":
    raise SystemExit(main())
