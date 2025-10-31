#!/usr/bin/env python3
"""
Generate a secure Flask secret key for session encryption.
"""

import secrets
import sys

def generate_secret_key(length=32):
    """Generate a cryptographically secure random secret key.
    
    Args:
        length: Logarithm of the desired number of random bytes (default: 32)
    
    Returns:
        A hexadecimal string secret key
    """
    return secrets.token_hex(length)

if __name__ == '__main__':
    length = 32
    if len(sys.argv) > 1:
        try:
            length = int(sys.argv[1])
        except ValueError:
            print(f"Invalid length '{sys.argv[1]}'. Using default length of 32.", file=sys.stderr)
    
    secret_key = generate_secret_key(length)
    print(secret_key)
    print(f"\n# Length: {len(secret_key)} characters ({length} bytes)", file=sys.stderr)




