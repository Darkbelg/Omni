#!/usr/bin/env python3
"""
PyTorch Memory Cleanup Utility

This script provides functions to properly clean up PyTorch resources,
particularly GPU memory allocations.
"""

import gc
import torch
import psutil
import os
import argparse
from typing import Optional, List, Any
from contextlib import contextmanager


def clear_pytorch_memory(verbose: bool = True) -> None:
    """
    Perform a thorough cleanup of PyTorch memory resources.

    Args:
        verbose: Whether to print memory usage information
    """
    # Get initial memory stats
    if verbose and torch.cuda.is_available():
        initial_gpu = torch.cuda.memory_allocated() / (1024**3)

    initial_ram = psutil.Process(os.getpid()).memory_info().rss / (1024**3)

    # Delete all global variables that are tensors or models
    for obj_name in list(globals()):
        if obj_name[0] != '_' and isinstance(globals()[obj_name], (torch.Tensor, torch.nn.Module)):
            if verbose:
                print(f"Deleting global tensor/model: {obj_name}")
            del globals()[obj_name]

    # Clear CUDA cache
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()

    # Force garbage collection
    gc.collect()

    # Print memory usage information if verbose
    if verbose:
        current_ram = psutil.Process(os.getpid()).memory_info().rss / (1024**3)
        print(f"RAM Memory: {current_ram:.2f} GB (freed {initial_ram - current_ram:.2f} GB)")

        if torch.cuda.is_available():
            current_gpu = torch.cuda.memory_allocated() / (1024**3)
            print(f"GPU Memory: {current_gpu:.2f} GB (freed {initial_gpu - current_gpu:.2f} GB)")


@contextmanager
def safe_model_context(model: Any = None, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
    """
    Context manager for safely using PyTorch models with automatic cleanup.

    Args:
        model: Optional model to load to the specified device
        device: Device to use ('cuda' or 'cpu')

    Example:
        with safe_model_context(my_model, 'cuda') as model:
            outputs = model(inputs)
    """
    try:
        if model is not None and device == 'cuda' and torch.cuda.is_available():
            model = model.to(device)
        yield model
    finally:
        # Cleanup when exiting the context
        if model is not None and device == 'cuda' and torch.cuda.is_available():
            model = model.to('cpu')
        clear_pytorch_memory(verbose=False)


def cleanup_torch_processes(verbose: bool = True) -> None:
    """
    Attempt to identify and terminate orphaned PyTorch processes.

    Args:
        verbose: Whether to print process information
    """
    import subprocess
    import signal

    # Find Python processes that might be PyTorch-related
    try:
        result = subprocess.run(
            ["ps", "-eo", "pid,rss,command"],
            capture_output=True,
            text=True,
            check=True
        )

        lines = result.stdout.strip().split('\n')
        current_pid = os.getpid()

        for line in lines:
            if 'python' in line.lower() and 'torch' in line.lower():
                parts = line.split()
                if len(parts) >= 3:
                    pid = int(parts[0])
                    memory_kb = int(parts[1])

                    # Skip current process
                    if pid == current_pid:
                        continue

                    if verbose:
                        print(f"Found PyTorch process: PID {pid}, Memory: {memory_kb/1024:.2f} MB")

                    # Ask for confirmation before killing
                    if verbose:
                        confirm = input(f"Terminate process {pid}? (y/n): ")
                        if confirm.lower() == 'y':
                            try:
                                os.kill(pid, signal.SIGTERM)
                                print(f"Process {pid} terminated.")
                            except Exception as e:
                                print(f"Failed to terminate process {pid}: {e}")
    except Exception as e:
        print(f"Error finding PyTorch processes: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PyTorch Memory Cleanup Utility')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress verbose output')
    parser.add_argument('--processes', '-p', action='store_true', help='Cleanup PyTorch processes')

    args = parser.parse_args()

    print("Running PyTorch memory cleanup...")
    clear_pytorch_memory(verbose=not args.quiet)

    if args.processes:
        cleanup_torch_processes(verbose=not args.quiet)

    print("Cleanup complete.")