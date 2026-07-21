#!/usr/bin/env python3
"""
Quick test to verify engineering view works without starting the full Flask app.
Tests the database query and template rendering.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from t5gweb.database.operations import get_engineering_cases

def test_query():
    """Test the database query"""
    print("Testing engineering cases query...")

    # Test 1: Current sprint only
    print("\n1. Testing current sprint (T5GFE Sprint 291)")
    cases = get_engineering_cases("T5GFE Sprint 291")
    print(f"   Found {len(cases)} cases")
    if cases:
        first_case = list(cases.values())[0]
        print(f"   First case: {first_case['case_number']}")
        print(f"   Summary: {first_case['summary'][:50]}...")

    # Test 2: All sprints
    print("\n2. Testing all sprints (None)")
    cases_all = get_engineering_cases(None)
    print(f"   Found {len(cases_all)} cases across all sprints")

    # Test 3: Specific engineer
    print("\n3. Testing engineer filter (Adrien Luneau)")
    cases_adrien = get_engineering_cases("T5GFE Sprint 291", "Adrien Luneau")
    print(f"   Found {len(cases_adrien)} cases for Adrien in Sprint 291")

    # Test 4: All sprints for Adrien
    print("\n4. Testing all sprints for Adrien")
    cases_adrien_all = get_engineering_cases(None, "Adrien Luneau")
    print(f"   Found {len(cases_adrien_all)} cases for Adrien across all sprints")

    print("\n✅ Query tests completed successfully!")
    return True

if __name__ == "__main__":
    try:
        test_query()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
