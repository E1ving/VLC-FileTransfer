import argparse
import os

from core.decoder_engine import DecoderEngine


# 选择一个安全的拆帧输出目录：若目标目录已包含 png，则自动使用带后缀的新目录，避免混入旧帧
def _choose_output_frames_dir(frames_dir: str) -> str:
    base = frames_dir
    candidate = base
    suffix = 0
    while True:
        if not os.path.exists(candidate):
            os.makedirs(candidate)
            return candidate

        if not os.path.isdir(candidate):
            raise RuntimeError(f"frames_dir is not a directory: {candidate}")

        has_png = any(name.lower().endswith(".png") for name in os.listdir(candidate))
        if not has_png:
            return candidate

        suffix += 1
        candidate = f"{base}_{suffix}"


# 将 vout.bin（每 bit 用 1 个字节 0/1 表示）按 8 bit 打包回真实字节流，生成 out.bin
def _pack_vout_bits_to_bytes(vout_path: str, out_path: str) -> int:
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)

    bytes_written = 0
    cur = 0
    cur_bits = 0
    with open(vout_path, "rb") as fin, open(out_path, "wb") as fout:
        while True:
            chunk = fin.read(8192)
            if not chunk:
                break
            for b in chunk:
                bit = 1 if b else 0
                cur = (cur << 1) | bit
                cur_bits += 1
                if cur_bits == 8:
                    fout.write(bytes([cur]))
                    bytes_written += 1
                    cur = 0
                    cur_bits = 0
    return bytes_written


# 解码入口：视频拆帧 -> 图片解调+CRC -> 输出 vout.bin -> 可选输出 out.bin
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video_path")
    parser.add_argument("out_path", nargs="?", default=None)
    parser.add_argument("vout_path", nargs="?", default=None)
    parser.add_argument("--frames-dir", default="temp_extracted")
    parser.add_argument("--fps-limit", type=float, default=None)
    parser.add_argument("--out", default=os.path.join("data", "out.bin"))
    parser.add_argument("--vout", default=os.path.join("data", "vout.bin"))
    parser.add_argument("--no-out", action="store_true")
    parser.add_argument("--skip-extract", action="store_true")
    parser.add_argument("--keep-bad-crc", action="store_true")
    args = parser.parse_args()

    dec = DecoderEngine()

    out_path = args.out_path or args.out
    vout_path = args.vout_path or args.vout

    if not args.skip_extract:
        # 1) 视频 -> 图片序列（OpenCV VideoCapture）
        frames_dir = _choose_output_frames_dir(args.frames_dir)
        extracted = dec.video_to_frames(args.video_path, frames_dir, fps_limit=args.fps_limit)
        print(f"✅ 已提取 {extracted} 帧至 {frames_dir}")
    else:
        # 直接使用已有图片目录（不重新拆帧）
        frames_dir = args.frames_dir

    # 2) 图片序列 -> vout.bin（每个 bit 保存为一个字节 0/1；可按 CRC 过滤坏帧）
    bits_written = dec.frames_to_vout(
        frames_dir,
        output_path=vout_path,
        require_crc_pass=not args.keep_bad_crc,
    )
    print(f"✅ 已写入 vout: {vout_path} ({bits_written} bytes)")

    if not args.no_out:
        # 3) vout.bin -> out.bin（将 bit 流打包为真实字节流）
        out_bytes = _pack_vout_bits_to_bytes(vout_path, out_path)
        print(f"✅ 已写入 out: {out_path} ({out_bytes} bytes)")


if __name__ == "__main__":
    main()
