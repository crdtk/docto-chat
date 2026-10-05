"""Benchmark quantized vs non-quantized model performance."""

import time
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.models import ModelManager

def benchmark_model(quantize: bool = False) -> dict:
    """Benchmark model with optional quantization.

    Args:
        quantize: Whether to use 8-bit quantization

    Returns:
        Dict with load_time, model_size_gb, throughput
    """
    os.environ["QUANTIZE"] = "true" if quantize else "false"

    print(f"\n{'='*60}")
    print(f"Benchmarking: {'8-bit Quantized' if quantize else 'Full Precision (float32)'}")
    print(f"{'='*60}")

    # Measure load time
    start = time.time()
    mm = ModelManager()
    load_time = time.time() - start
    print(f"Load time: {load_time:.2f}s")

    # Estimate model size (rough, doesn't account for optimizer state)
    total_params = sum(p.numel() for p in mm.model.parameters())
    bytes_per_param = 1 if quantize else 4
    model_size_gb = (total_params * bytes_per_param) / 1e9
    print(f"Estimated model size: {model_size_gb:.2f}GB ({total_params:,} params)")

    # Measure generation throughput
    prompt = "What is aspirin? " * 5
    inputs = mm.tokenizer(prompt, return_tensors="pt")

    start = time.time()
    outputs = mm.model.generate(**inputs, max_new_tokens=20)
    gen_time = time.time() - start
    tokens = outputs.shape[1] - inputs['input_ids'].shape[1]
    throughput = tokens / gen_time if gen_time > 0 else 0

    print(f"Generation time: {gen_time:.2f}s ({tokens} new tokens)")
    print(f"Throughput: {throughput:.2f} tok/s")

    return {
        "quantized": quantize,
        "load_time": load_time,
        "model_size_gb": model_size_gb,
        "throughput": throughput,
        "total_params": total_params,
    }

if __name__ == "__main__":
    print("\nComparing model quantization performance...\n")

    # Benchmark without quantization
    results_no_quant = benchmark_model(False)

    # Benchmark with quantization
    results_quant = benchmark_model(True)

    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"\nMemory reduction: {(1 - results_quant['model_size_gb'] / results_no_quant['model_size_gb']) * 100:.1f}%")
    print(f"  Full precision: {results_no_quant['model_size_gb']:.2f}GB")
    print(f"  8-bit quantized: {results_quant['model_size_gb']:.2f}GB")

    throughput_change = (results_quant['throughput'] / results_no_quant['throughput'] - 1) * 100
    print(f"\nThroughput change: {throughput_change:+.1f}%")
    print(f"  Full precision: {results_no_quant['throughput']:.2f} tok/s")
    print(f"  8-bit quantized: {results_quant['throughput']:.2f} tok/s")

    load_time_change = (results_quant['load_time'] / results_no_quant['load_time'] - 1) * 100
    print(f"\nLoad time change: {load_time_change:+.1f}%")
    print(f"  Full precision: {results_no_quant['load_time']:.2f}s")
    print(f"  8-bit quantized: {results_quant['load_time']:.2f}s")
