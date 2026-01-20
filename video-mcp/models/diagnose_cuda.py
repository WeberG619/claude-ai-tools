import torch
import os

print("=" * 50)
print("PyTorch CUDA Diagnostic")
print("=" * 50)

print(f"\nPyTorch version: {torch.__version__}")
print(f"PyTorch built with CUDA: {torch.version.cuda}")

print(f"\nCUDA_PATH: {os.environ.get('CUDA_PATH', 'NOT SET')}")

if hasattr(torch.cuda, 'get_arch_list'):
    print(f"CUDA arch list: {torch.cuda.get_arch_list()}")

print(f"\nCUDA available: {torch.cuda.is_available()}")
print(f"CUDA device count: {torch.cuda.device_count()}")

if torch.backends.cudnn.is_available():
    print(f"cuDNN version: {torch.backends.cudnn.version()}")
else:
    print("cuDNN: Not available")

try:
    torch.cuda.init()
    print("\nCUDA init: Success")
except Exception as e:
    print(f"\nCUDA init error: {e}")

# Check if CUDA DLLs are findable
import ctypes
import sys

cuda_dlls = ['cudart64_118.dll', 'cublas64_11.dll', 'cublasLt64_11.dll']
print("\nChecking CUDA DLLs:")
for dll in cuda_dlls:
    try:
        ctypes.CDLL(dll)
        print(f"  {dll}: Found")
    except OSError as e:
        print(f"  {dll}: NOT FOUND - {e}")

# Check PATH for CUDA
print("\nPATH entries containing 'CUDA':")
for p in os.environ.get('PATH', '').split(';'):
    if 'cuda' in p.lower():
        print(f"  {p}")
