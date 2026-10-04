#!/usr/bin/env python3
"""
Create strategy manifest tracking all 205 LazyBear TradingView strategies
using the authoritative list in docs/tradingViewStrats.md.

This script parses the Markdown to extract:
- number (1..205)
- name (as written in the MD list)
- primary URL (prefers TradingView link if present, otherwise first URL)

It then marks the subset implemented in strategies/tradingview_core_strategies.py
and writes a structured manifest to task/strategy_manifest.json.
"""

import json
import os
import re
from typing import Dict, List, Tuple, Optional

def parse_tradingview_strats(md_path: str) -> List[Tuple[int, str, Optional[str]]]:
    """Parse docs/tradingViewStrats.md and return list of (number, name, url).

    Rules:
    - Prefer a TradingView URL (starts with https://www.tradingview.com/) on the same line.
    - If none on the same line, take the first URL on subsequent lines until next numbered item.
    - If still none, return None for URL.
    """
    with open(md_path, 'r') as f:
        lines = f.readlines()

    # Precompile regexes
    numbered_re = re.compile(r"^\s*(\d+)[\.:]?\s+(.*)")
    url_re = re.compile(r"https?://\S+")

    items: List[Tuple[int, str, Optional[str]]] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].rstrip('\n')
        m = numbered_re.match(line)
        if not m:
            i += 1
            continue

        # Extract number and raw text
        num = int(m.group(1))
        rest = m.group(2).strip()

        # Name is text before the first ':' if present; else full rest
        # Find any URLs on the same line
        same_line_urls = url_re.findall(rest)
        # Prefer TradingView link if present
        url: Optional[str] = None
        if same_line_urls:
            tv_urls = [u for u in same_line_urls if 'tradingview.com' in u]
            url = tv_urls[0] if tv_urls else same_line_urls[0]

        # Derive name: content before first URL if present; otherwise up to first ':'
        name = rest
        if same_line_urls:
            first_url_pos = rest.find(same_line_urls[0])
            if first_url_pos != -1:
                name = rest[:first_url_pos]
        else:
            colon_idx = rest.find(':')
            if colon_idx != -1:
                name = rest[:colon_idx]
        name = name.strip().rstrip(' ;:-')

        # If not found, look ahead until the next numbered line
        if url is None:
            j = i + 1
            while j < n:
                next_line = lines[j].rstrip('\n')
                # Stop if the next numbered item begins
                if numbered_re.match(next_line):
                    break
                urls = url_re.findall(next_line)
                if urls:
                    tv_urls = [u for u in urls if 'tradingview.com' in u]
                    url = tv_urls[0] if tv_urls else urls[0]
                    break
                j += 1

        items.append((num, name, url))
        i += 1

    # Sort by number to be safe
    items.sort(key=lambda x: x[0])
    return items


def sanitize_filename(name: str) -> str:
    """Create a safe filename segment from a strategy name."""
    # Lowercase, replace non-alphanumeric with underscore, collapse repeats
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip('_')
    return s


def create_strategy_manifest():
    """Create comprehensive manifest of all strategies from docs/tradingViewStrats.md"""
    md_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs', 'tradingViewStrats.md')
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"Cannot find tradingViewStrats.md at {md_path}")
    
    parsed = parse_tradingview_strats(md_path)
    if not parsed:
        raise RuntimeError("No strategies parsed from tradingViewStrats.md")
    
    # Mark which ones are implemented
    implemented_strategies = {
        17: "ZeroLagEMAStrategy",
        24: "FRAMAStrategy", 
        28: "KaufmannAMAStrategy",
        33: "SchaffTrendCycleStrategy",
        68: "TradersDynamicIndexStrategy",
        86: "WaveTrendStrategy",
        89: "ElderImpulseStrategy",
        108: "PremierStochasticStrategy",
        109: "SqueezeMomentumStrategy",
        111: "MACZStrategy",
        160: "CoralTrendStrategy",
        170: "InsyncIndexStrategy",
        182: "FireflyOscillatorStrategy",
        186: "CompositeMomentumIndexStrategy",
        196: "MESAAdaptiveMAStrategy",
    }
    
    total = len(parsed)
    manifest = {
        "total_strategies": total,
        "implemented": len(implemented_strategies),
        "pending": total - len(implemented_strategies),
        "strategies": {}
    }
    
    # Create entry for each strategy
    for num, name, url in parsed:
        strategy_id = f"strategy_{num:03d}"
        filename_stub = sanitize_filename(name) or f"strategy_{num:03d}"
        # Build file path: keep implemented pointing to core file; others staged in lazybear namespace
        if num in implemented_strategies:
            file_path = "strategies/tradingview_core_strategies.py"
            verification_status = "verified"
            notes = "Core implementation"
            status = "implemented"
        else:
            file_path = f"strategies/lazybear/technical_indicators/technical_indicators/{strategy_id}_{filename_stub}.py"
            verification_status = None
            notes = "Pending implementation"
            status = "pending"

        manifest["strategies"][strategy_id] = {
            "number": num,
            "name": name,
            "tradingview_url": url,
            "type": None,
            "status": status,
            "implementation_class": implemented_strategies.get(num, None),
            "file_path": file_path,
            "implementer_agent": None,
            "reviewer_agents": [],
            "verification_status": verification_status,
            "test_results": None,
            "notes": notes
        }
    
    # Save manifest
    output_path = "task/strategy_manifest.json"
    with open(output_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Created strategy manifest: {output_path}")
    print(f"Total strategies: {manifest['total_strategies']}")
    print(f"Implemented: {manifest['implemented']}")
    print(f"Pending: {manifest['pending']}")
    
    return manifest

if __name__ == "__main__":
    manifest = create_strategy_manifest()
    
    # Generate summary report
    print("\n" + "="*50)
    print("STRATEGY IMPLEMENTATION STATUS")
    print("="*50)
    print(f"✅ Implemented: {manifest['implemented']}/205 ({manifest['implemented']/205*100:.1f}%)")
    print(f"❌ Pending: {manifest['pending']}/205 ({manifest['pending']/205*100:.1f}%)")
    print("\n📋 Next Steps:")
    print("1. Deploy implementation agents for pending strategies")
    print("2. Each agent gets one strategy to implement")
    print("3. Two reviewers verify each implementation")
    print("4. Update manifest as strategies are completed")
