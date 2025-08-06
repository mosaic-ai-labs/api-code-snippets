#!/usr/bin/env python3
"""
Test Mosaic API authentication by calling the /whoami endpoint.

This script validates that your API key is correctly configured and working.

Usage:
    python test_auth.py [--api-key API_KEY]
    
Example:
    # Using environment variable
    export MOSAIC_API_KEY=mk_your_key
    python test_auth.py
    
    # Using command line argument
    python test_auth.py --api-key mk_your_key
"""

import argparse
import os
import sys
import json
import requests
from typing import Optional, Dict, Any


class MosaicAuthTester:
    """Test Mosaic API authentication."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.mosaic.so"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def test_whoami(self) -> Dict[str, Any]:
        """
        Call the /whoami endpoint to verify authentication.
        
        Returns:
            Response data from the API
        """
        endpoint = f"{self.base_url}/whoami"
        
        try:
            response = requests.get(endpoint, headers=self.headers, timeout=10)
            
            # Check if endpoint exists
            if response.status_code == 404:
                # Try alternative endpoints that might exist
                return self.test_alternative_endpoints()
            
            response.raise_for_status()
            return {
                'success': True,
                'status_code': response.status_code,
                'data': response.json() if response.text else {}
            }
            
        except requests.exceptions.HTTPError as e:
            return {
                'success': False,
                'status_code': e.response.status_code if e.response else None,
                'error': str(e),
                'response': e.response.text if e.response else None
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_alternative_endpoints(self) -> Dict[str, Any]:
        """
        Test alternative endpoints to verify authentication.
        Try common API endpoints that might reveal auth status.
        
        Returns:
            Response data from successful endpoint
        """
        # Alternative endpoints to try
        test_endpoints = [
            ('/me', 'GET'),
            ('/user', 'GET'),
            ('/account', 'GET'),
            ('/auth/verify', 'GET'),
            ('/auth/validate', 'GET'),
            ('/api/whoami', 'GET'),
            ('/api/me', 'GET'),
            ('/videos/get_upload_url', 'GET'),  # Known endpoint from docs
        ]
        
        results = []
        
        for endpoint_path, method in test_endpoints:
            endpoint = f"{self.base_url}{endpoint_path}"
            
            try:
                if method == 'GET':
                    response = requests.get(endpoint, headers=self.headers, timeout=5)
                else:
                    response = requests.post(endpoint, headers=self.headers, json={}, timeout=5)
                
                # If we get a 200 or 401/403, it means the endpoint exists
                if response.status_code in [200, 201, 204]:
                    return {
                        'success': True,
                        'endpoint': endpoint_path,
                        'status_code': response.status_code,
                        'data': response.json() if response.text else {},
                        'note': f'Successfully authenticated via {endpoint_path}'
                    }
                elif response.status_code in [401, 403]:
                    results.append({
                        'endpoint': endpoint_path,
                        'status_code': response.status_code,
                        'exists': True,
                        'authenticated': False
                    })
                    
            except:
                continue
        
        # If no successful auth, return summary of what we found
        return {
            'success': False,
            'message': 'Could not find /whoami endpoint, but tested other endpoints',
            'tested_endpoints': results
        }
    
    def validate_api_key_format(self) -> Dict[str, bool]:
        """
        Validate the API key format.
        
        Returns:
            Dictionary with validation results
        """
        validations = {
            'has_prefix': self.api_key.startswith('mk_'),
            'min_length': len(self.api_key) > 10,
            'no_spaces': ' ' not in self.api_key,
            'no_quotes': '"' not in self.api_key and "'" not in self.api_key,
        }
        
        return validations


def print_results(api_key: str, results: Dict[str, Any], validations: Dict[str, bool]):
    """
    Pretty print the test results.
    
    Args:
        api_key: The API key being tested
        results: Results from API call
        validations: Validation results for the API key format
    """
    print("\n" + "="*60)
    print("🔐 MOSAIC API AUTHENTICATION TEST")
    print("="*60)
    
    # Show API key (masked)
    if len(api_key) > 20:
        masked_key = f"{api_key[:10]}...{api_key[-4:]}"
    else:
        masked_key = f"{api_key[:6]}..." if len(api_key) > 6 else "***"
    
    print(f"\n📌 API Key: {masked_key}")
    print(f"🌐 API URL: {results.get('base_url', 'https://api.mosaic.so')}")
    
    # Format validation
    print("\n📋 API Key Format Validation:")
    all_valid = True
    for check, passed in validations.items():
        icon = "✅" if passed else "❌"
        check_name = check.replace('_', ' ').title()
        print(f"   {icon} {check_name}")
        if not passed:
            all_valid = False
    
    if not all_valid:
        print("\n⚠️  Warning: API key format appears incorrect!")
        print("   Mosaic API keys should start with 'mk_'")
    
    # API call results
    print("\n📡 API Call Results:")
    
    if results.get('success'):
        print(f"   ✅ Authentication successful!")
        
        if 'endpoint' in results:
            print(f"   📍 Endpoint: {results['endpoint']}")
        
        print(f"   📊 Status Code: {results.get('status_code', 'N/A')}")
        
        if results.get('data'):
            print(f"\n📦 Response Data:")
            # Pretty print the response data
            data_str = json.dumps(results['data'], indent=2)
            for line in data_str.split('\n'):
                print(f"   {line}")
        
        if results.get('note'):
            print(f"\n💡 Note: {results['note']}")
            
    else:
        print(f"   ❌ Authentication failed!")
        
        if results.get('status_code'):
            print(f"   📊 Status Code: {results['status_code']}")
            
            if results['status_code'] == 401:
                print("\n   🔒 Error: Unauthorized (401)")
                print("      The API key is invalid or has been revoked.")
                print("      Please check your API key in the Mosaic dashboard.")
            elif results['status_code'] == 403:
                print("\n   🚫 Error: Forbidden (403)")
                print("      The API key doesn't have permission for this operation.")
            elif results['status_code'] == 404:
                print("\n   🔍 Error: Not Found (404)")
                print("      The /whoami endpoint doesn't exist.")
                
                if results.get('tested_endpoints'):
                    print("\n   📝 Tested alternative endpoints:")
                    for endpoint_result in results['tested_endpoints']:
                        if endpoint_result.get('exists'):
                            auth_status = "🔒 Requires auth" if not endpoint_result.get('authenticated') else "✅ Authenticated"
                            print(f"      • {endpoint_result['endpoint']}: {auth_status} ({endpoint_result['status_code']})")
            else:
                print(f"\n   ⚠️  Unexpected status code: {results['status_code']}")
        
        if results.get('error'):
            print(f"\n   🐛 Error Details: {results['error']}")
        
        if results.get('response'):
            print(f"\n   📄 Response Body:")
            try:
                response_data = json.loads(results['response'])
                for line in json.dumps(response_data, indent=2).split('\n'):
                    print(f"      {line}")
            except:
                # If not JSON, print as-is
                print(f"      {results['response']}")
    
    # Summary
    print("\n" + "="*60)
    if results.get('success') and all_valid:
        print("✅ SUCCESS: Your API key is valid and working correctly!")
        print("\nYou can now use this API key with:")
        print("  • add_triggers.py - to add YouTube triggers")
        print("  • webhook_listener.py - to receive webhooks")
        print("  • Any other Mosaic API operations")
    elif results.get('success'):
        print("⚠️  PARTIAL SUCCESS: API key works but format is non-standard")
    else:
        print("❌ FAILED: Unable to authenticate with the provided API key")
        print("\nTroubleshooting steps:")
        print("  1. Verify your API key in the Mosaic dashboard")
        print("  2. Ensure the key starts with 'mk_'")
        print("  3. Check that the key hasn't been revoked")
        print("  4. Try generating a new API key if needed")
    
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Test Mosaic API authentication',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Using environment variable
  export MOSAIC_API_KEY=mk_your_api_key
  python test_auth.py
  
  # Using command line argument
  python test_auth.py --api-key mk_your_api_key
  
  # Test with custom API URL
  python test_auth.py --api-key mk_xxx --base-url https://api.mosaic.so
  
  # Verbose output
  python test_auth.py --verbose
        '''
    )
    
    parser.add_argument(
        '--api-key',
        help='Mosaic API key (or set MOSAIC_API_KEY env var)'
    )
    
    parser.add_argument(
        '--base-url',
        default='https://api.mosaic.so',
        help='Base URL for Mosaic API (default: https://api.mosaic.so)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show verbose output including all tested endpoints'
    )
    
    args = parser.parse_args()
    
    # Get API key from args or environment
    api_key = args.api_key or os.environ.get('MOSAIC_API_KEY')
    
    if not api_key:
        print("❌ Error: API key is required")
        print("\nPlease provide an API key using one of these methods:")
        print("  1. Command line: python test_auth.py --api-key mk_xxx")
        print("  2. Environment: export MOSAIC_API_KEY=mk_xxx")
        sys.exit(1)
    
    # Create tester
    tester = MosaicAuthTester(api_key, args.base_url)
    
    # Validate API key format
    validations = tester.validate_api_key_format()
    
    # Test authentication
    print("\n🔄 Testing API authentication...")
    results = tester.test_whoami()
    results['base_url'] = args.base_url
    
    # Print results
    print_results(api_key, results, validations)
    
    # Exit code based on success
    sys.exit(0 if results.get('success') else 1)


if __name__ == "__main__":
    main()
