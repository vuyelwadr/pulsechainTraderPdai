#!/usr/bin/env python3
"""
Generate Strategies Manifest
Creates the strategies_manifest.json with new sequential numbering
"""
import json
from pathlib import Path

def load_inventory():
    """Load the comprehensive inventory"""
    with open('strategy_inventory.json', 'r') as f:
        return json.load(f)

def create_manifest():
    """Create the reorganized manifest with new sequential numbering"""
    inventory = load_inventory()
    
    # Priority rules for handling duplicates
    def get_priority(strategy):
        """Higher number = higher priority"""
        score = 0
        
        # Prioritize template-based implementations
        if strategy['template_based']:
            score += 100
        
        # Prioritize candlestick patterns
        if strategy['ta_lib_function'] and strategy['ta_lib_function'].startswith('CDL'):
            score += 50
        
        # Prioritize strategies with proper LazyBear naming
        if strategy['lazybear_name']:
            score += 10
        
        # Prioritize strategies with proper strategy names
        if strategy['strategy_name']:
            score += 5
        
        return score
    
    # Group by unique TA-Lib function to resolve duplicates
    by_talib_function = {}
    for strategy in inventory:
        func = strategy['ta_lib_function']
        if func:
            if func not in by_talib_function:
                by_talib_function[func] = []
            by_talib_function[func].append(strategy)
    
    # Select best implementation for each TA-Lib function
    unique_strategies = []
    archived_strategies = []
    
    for func, strategies in by_talib_function.items():
        if len(strategies) == 1:
            unique_strategies.append(strategies[0])
        else:
            # Sort by priority (highest first)
            sorted_strategies = sorted(strategies, key=get_priority, reverse=True)
            unique_strategies.append(sorted_strategies[0])  # Keep best
            archived_strategies.extend(sorted_strategies[1:])  # Archive rest
    
    # Add strategies without TA-Lib functions
    for strategy in inventory:
        if not strategy['ta_lib_function']:
            unique_strategies.append(strategy)
    
    # Sort unique strategies: candlestick patterns first, then others
    candlestick_strategies = [s for s in unique_strategies if s['ta_lib_function'] and s['ta_lib_function'].startswith('CDL')]
    other_strategies = [s for s in unique_strategies if not (s['ta_lib_function'] and s['ta_lib_function'].startswith('CDL'))]
    
    # Sort candlestick patterns alphabetically by TA-Lib function
    candlestick_strategies.sort(key=lambda x: x['ta_lib_function'])
    # Sort others alphabetically by filename  
    other_strategies.sort(key=lambda x: x['filename'])
    
    # Create manifest entries with new sequential numbering
    manifest_entries = []
    strategy_counter = 1
    
    # Process candlestick patterns first (001-0XX)
    for strategy in candlestick_strategies:
        new_id = f"{strategy_counter:03d}"
        
        # Generate new names
        func_name = strategy['ta_lib_function'].replace('CDL', '').lower()
        words = []
        current_word = ""
        for char in func_name:
            if char.isdigit():
                if current_word:
                    words.append(current_word)
                    current_word = ""
                words.append(char)
            else:
                current_word += char
        if current_word:
            words.append(current_word)
        
        # Join words with underscores
        file_suffix = '_'.join(words)
        class_name_suffix = ''.join(word.capitalize() for word in words)
        
        entry = {
            "strategy_id": new_id,
            "new_file_path": f"lazybear/candlestick_patterns/strategy_{new_id}_{file_suffix}.py",
            "new_class_name": f"Strategy{new_id}{class_name_suffix}",
            "new_strategy_name": f"Strategy_{new_id}_{class_name_suffix.replace('_', '')}",
            "ta_lib_function": strategy['ta_lib_function'],
            "type": "candlestick/reversal",
            "status": "active",
            "implementation_type": "template" if strategy['template_based'] else "legacy",
            
            # Original metadata
            "original_file_path": strategy['filepath'],
            "original_filename": strategy['filename'],
            "original_class_name": strategy['class_name'],
            "original_strategy_name": strategy['strategy_name'],
            "original_lazybear_number": strategy['lazybear_number'],
            "lazybear_name": strategy['lazybear_name'],
            "description": strategy['description'] or f"Implements {strategy['ta_lib_function']} candlestick pattern"
        }
        
        manifest_entries.append(entry)
        strategy_counter += 1
    
    # Process other strategies (continuing from candlestick count)
    for strategy in other_strategies:
        new_id = f"{strategy_counter:03d}"
        
        # Use filename for naming (remove strategy_XXX_ prefix)
        filename_base = strategy['filename'].replace('.py', '')
        # Remove original number prefix
        import re
        clean_name = re.sub(r'^strategy_\d+_', '', filename_base)
        
        words = clean_name.split('_')
        class_name_suffix = ''.join(word.capitalize() for word in words)
        
        entry = {
            "strategy_id": new_id,
            "new_file_path": f"lazybear/technical_indicators/strategy_{new_id}_{clean_name}.py",
            "new_class_name": f"Strategy{new_id}{class_name_suffix}",
            "new_strategy_name": f"Strategy_{new_id}_{class_name_suffix.replace('_', '')}",
            "ta_lib_function": strategy['ta_lib_function'],
            "type": "technical_indicator",
            "status": "active",
            "implementation_type": "template" if strategy['template_based'] else "legacy",
            
            # Original metadata
            "original_file_path": strategy['filepath'],
            "original_filename": strategy['filename'],
            "original_class_name": strategy['class_name'],
            "original_strategy_name": strategy['strategy_name'],
            "original_lazybear_number": strategy['lazybear_number'],
            "lazybear_name": strategy['lazybear_name'],
            "description": strategy['description'] or f"Technical indicator strategy"
        }
        
        manifest_entries.append(entry)
        strategy_counter += 1
    
    # Create archived entries
    archived_entries = []
    for strategy in archived_strategies:
        entry = {
            "original_file_path": strategy['filepath'],
            "original_filename": strategy['filename'],
            "original_class_name": strategy['class_name'],
            "original_strategy_name": strategy['strategy_name'],
            "original_lazybear_number": strategy['lazybear_number'],
            "lazybear_name": strategy['lazybear_name'],
            "ta_lib_function": strategy['ta_lib_function'],
            "type": strategy['type'],
            "status": "archived_duplicate",
            "reason": f"Duplicate of {strategy['ta_lib_function']}, lower priority implementation",
            "archive_path": f"lazybear/_archive/{strategy['filename']}"
        }
        archived_entries.append(entry)
    
    # Create final manifest
    manifest = {
        "metadata": {
            "version": "1.0",
            "generated_date": "2024-12-29",
            "description": "LazyBear trading strategies reorganization manifest",
            "total_active_strategies": len(manifest_entries),
            "total_archived_strategies": len(archived_entries),
            "candlestick_patterns_count": len(candlestick_strategies),
            "technical_indicators_count": len(other_strategies)
        },
        "active_strategies": manifest_entries,
        "archived_strategies": archived_entries
    }
    
    return manifest

def main():
    manifest = create_manifest()
    
    # Save manifest
    output_path = "/Users/ruwodda/Documents/Personal/Repos/trading/pulsechainTraderPdai/strategies_manifest.json"
    with open(output_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"📋 Strategies manifest created: {output_path}")
    
    # Print summary
    print(f"\n📊 REORGANIZATION SUMMARY:")
    print(f"   Active strategies: {manifest['metadata']['total_active_strategies']}")
    print(f"   - Candlestick patterns: {manifest['metadata']['candlestick_patterns_count']}")
    print(f"   - Technical indicators: {manifest['metadata']['technical_indicators_count']}")
    print(f"   Archived duplicates: {manifest['metadata']['total_archived_strategies']}")
    
    print(f"\n✅ NEW DIRECTORY STRUCTURE:")
    print(f"   lazybear/candlestick_patterns/    (001-{manifest['metadata']['candlestick_patterns_count']:03d})")
    print(f"   lazybear/technical_indicators/    ({manifest['metadata']['candlestick_patterns_count']+1:03d}-{manifest['metadata']['total_active_strategies']:03d})")
    print(f"   lazybear/_archive/                ({manifest['metadata']['total_archived_strategies']} duplicates)")
    
    # Show first few entries as examples
    print(f"\n🔢 SAMPLE NEW NUMBERING:")
    for i, strategy in enumerate(manifest['active_strategies'][:5]):
        print(f"   {strategy['strategy_id']}: {strategy['ta_lib_function']} → {strategy['new_class_name']}")
    
    if manifest['metadata']['total_active_strategies'] > 5:
        print(f"   ... and {manifest['metadata']['total_active_strategies'] - 5} more")

if __name__ == "__main__":
    main()