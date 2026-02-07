"""
Quick Import Verification Script
Tests that critical imports work without loading heavy models.
"""

print("=" * 50)
print("DevMind Import Verification")
print("=" * 50)

# Test 1: Embeddings module
print("\n[Test 1] devmind.embeddings imports...")
try:
    from devmind.embeddings import get_model_manager, ModelManager, Encoder
    print("✓ SUCCESS: devmind.embeddings")
except Exception as e:
    print(f"✗ FAILED: {e}")
    exit(1)

# Test 2: Vectorstore module  
print("\n[Test 2] devmind.vectorstore imports...")
try:
    from devmind.vectorstore import IndexManager, FAISSClient
    print("✓ SUCCESS: devmind.vectorstore")
except Exception as e:
    print(f"✗ FAILED: {e}")
    exit(1)

# Test 3: Container initialization (without loading models)
print("\n[Test 3] devmind.core.container imports...")
try:
    from devmind.core.container import DIContainer, initialize_container, get_container
    print("✓ SUCCESS: devmind.core.container")
except Exception as e:
    print(f"✗ FAILED: {e}")
    exit(1)

# Test 4: API app creation (without starting server)
print("\n[Test 4] devmind.api.app imports...")
try:
    from devmind.api.app import create_app
    print("✓ SUCCESS: devmind.api.app")
except Exception as e:
    print(f"✗ FAILED: {e}")
    exit(1)

# Test 5: LLM module
print("\n[Test 5] devmind.llm imports...")
try:
    from devmind.llm import get_llm_manager, ChatEngine
    print("✓ SUCCESS: devmind.llm")
except Exception as e:
    print(f"✗ FAILED: {e}")
    exit(1)

print("\n" + "=" * 50)
print("✓ ALL IMPORT TESTS PASSED!")
print("=" * 50)
print("\nThe critical import errors have been FIXED.")
print("Core modules can now be imported successfully.")
print("\nNote: Full runtime testing requires:")
print("  - Running Qdrant vector database")
print("  - Running PostgreSQL")
print("  - Running Redis")
print("  - Downloading ML models")
