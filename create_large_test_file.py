# 创建一个足够大的测试文件，确保需要122帧来编码

# 每帧可以编码的字节数
bytes_per_frame = 843

# 需要的帧数
required_frames = 122

# 总数据量
required_bytes = bytes_per_frame * required_frames

# 创建测试数据
test_data = b"Hello, this is a test file for VLC File Transfer. " * 10000

# 截取需要的长度
test_data = test_data[:required_bytes]

# 写入文件
with open("data/test_large.bin", "wb") as f:
    f.write(test_data)

print(f"✅ 测试文件创建完成: data/test_large.bin")
print(f"📊 文件大小: {len(test_data)} bytes")
print(f"📊 需要的帧数: {required_frames}")
