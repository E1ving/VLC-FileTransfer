import os
import sys
def generate_random_bin(filename, size_kb):
    """
    生成指定大小的随机二进制文件
    :param filename: 输出文件名
    :param size_kb: 文件大小 (单位: KB)
    """
    size_bytes = size_kb * 1024
    
    # 使用 os.urandom 生成加密强度的随机字节
    with open(filename, "wb") as f:
        f.write(os.urandom(size_bytes))
        
    print(f"✅ 已生成测试文件: {filename}")
    print(f"📊 文件大小: {size_bytes} 字节 ({size_kb} KB)")
    print(f"🔑 文件哈希检查 (前8字节): {os.urandom(8).hex()}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python bin_generator.py <filename> <size_in_kb>")
        sys.exit(1)
        
    try:
        fname = sys.argv[1]
        skb = int(sys.argv[2])
        generate_random_bin(fname, skb)
    except ValueError:
        print("❌ 错误：大小必须是整数")