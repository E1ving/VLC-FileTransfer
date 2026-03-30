# VLC-FileTransfer
XMU Computer Networks Course Project – Group 19

可见光文件传输系统 - 通过屏幕显示和摄像头拍摄实现数据传输。

## 系统架构

```
二进制文件 → [发送端] → 视频文件 → [屏幕播放] → [手机拍摄] → [接收端] → 二进制文件
```

## 快速开始

### 发送端（编码器）

将二进制文件编码为视频：

```bash
python encoder.py in.bin out.mp4 1000
```

参数说明：
- `in.bin`: 输入二进制文件（长度 ≤ 10MB）
- `out.mp4`: 输出视频文件
- `1000`: 视频最大时长（毫秒）

**注意**：程序会根据时长限制自动计算最大数据容量，超出部分将被截断。

### 接收端（解码器）

将拍摄的视频解码为二进制文件：

```bash
python decoder.py recorded.mp4 out.bin vout.bin
```

参数说明：
- `recorded.mp4`: 手机拍摄的视频
- `out.bin`: 解码输出的二进制文件
- `vout.bin`: 有效性标记文件（每字节8位掩码，1=正确，0=错误）

### 完整流程示例

```bash
# 1. 编码（生成1秒视频）
python encoder.py in.bin out.mp4 1000

# 2. 在屏幕上播放 out.mp4，用手机拍摄保存为 recorded.mp4

# 3. 解码
python decoder.py recorded.mp4 received.bin vout.bin
```

## 项目结构

```
VLC-FileTransfer/
├── core/                   # 核心编解码模块
│   ├── protocol.py         # 物理层协议参数
│   ├── encoder_engine.py   # 图像编码引擎
│   └── decoder_engine.py   # 图像解码引擎
├── utils/                  # 工具模块
│   └── video_muxer.py      # 视频合成/拆解
├── test/                   # 测试脚本
│   ├── test_loopback.py    # 编解码闭环测试
│   └── test_muxer.py       # 视频muxer测试
├── docs/
│   └── protocol_spec.md    # 协议规范文档
├── encoder.py              # 发送端主程序
└── decoder.py              # 接收端主程序
```

## 协议参数

- 屏幕分辨率: 1920 × 1080
- 帧率: 60 FPS
- 每帧数据容量: 2976 bits
- 每帧总容量: 3136 bits (含 CRC-16)
- 传输速率: ~178 kbps

## 测试

运行单元测试：

```bash
# 测试编解码闭环
python test/test_loopback.py

# 测试视频muxer
python test/test_muxer.py
```

## 依赖

- Python 3.8+
- OpenCV (`pip install opencv-python`)
- NumPy (`pip install numpy`)
- FFmpeg（可选，用于无损编码）