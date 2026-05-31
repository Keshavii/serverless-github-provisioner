#!/usr/bin/env python3
"""Quick validator tests."""

from src.business.validators import RepositoryRequest
from src.shared.exceptions import ValidationError

print('Testing validators...\n')

# Test 1: Valid input
try:
    valid = RepositoryRequest(
        repo_name='my-service',
        github_org='hiyamodi-org',
        description='A test service',
        vp_name='Hiya Modi',
        director_name='Hiya Modi',
        em_name='Bob Johnson',
        product_line='Platform',
        department='Engineering',
        repo_type='Private',
        code_type='Python'
    )
    print('✅ Test 1 PASSED: Valid input accepted')
except Exception as e:
    print(f'❌ Test 1 FAILED: {e}')

# Test 2: Empty repo_name
try:
    invalid = RepositoryRequest(
        repo_name='',
        github_org='hiyamodi-org',
        description='Test',
        vp_name='John',
        director_name='Jane',
        em_name='Bob',
        product_line='Platform',
        department='Eng',
        repo_type='Private',
        code_type='Python'
    )
    print('❌ Test 2 FAILED: Empty repo_name should have been rejected')
except ValidationError as e:
    print(f'✅ Test 2 PASSED: Empty repo_name rejected')
except Exception as e:
    print(f'✅ Test 2 PASSED: Empty repo_name rejected (Pydantic error)')

# Test 3: Empty github_org
try:
    invalid = RepositoryRequest(
        repo_name='my-service',
        github_org='',
        description='Test',
        vp_name='John',
        director_name='Jane',
        em_name='Bob',
        product_line='Platform',
        department='Eng',
        repo_type='Private',
        code_type='Python'
    )
    print('❌ Test 3 FAILED: Empty github_org should have been rejected')
except ValidationError as e:
    print(f'✅ Test 3 PASSED: Empty github_org rejected')
except Exception as e:
    print(f'✅ Test 3 PASSED: Empty github_org rejected (Pydantic error)')

# Test 4: Whitespace-only description
try:
    invalid = RepositoryRequest(
        repo_name='my-service',
        github_org='hiyamodi-org',
        description='   ',
        vp_name='John',
        director_name='Jane',
        em_name='Bob',
        product_line='Platform',
        department='Eng',
        repo_type='Private',
        code_type='Python'
    )
    print('❌ Test 4 FAILED: Whitespace-only description should have been rejected')
except (ValidationError, Exception) as e:
    print(f'✅ Test 4 PASSED: Whitespace-only description rejected')

# Test 5: Empty vp_name
try:
    invalid = RepositoryRequest(
        repo_name='my-service',
        github_org='hiyamodi-org',
        description='Test',
        vp_name='',
        director_name='Jane',
        em_name='Bob',
        product_line='Platform',
        department='Eng',
        repo_type='Private',
        code_type='Python'
    )
    print('❌ Test 5 FAILED: Empty vp_name should have been rejected')
except (ValidationError, Exception) as e:
    print(f'✅ Test 5 PASSED: Empty vp_name rejected')

print('\n🎉 All validator tests completed!')
