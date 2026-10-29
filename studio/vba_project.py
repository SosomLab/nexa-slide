# -*- coding: utf-8 -*-
"""엑셀 VBA 프로젝트(xl/vbaProject.bin) 읽기·다시 쓰기 - 외부 라이브러리 없이(MS-CFB 복합 파일 · MS-OVBA 압축).

    python3 studio/vba_project.py <vbaProject.bin>            # 모듈 목록과 소스
    python3 studio/vba_project.py <bin> --json                # [{name, kind, code}] JSON

read_modules(data)         → [{"name", "kind": "std"|"doc"|"cls", "code"}]  (소스는 프로젝트 코드 페이지로 풀어 읽는다)
write_modules(data, mods)  → 새 vbaProject.bin 바이트. mods 의 code 로 모듈 소스를 바꾸고, 새 표준 모듈은 더하고, 빠진 표준 모듈은 뺀다.
    문서·클래스 모듈(통합 문서·시트·폼)은 코드만 바꾸고 더하거나 빼지 않는다.
    다시 쓴 프로젝트는 컴파일된 코드(p-code 성능 캐시·__SRP_ 스트림)를 버리고 _VBA_PROJECT 판을 0xFFFF 로 둔다 -
    MS-OVBA 2.3.4.1 규칙대로라 엑셀이 열 때 소스에서 다시 컴파일한다.
"""
import argparse
import json
import struct
import sys

# ---------------------------------------------------------------- MS-OVBA 2.4.1 압축
def decompress(buf):
    if not buf or buf[0] != 1:
        raise ValueError("VBA 압축 서명이 아니다")
    out, i = bytearray(), 1
    while i < len(buf):
        hdr = struct.unpack_from("<H", buf, i)[0]
        size, flag = (hdr & 0x0FFF) + 3, hdr & 0x8000
        chunk, i = buf[i + 2:i + size], i + size
        if not flag:
            out += chunk[:4096]
            continue
        start, j = len(out), 0
        while j < len(chunk):
            flags = chunk[j]
            j += 1
            for b in range(8):
                if j >= len(chunk):
                    break
                if not flags & (1 << b):
                    out.append(chunk[j])
                    j += 1
                    continue
                tok = struct.unpack_from("<H", chunk, j)[0]
                j += 2
                d = len(out) - start
                bits = max((d - 1).bit_length(), 4)
                ln = (tok & (0xFFFF >> bits)) + 3
                off = (tok >> (16 - bits)) + 1
                src = len(out) - off
                for k in range(ln):
                    out.append(out[src + k])
    return bytes(out)


def compress(data):
    out = bytearray(b"\x01")
    for cs in range(0, len(data), 4096):  # 빈 소스 = 서명 바이트만
        chunk = data[cs:cs + 4096]
        body, p = bytearray(), 0
        while p < len(chunk):
            fpos, flags = len(body), 0
            body.append(0)
            for b in range(8):
                if p >= len(chunk):
                    break
                bits = max((p - 1).bit_length(), 4) if p else 4
                maxlen, maxoff = (0xFFFF >> bits) + 3, 1 << bits
                best, boff = 0, 0
                lo = max(0, p - maxoff)
                for s in range(p - 1, lo - 1, -1):  # 가장 긴 일치(창 안, 겹쳐도 된다)
                    n = 0
                    while n < maxlen and p + n < len(chunk) and chunk[s + n] == chunk[p + n]:
                        n += 1
                    if n > best:
                        best, boff = n, p - s
                        if n == maxlen:
                            break
                if best >= 3:
                    flags |= 1 << b
                    body += struct.pack("<H", ((boff - 1) << (16 - bits)) | (best - 3))
                    p += best
                else:
                    body.append(chunk[p])
                    p += 1
            body[fpos] = flags
        if len(body) > 4096:  # 압축이 안 되면 그대로(정확히 4096 바이트 조각만 가능 - 끝 조각은 위에서 늘 줄어든다)
            out += struct.pack("<H", 0x3000 | (4096 + 2 - 3)) + chunk.ljust(4096, b"\x00")
        else:
            out += struct.pack("<H", 0xB000 | (len(body) + 2 - 3)) + body
    return bytes(out)


# ---------------------------------------------------------------- MS-CFB 복합 파일
FREE, END, FATSECT = 0xFFFFFFFF, 0xFFFFFFFE, 0xFFFFFFFD


class Cfb:
    """읽기: streams {경로: 바이트}(경로는 'VBA/dir' 처럼 '/'), storages [경로], clsid {경로: 16바이트}."""

    def __init__(self, data):
        if data[:8] != bytes.fromhex("D0CF11E0A1B11AE1"):
            raise ValueError("복합 파일(OLE)이 아니다")
        ss = 1 << struct.unpack_from("<H", data, 0x1E)[0]
        mss = 1 << struct.unpack_from("<H", data, 0x20)[0]
        nfat, dir0, cutoff, mf0, nmf, dif0, ndif = struct.unpack_from("<I I 4x I I I I I", data, 0x2C)
        sec = lambda n: data[(n + 1) * ss:(n + 2) * ss]  # noqa: E731
        difat = list(struct.unpack_from("<109I", data, 0x4C))
        d = dif0
        for _ in range(ndif):
            v = struct.unpack(f"<{ss // 4}I", sec(d))
            difat += v[:-1]
            d = v[-1]
        fat = []
        for s in difat[:nfat]:
            fat += struct.unpack(f"<{ss // 4}I", sec(s))

        def chain(s, f):
            seen = []
            while s not in (END, FREE) and s < len(f) and len(seen) <= len(f):
                seen.append(s)
                s = f[s]
            return seen
        read = lambda s: b"".join(sec(x) for x in chain(s, fat))  # noqa: E731
        dirs = read(dir0)
        ents = []
        for k in range(len(dirs) // 128):
            e = dirs[k * 128:(k + 1) * 128]
            nl = struct.unpack_from("<H", e, 64)[0]
            ents.append({"name": e[:max(nl - 2, 0)].decode("utf-16-le"), "type": e[66], "l": struct.unpack_from("<I", e, 68)[0],
                         "r": struct.unpack_from("<I", e, 72)[0], "c": struct.unpack_from("<I", e, 76)[0], "clsid": e[80:96],
                         "start": struct.unpack_from("<I", e, 116)[0], "size": struct.unpack_from("<Q", e, 120)[0] & 0xFFFFFFFF})
        minifat = list(struct.unpack(f"<{(nmf * ss) // 4}I", read(mf0))) if nmf else []
        ministream = read(ents[0]["start"]) if ents else b""
        self.streams, self.storages, self.clsid = {}, [], {}

        def walk(i, path, depth=0):
            if i >= len(ents) or i == FREE or depth > 200:
                return
            e = ents[i]
            walk(e["l"], path, depth + 1)
            walk(e["r"], path, depth + 1)
            p = (path + "/" if path else "") + e["name"]
            if e["type"] == 1:
                self.storages.append(p)
                self.clsid[p] = e["clsid"]
                walk(e["c"], p, depth + 1)
            elif e["type"] == 2:
                if e["size"] < cutoff:
                    raw = b"".join(ministream[x * mss:(x + 1) * mss] for x in chain(e["start"], minifat))
                else:
                    raw = read(e["start"])
                self.streams[p] = raw[:e["size"]]
        if ents:
            self.clsid[""] = ents[0]["clsid"]
            walk(ents[0]["c"], "")


def cfb_write(streams, storages, clsid=None):
    """streams {경로: 바이트} · storages [경로] → CFB v3(512 바이트 섹터) 바이트. 4096 바이트 미만 스트림은 미니 스트림에."""
    clsid = clsid or {}
    ss, mss, cutoff = 512, 64, 4096
    nodes = [{"name": "Root Entry", "type": 5, "path": "", "kids": []}]
    index = {"": 0}
    for p in sorted(set(storages) | {"/".join(s.split("/")[:k]) for s in streams for k in range(1, len(s.split("/")))}, key=lambda x: x.count("/")):
        index[p] = len(nodes)
        nodes.append({"name": p.split("/")[-1], "type": 1, "path": p, "kids": []})
    for p in streams:
        index[p] = len(nodes)
        nodes.append({"name": p.split("/")[-1], "type": 2, "path": p, "kids": []})
    for n in nodes[1:]:
        nodes[index["/".join(n["path"].split("/")[:-1])]]["kids"].append(index[n["path"]])
    key = lambda i: (len(nodes[i]["name"]), nodes[i]["name"].upper())  # noqa: E731 - CFB 이름 비교(길이 먼저, 대문자로)
    for n in nodes:
        n["l"] = n["r"] = n["c"] = FREE

    def tree(ids):  # 균형 이진 트리(모두 검정 - 읽는 쪽은 색을 검사하지 않는다)
        if not ids:
            return FREE
        m = len(ids) // 2
        nodes[ids[m]]["l"], nodes[ids[m]]["r"] = tree(ids[:m]), tree(ids[m + 1:])
        return ids[m]
    for n in nodes:
        if n["type"] in (1, 5):
            n["c"] = tree(sorted(n["kids"], key=key))
    # 미니 스트림
    mini, minifat = bytearray(), []
    for n in nodes:
        if n["type"] != 2:
            continue
        b = streams[n["path"]]
        n["size"] = len(b)
        if len(b) < cutoff:
            if not b:
                n["start"] = END
                continue
            k = (len(b) + mss - 1) // mss
            n["start"] = len(minifat)
            minifat += list(range(len(minifat) + 1, len(minifat) + k)) + [END]
            mini += b.ljust(k * mss, b"\x00")
    big = [n for n in nodes if n["type"] == 2 and n["size"] >= cutoff]
    secs = lambda nb: (nb + ss - 1) // ss  # noqa: E731
    ndir = secs(len(nodes) * 128)
    nmf = secs(len(minifat) * 4)
    nmini = secs(len(mini))
    nbig = sum(secs(n["size"]) for n in big)
    nfat = 1
    while True:
        total = nfat + ndir + nmf + nmini + nbig
        if secs(total * 4) <= nfat:
            break
        nfat += 1
    if nfat > 109:
        raise ValueError("파일이 너무 크다(DIFAT 미지원)")
    fat = [FATSECT] * nfat
    body = []

    def put(b, k):
        s = len(fat)
        fat.extend(list(range(s + 1, s + k)) + [END])
        body.append(b.ljust(k * ss, b"\x00"))
        return s
    dir0 = len(fat)
    dir_pos = len(body)
    put(b"", ndir)  # 디렉터리 - 아래에서 채운다
    mf0 = put(b"".join(struct.pack("<I", x) for x in minifat), nmf) if nmf else END
    nodes[0]["start"], nodes[0]["size"] = (put(bytes(mini), nmini), len(mini)) if nmini else (END, 0)
    for n in big:
        n["start"] = put(streams[n["path"]], secs(n["size"]))
    ents = bytearray()
    for n in nodes:
        nm = n["name"].encode("utf-16-le")[:62]
        e = bytearray(128)
        e[:len(nm)] = nm
        struct.pack_into("<H B B I I I", e, 64, len(nm) + 2, n["type"], 1, n["l"], n["r"], n["c"])
        e[80:96] = clsid.get(n["path"], b"\x00" * 16)[:16].ljust(16, b"\x00")
        struct.pack_into("<I Q", e, 116, n.get("start", END) if n["type"] != 1 else 0, n.get("size", 0) if n["type"] != 1 else 0)
        ents += e
    ents = ents.ljust(ndir * ss, b"\x00")
    for k in range(len(ents) // 128, ndir * ss // 128):  # 빈 칸 항목
        pass
    pad = bytearray(ents)
    for k in range(len(nodes), ndir * ss // 128):  # 쓰지 않는 디렉터리 항목은 형제·자식 없음
        struct.pack_into("<I I I", pad, k * 128 + 68, FREE, FREE, FREE)
    body[dir_pos] = bytes(pad)
    fat = fat + [FREE] * (nfat * ss // 4 - len(fat))
    fatb = b"".join(struct.pack("<I", x) for x in fat)
    hdr = bytearray(512)
    hdr[:8] = bytes.fromhex("D0CF11E0A1B11AE1")
    struct.pack_into("<H H H H H", hdr, 0x18, 0x3E, 3, 0xFFFE, 9, 6)
    struct.pack_into("<I I I I I I I I", hdr, 0x2C, nfat, dir0, 0, cutoff, mf0, nmf, END, 0)
    difat = list(range(nfat)) + [FREE] * (109 - nfat)
    struct.pack_into("<109I", hdr, 0x4C, *difat)
    return bytes(hdr) + fatb + b"".join(body)


# ---------------------------------------------------------------- VBA dir 스트림(MS-OVBA 2.3.4.2)
def _records(d):
    out, i = [], 0
    while i + 6 <= len(d):
        rid, size = struct.unpack_from("<H I", d, i)
        if rid == 0x0009:  # PROJECTVERSION - 크기 칸은 4 인데 실제로 6 바이트(주 판 4 + 부 판 2)
            size = 6
        out.append([rid, bytes(d[i + 6:i + 6 + size])])
        i += 6 + size
    return out


def _pack(recs):
    return b"".join(struct.pack("<H I", rid, 4 if rid == 0x0009 else len(b)) + b for rid, b in recs)


def _codepage(recs):
    for rid, b in recs:
        if rid == 0x0003:
            return struct.unpack("<H", b)[0]
    return 1252


def _enc(cp):
    return "cp949" if cp == 949 else f"cp{cp}"


def _modules(recs):
    """dir 레코드 → [(시작 위치, 끝 위치, {name, stream, offset, kind})] - 모듈마다 MODULENAME(0x19) ~ 끝(0x2B)."""
    cp, mods, cur = _codepage(recs), [], None
    for k, (rid, b) in enumerate(recs):
        if rid == 0x0019:
            cur = {"at": k, "name": b.decode(_enc(cp), "replace"), "kind": "std"}
        elif cur is None:
            continue
        elif rid == 0x0047:
            cur["name"] = b.decode("utf-16-le", "replace")
        elif rid == 0x001A:
            cur["stream"] = b.decode(_enc(cp), "replace")
        elif rid == 0x0032:
            cur["stream"] = b.decode("utf-16-le", "replace")
        elif rid == 0x0031:
            cur["offset"] = struct.unpack("<I", b)[0]
        elif rid == 0x0022:
            cur["kind"] = "doc"
        elif rid == 0x002B:
            cur["end"] = k
            mods.append(cur)
            cur = None
    return mods


def read_modules(data):
    cf = Cfb(data)
    vba = _vba_root(cf)
    recs = _records(decompress(cf.streams[vba + "dir"]))
    cp, out = _codepage(recs), []
    project = cf.streams.get(vba.rsplit("VBA/", 1)[0] + "PROJECT", b"").decode(_enc(cp), "replace")
    classes = {ln.split("=", 1)[1].strip() for ln in project.splitlines() if ln.startswith("Class=")}
    for m in _modules(recs):
        raw = cf.streams.get(vba + m.get("stream", m["name"]), b"")
        code = decompress(raw[m.get("offset", 0):]).rstrip(b"\x00").decode(_enc(cp), "replace") if raw else ""
        kind = "cls" if m["kind"] == "doc" and m["name"] in classes else m["kind"]
        out.append({"name": m["name"], "kind": kind, "code": _strip_attrs(code)})
    return out


def _vba_root(cf):
    for p in cf.streams:
        if p.endswith("VBA/dir"):
            return p[:-3]
    raise ValueError("VBA/dir 스트림이 없다")


ATTR = "Attribute VB_"


def _strip_attrs(code):
    """소스 앞의 Attribute VB_ 줄(모듈 속성 - 사람이 고치지 않는다)을 뺀다. 쓸 때 되살린다."""
    return "\r\n".join(ln for ln in code.replace("\r\n", "\n").split("\n") if not ln.startswith(ATTR)).strip("\r\n") + ("\r\n" if code.strip() else "")


def _attrs_of(code):
    return [ln for ln in code.replace("\r\n", "\n").split("\n") if ln.startswith(ATTR)]


def write_modules(data, mods):
    """mods [{name, kind, code}] 로 모듈 소스를 바꾼 새 vbaProject.bin."""
    cf = Cfb(data)
    vba = _vba_root(cf)
    base = vba.rsplit("VBA/", 1)[0]
    recs = _records(decompress(cf.streams[vba + "dir"]))
    cp = _codepage(recs)
    enc = _enc(cp)
    want = {m["name"]: m for m in mods}
    old = _modules(recs)
    have = {m["name"] for m in old}
    streams = {p: b for p, b in cf.streams.items() if not p.split("/")[-1].startswith("__SRP_")}
    keep, drop = [], set()
    for m in old:  # 있던 모듈 - 코드 바꾸기, 표준 모듈이 빠졌으면 지우기
        sp = vba + m.get("stream", m["name"])
        raw = cf.streams.get(sp, b"")
        src = decompress(raw[m.get("offset", 0):]).rstrip(b"\x00").decode(enc, "replace") if raw else ""
        if m["name"] not in want and m["kind"] == "std":
            drop.add(m["name"])
            streams.pop(sp, None)
            continue
        code = want[m["name"]]["code"] if m["name"] in want else _strip_attrs(src)
        full = "\r\n".join(_attrs_of(src) or [f'Attribute VB_Name = "{m["name"]}"']) + "\r\n" + code.replace("\r\n", "\n").replace("\n", "\r\n")
        streams[sp] = compress(full.encode(enc, "replace"))
        keep.append(m)
    # dir 다시 쓰기 - 지운 모듈 레코드 빼기, 오프셋 0(성능 캐시 없음), 새 표준 모듈 더하기, 모듈 수(PROJECTMODULES 0x0F) 고치기
    out, k = [], 0
    starts = {m["at"]: m for m in old}
    while k < len(recs):
        if k in starts:
            m = starts[k]
            seg = recs[m["at"]:m["end"] + 1]
            if m["name"] not in drop:
                out += [[rid, struct.pack("<I", 0) if rid == 0x0031 else b] for rid, b in seg]
            k = m["end"] + 1
            continue
        out.append(recs[k])
        k += 1
    adds = [m for m in mods if m["name"] not in have]
    for m in adds:
        nm = m["name"]
        out_at = next(i for i in range(len(out) - 1, -1, -1) if out[i][0] == 0x002B) + 1 if any(r[0] == 0x002B for r in out) else len(out) - 1
        seg = [[0x0019, nm.encode(enc)], [0x0047, nm.encode("utf-16-le")], [0x001A, nm.encode(enc)], [0x0032, nm.encode("utf-16-le")],
               [0x001C, b""], [0x0048, b""], [0x0031, struct.pack("<I", 0)], [0x001E, struct.pack("<I", 0)], [0x002C, struct.pack("<H", 0xFFFF)],
               [0x0021, b""], [0x002B, b""]]
        out[out_at:out_at] = seg
        streams[vba + nm] = compress((f'Attribute VB_Name = "{nm}"\r\n' + m["code"].replace("\r\n", "\n").replace("\n", "\r\n")).encode(enc, "replace"))
    n = sum(1 for r in out if r[0] == 0x0019)
    for r in out:
        if r[0] == 0x000F:
            r[1] = struct.pack("<H", n)
    streams[vba + "dir"] = compress(_pack(out))
    streams[vba + "_VBA_PROJECT"] = bytes([0xCC, 0x61, 0xFF, 0xFF, 0x00, 0x00, 0x00])  # 판 0xFFFF - 엑셀이 소스에서 다시 컴파일
    if base + "PROJECT" in streams:  # PROJECT 스트림 - 모듈 줄(Module=) 더하기·빼기
        lines = streams[base + "PROJECT"].decode(enc, "replace").split("\r\n")
        lines = [ln for ln in lines if not (ln.startswith("Module=") and ln.split("=", 1)[1] in drop)]
        at = max([i for i, ln in enumerate(lines) if ln.startswith(("Module=", "Document=", "Class=", "Package=", "BaseClass="))] or [0]) + 1
        for m in adds:
            lines.insert(at, f"Module={m['name']}")
            at += 1
        streams[base + "PROJECT"] = "\r\n".join(lines).encode(enc, "replace")
    return cfb_write(streams, cf.storages, cf.clsid)


def main():
    ap = argparse.ArgumentParser(description="엑셀 VBA 프로젝트 모듈 읽기")
    ap.add_argument("bin")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    mods = read_modules(open(a.bin, "rb").read())
    if a.json:
        print(json.dumps(mods, ensure_ascii=False, indent=1))
        return
    for m in mods:
        print(f"===== {m['name']} ({m['kind']})")
        print(m["code"])


if __name__ == "__main__":
    main()
