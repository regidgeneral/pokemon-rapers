"""Tạo sẵn ảnh mặt trước (thường + shiny) của mọi loài FireRed vào sprites\\fr\\ (chỉ cần chạy một lần, cần pillow).
  py -3 gen_sprites.py"""
import os, struct, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mm_core import Rom, EMERALD, SPRITE_ROOT

B = 0x08000000


def to_image(tiles, pal):
    img = Image.new('RGBA', (64, 64))
    px = img.load()
    for t in range(64):
        tx, ty = (t % 8) * 8, (t // 8) * 8
        for i in range(32):
            b = tiles[t * 32 + i]
            y, x = i // 4, (i % 4) * 2
            for k, v in enumerate((b & 15, b >> 4)):
                px[tx + x + k, ty + y] = (0, 0, 0, 0) if v == 0 else pal[v] + (255,)
    return img


def make_aow_decoder(r):
    table = r.profile.sprite_front

    def decode(sp):
        ptr = struct.unpack_from('<I', r.d, r._o(table) + 8 * sp)[0]
        if not B <= ptr < B + len(r.d) or r.d[ptr - B] != 0x10:      # cuối bảng là dữ liệu rác, không phải LZ77
            raise ValueError('không có ảnh cho loài %d' % sp)
        tiles = r.lz77(ptr)
        if len(tiles) < 0x800:
            raise ValueError('ảnh loài %d thiếu dữ liệu' % sp)
        return tiles
    return decode


def generate():
    prof = EMERALD
    r = Rom(prof)
    out_dir = os.path.join(SPRITE_ROOT, prof.sprite_dir)
    os.makedirs(out_dir, exist_ok=True)
    decode = make_aow_decoder(r)
    ok = bad = 0
    for sp in range(1, prof.sprite_max + 1):
        try:
            tiles = decode(sp)
            to_image(tiles, r.palette(sp, False)).save(os.path.join(out_dir, '%d.png' % sp))
            to_image(tiles, r.palette(sp, True)).save(os.path.join(out_dir, '%d_s.png' % sp))
            ok += 1
        except Exception as e:
            bad += 1
    print('%s: %d loai co anh, %d loai bo qua (khong co du lieu), thu muc %s' % (prof.title, ok, bad, out_dir))


if __name__ == '__main__':
    generate()
