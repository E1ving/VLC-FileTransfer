import numpy as np

def evaluate(in_path, out_path, vout_path):
    with open(in_path, 'rb') as f1, open(out_path, 'rb') as f2, open(vout_path, 'rb') as f3:
        original = np.frombuffer(f1.read(), dtype=np.uint8)
        recovered = np.frombuffer(f2.read(), dtype=np.uint8)
        masks = np.frombuffer(f3.read(), dtype=np.uint8)

    # 1. 长度对比 (丢包评估)
    min_len = min(len(original), len(recovered))
    original = original[:min_len]
    recovered = recovered[:min_len]
    
    # 2. 计算比特级误码率 (BER - Bit Error Rate)
    # 将字节转为比特位
    orig_bits = np.unpackbits(original)
    rec_bits = np.unpackbits(recovered)
    
    # 计算差异
    diff = (orig_bits != rec_bits)
    total_bits = len(orig_bits)
    bit_errors = np.sum(diff)
    ber = bit_errors / total_bits
    
    # 3. 基于 vout 的有效性统计
    # 统计 vout 中 0xFF 的比例（即被标记为“有效”的字节比例）
    valid_ratio = np.sum(masks == 0xFF) / len(masks)
    
    print(f"--- VLC 系统传输评估报告 ---")
    print(f"传输总字节数: {total_bits // 8} Bytes")
    print(f"比特误码率 (BER): {ber:.6f}")
    print(f"帧有效率 (Valid Frame Ratio): {valid_ratio:.2%}")
    print(f"错误比特数: {bit_errors} bits")

if __name__ == "__main__":
    evaluate("in.bin", "out.bin", "vout.bin")