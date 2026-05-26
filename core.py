import os
import re
import json
import sys
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

FPS = 180
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    _EXPORT_FOLDER = os.path.dirname(sys.executable)
else:
    _EXPORT_FOLDER = os.path.join(os.path.dirname(SCRIPT_DIR), "EXPORTED TEXT FILES HERE")
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def set_export_path(path: str):
    global _EXPORT_FOLDER
    _EXPORT_FOLDER = path

def get_export_path() -> str:
    return _EXPORT_FOLDER

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".webp"}

_OCR_SUPPORTED = True
try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    from PIL import Image
except Exception:
    _OCR_SUPPORTED = False


@dataclass
class SplitPoint:
    round: int
    frames: int
    time: float


@dataclass
class ComparisonRow:
    round: int
    a_frames: int
    a_time: float
    cum_a: float
    b_frames: int
    b_time: float
    cum_b: float
    df: int
    dt: float
    win: str
    mom: int


@dataclass
class Summary:
    a_wins: int = 0
    b_wins: int = 0
    ties: int = 0
    ta: int = 0
    tb: int = 0
    ttA: float = 0.0
    ttB: float = 0.0
    total_rounds: int = 0


def set_tesseract_path(path: str) -> None:
    global TESSERACT_PATH, _OCR_SUPPORTED
    TESSERACT_PATH = path
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = path
        from PIL import Image
        _OCR_SUPPORTED = True
    except Exception:
        _OCR_SUPPORTED = False


def ocr_supported() -> bool:
    return _OCR_SUPPORTED


# =========================
# MIN TIME SPLITS
# =========================
MIN_TIME_SPLITS: List[SplitPoint] = [
    SplitPoint(1,1052,5.844),SplitPoint(2,1141,6.339),
    SplitPoint(3,1004,5.578),SplitPoint(4,1040,5.777),
    SplitPoint(5,991,5.506),SplitPoint(6,1123,6.239),
    SplitPoint(7,1610,8.944),SplitPoint(8,1734,9.634),
    SplitPoint(9,1138,6.322),SplitPoint(10,2881,16.005),
    SplitPoint(11,1151,6.395),SplitPoint(12,1045,5.805),
    SplitPoint(13,1934,10.745),SplitPoint(14,1599,8.883),
    SplitPoint(15,1501,8.339),SplitPoint(16,963,5.350),
    SplitPoint(17,301,1.672),SplitPoint(18,1610,8.945),
    SplitPoint(19,947,5.261),SplitPoint(20,316,1.755),
    SplitPoint(21,1089,6.050),SplitPoint(22,481,2.673),
    SplitPoint(23,411,2.283),SplitPoint(24,541,3.006),
    SplitPoint(25,1270,7.055),SplitPoint(26,872,4.845),
    SplitPoint(27,2057,11.427),SplitPoint(28,301,1.673),
    SplitPoint(29,916,5.088),SplitPoint(30,786,4.367),
    SplitPoint(31,956,5.311),SplitPoint(32,1679,9.328),
    SplitPoint(33,1522,8.456),SplitPoint(34,2161,12.005),
    SplitPoint(35,2027,11.261),SplitPoint(36,1261,7.006),
    SplitPoint(37,2612,14.511),SplitPoint(38,1745,9.694),
    SplitPoint(39,2277,12.650),SplitPoint(40,32,0.178),
]

MEDIUM_TIME_SPLITS: List[SplitPoint] = [
    SplitPoint(1,1052,5.844),SplitPoint(2,1141,6.338),
    SplitPoint(3,1004,5.577),SplitPoint(4,1040,5.777),
    SplitPoint(5,991,5.505),SplitPoint(6,1123,6.238),
    SplitPoint(7,1610,8.944),SplitPoint(8,1734,9.633),
    SplitPoint(9,1138,6.322),SplitPoint(10,2881,16.005),
    SplitPoint(11,1151,6.394),SplitPoint(12,1045,5.805),
    SplitPoint(13,1934,10.744),SplitPoint(14,1599,8.883),
    SplitPoint(15,1501,8.338),SplitPoint(16,963,5.350),
    SplitPoint(17,301,1.672),SplitPoint(18,1610,8.944),
    SplitPoint(19,947,5.261),SplitPoint(20,316,1.755),
    SplitPoint(21,1089,6.050),SplitPoint(22,481,2.672),
    SplitPoint(23,411,2.283),SplitPoint(24,541,3.005),
    SplitPoint(25,1270,7.055),SplitPoint(26,872,4.844),
    SplitPoint(27,2057,11.427),SplitPoint(28,301,1.672),
    SplitPoint(29,916,5.088),SplitPoint(30,786,4.366),
    SplitPoint(31,956,5.311),SplitPoint(32,1679,9.327),
    SplitPoint(33,1522,8.455),SplitPoint(34,2161,12.005),
    SplitPoint(35,2027,11.261),SplitPoint(36,1261,7.005),
    SplitPoint(37,2612,14.511),SplitPoint(38,1745,9.694),
    SplitPoint(39,2277,12.650),SplitPoint(40,32,0.177),
    SplitPoint(41,2774,15.411),SplitPoint(42,697,3.872),
    SplitPoint(43,557,3.094),SplitPoint(44,1421,7.894),
    SplitPoint(45,3187,17.705),SplitPoint(46,421,2.338),
    SplitPoint(47,1480,8.222),SplitPoint(48,3345,18.583),
    SplitPoint(49,3001,16.672),SplitPoint(50,1711,9.505),
    SplitPoint(51,1450,8.055),SplitPoint(52,1235,6.861),
    SplitPoint(53,2101,11.672),SplitPoint(54,1166,6.477),
    SplitPoint(55,1759,9.772),SplitPoint(56,943,5.238),
    SplitPoint(57,1575,8.750),SplitPoint(58,2641,14.672),
    SplitPoint(59,1571,8.727),SplitPoint(60,32,0.178),
]

HARD_TIME_SPLITS: List[SplitPoint] = [
    SplitPoint(3,1004,5.577),SplitPoint(4,1040,5.777),
    SplitPoint(5,991,5.505),SplitPoint(6,1123,6.238),
    SplitPoint(7,1610,8.944),SplitPoint(8,1734,9.633),
    SplitPoint(9,1138,6.322),SplitPoint(10,2881,16.005),
    SplitPoint(11,1151,6.394),SplitPoint(12,1045,5.805),
    SplitPoint(13,1934,10.744),SplitPoint(14,1599,8.883),
    SplitPoint(15,1501,8.338),SplitPoint(16,963,5.350),
    SplitPoint(17,301,1.672),SplitPoint(18,1610,8.944),
    SplitPoint(19,947,5.261),SplitPoint(20,316,1.755),
    SplitPoint(21,1089,6.050),SplitPoint(22,481,2.672),
    SplitPoint(23,411,2.283),SplitPoint(24,541,3.005),
    SplitPoint(25,1270,7.055),SplitPoint(26,872,4.844),
    SplitPoint(27,2057,11.427),SplitPoint(28,301,1.672),
    SplitPoint(29,916,5.088),SplitPoint(30,786,4.366),
    SplitPoint(31,956,5.311),SplitPoint(32,1679,9.327),
    SplitPoint(33,1522,8.455),SplitPoint(34,2161,12.005),
    SplitPoint(35,2027,11.261),SplitPoint(36,1261,7.005),
    SplitPoint(37,2612,14.511),SplitPoint(38,1745,9.694),
    SplitPoint(39,2277,12.650),SplitPoint(40,32,0.177),
    SplitPoint(41,2774,15.411),SplitPoint(42,697,3.872),
    SplitPoint(43,557,3.094),SplitPoint(44,1421,7.894),
    SplitPoint(45,3187,17.705),SplitPoint(46,421,2.338),
    SplitPoint(47,1480,8.222),SplitPoint(48,3345,18.583),
    SplitPoint(49,3001,16.672),SplitPoint(50,1711,9.505),
    SplitPoint(51,1450,8.055),SplitPoint(52,1235,6.861),
    SplitPoint(53,2101,11.672),SplitPoint(54,1166,6.477),
    SplitPoint(55,1759,9.772),SplitPoint(56,943,5.238),
    SplitPoint(57,1575,8.750),SplitPoint(58,2641,14.672),
    SplitPoint(59,1571,8.727),SplitPoint(60,32,0.178),
    SplitPoint(61,1201,6.672),SplitPoint(62,2899,16.105),
    SplitPoint(63,2537,14.094),SplitPoint(64,574,3.188),
    SplitPoint(65,3723,20.683),SplitPoint(66,1367,7.594),
    SplitPoint(67,1589,8.827),SplitPoint(68,480,2.666),
    SplitPoint(69,2529,14.050),SplitPoint(70,2471,13.727),
    SplitPoint(71,994,5.522),SplitPoint(72,1303,7.238),
    SplitPoint(73,1603,8.905),SplitPoint(74,4945,27.472),
    SplitPoint(75,1360,7.555),SplitPoint(76,108,0.600),
    SplitPoint(77,3538,19.655),SplitPoint(78,5401,30.005),
    SplitPoint(79,3601,20.005),SplitPoint(80,65,0.361),
]

IMPOPPABLE_TIME_SPLITS: List[SplitPoint] = [
    SplitPoint(6,1123,6.238),
    SplitPoint(7,1610,8.944),SplitPoint(8,1734,9.633),
    SplitPoint(9,1138,6.322),SplitPoint(10,2881,16.005),
    SplitPoint(11,1151,6.394),SplitPoint(12,1045,5.805),
    SplitPoint(13,1934,10.744),SplitPoint(14,1599,8.883),
    SplitPoint(15,1501,8.338),SplitPoint(16,963,5.350),
    SplitPoint(17,301,1.672),SplitPoint(18,1610,8.944),
    SplitPoint(19,947,5.261),SplitPoint(20,316,1.755),
    SplitPoint(21,1089,6.050),SplitPoint(22,481,2.672),
    SplitPoint(23,411,2.283),SplitPoint(24,541,3.005),
    SplitPoint(25,1270,7.055),SplitPoint(26,872,4.844),
    SplitPoint(27,2057,11.427),SplitPoint(28,301,1.672),
    SplitPoint(29,916,5.088),SplitPoint(30,786,4.366),
    SplitPoint(31,956,5.311),SplitPoint(32,1679,9.327),
    SplitPoint(33,1522,8.455),SplitPoint(34,2161,12.005),
    SplitPoint(35,2027,11.261),SplitPoint(36,1261,7.005),
    SplitPoint(37,2612,14.511),SplitPoint(38,1745,9.694),
    SplitPoint(39,2277,12.650),SplitPoint(40,32,0.177),
    SplitPoint(41,2774,15.411),SplitPoint(42,697,3.872),
    SplitPoint(43,557,3.094),SplitPoint(44,1421,7.894),
    SplitPoint(45,3187,17.705),SplitPoint(46,421,2.338),
    SplitPoint(47,1480,8.222),SplitPoint(48,3345,18.583),
    SplitPoint(49,3001,16.672),SplitPoint(50,1711,9.505),
    SplitPoint(51,1450,8.055),SplitPoint(52,1235,6.861),
    SplitPoint(53,2101,11.672),SplitPoint(54,1166,6.477),
    SplitPoint(55,1759,9.772),SplitPoint(56,943,5.238),
    SplitPoint(57,1575,8.750),SplitPoint(58,2641,14.672),
    SplitPoint(59,1571,8.727),SplitPoint(60,32,0.178),
    SplitPoint(61,1201,6.672),SplitPoint(62,2899,16.105),
    SplitPoint(63,2537,14.094),SplitPoint(64,574,3.188),
    SplitPoint(65,3724,20.688),SplitPoint(66,1367,7.594),
    SplitPoint(67,1589,8.827),SplitPoint(68,481,2.672),
    SplitPoint(69,2529,14.050),SplitPoint(70,2471,13.727),
    SplitPoint(71,994,5.522),SplitPoint(72,1303,7.238),
    SplitPoint(73,1603,8.905),SplitPoint(74,4945,27.472),
    SplitPoint(75,1360,7.555),SplitPoint(76,108,0.600),
    SplitPoint(77,3538,19.655),SplitPoint(78,5401,30.005),
    SplitPoint(79,3601,20.005),SplitPoint(80,66,0.366),
    SplitPoint(81,1592,8.844),SplitPoint(82,2144,11.911),
    SplitPoint(83,3613,20.072),SplitPoint(84,1503,8.350),
    SplitPoint(85,612,3.400),SplitPoint(86,1255,6.972),
    SplitPoint(87,612,3.400),SplitPoint(88,886,4.922),
    SplitPoint(89,1248,6.933),SplitPoint(90,716,3.977),
    SplitPoint(91,1801,10.005),SplitPoint(92,2102,11.677),
    SplitPoint(93,1204,6.688),SplitPoint(94,903,5.016),
    SplitPoint(95,3051,16.950),SplitPoint(96,1943,10.794),
    SplitPoint(97,332,1.844),SplitPoint(98,1804,10.022),
    SplitPoint(99,722,4.011),SplitPoint(100,26,0.144),
]

# =========================
# UTILITIES
# =========================
def parse_time(t: str) -> float:
    try:
        parts = t.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(t)
    except Exception:
        return 0.0

def fmt(sec: float) -> str:
    m = int(sec // 60)
    s = sec % 60
    return f"{m:02}:{s:06.3f}"

def _extract_numbers(line: str) -> List[float]:
    return [float(m) for m in re.findall(r"(\d+(?:\.\d+)?)", line)]

def _frames_time(v: float, as_frames: bool) -> Tuple[int, float]:
    return (int(v), v / FPS) if as_frames else (int(v * FPS), v)

# =========================
# OCR
# =========================
def ocr_image(path: str) -> Optional[str]:
    if not _OCR_SUPPORTED:
        return None
    try:
        import pytesseract
        from PIL import Image, ImageOps

        img = Image.open(path).convert("L")
        variants = [("gray", img)]
        w, h = img.size
        if w < h * 0.5:
            r, g, b = Image.open(path).convert("RGB").split()
            max_lum = max(r.convert("L").getextrema()[1],
                          g.convert("L").getextrema()[1],
                          b.convert("L").getextrema()[1])
            if max_lum > 200:
                variants.append(("inv", ImageOps.invert(img)))

        best_text, best_score = "", -1
        for name, proc in variants:
            for config in [
                "--psm 4 -c tessedit_char_whitelist=0123456789:.",
                "--psm 6 -c tessedit_char_whitelist=0123456789:.",
            ]:
                try:
                    text = pytesseract.image_to_string(proc, config=config)
                except Exception:
                    continue
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                ts = sum(1 for l in lines if re.match(r"^\d{1,2}:\d{2}\.\d{3}$", l))
                if ts > 0:
                    score = ts * 100 + len(lines)
                    if score > best_score:
                        best_score, best_text = score, text

            for config in ["--psm 6", ""]:
                try:
                    text = pytesseract.image_to_string(proc, config=config)
                except Exception:
                    continue
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                ts = sum(1 for l in lines if re.match(r"^\d{1,2}:\d{2}\.\d{3}$", l))
                vb = sum(1 for l in lines if "Round" in l and "Frame" in l)
                score = ts * 100 + vb * 20 + len(lines)
                if score > best_score:
                    best_score, best_text = score, text

        lines = []
        for l in best_text.splitlines():
            l = l.replace(",", ".").replace("|", "1").replace("O", "0").replace("o", "0")
            l = l.replace("l", "1").replace("I", "1").replace("@", "0")
            l = l.replace("$", "5").replace("&", "8")
            s = l.strip()
            if not s or s.startswith(("#", "//")):
                continue
            if re.match(r"^(setting|steam|Steam)", s, re.I):
                continue
            if "SteamID" in s or "minidump" in s.lower():
                continue
            if re.match(r"^\d{17,}$", s):
                continue
            lines.append(s)
        return "\n".join(lines)
    except Exception:
        return None

# =========================
# PARSING
# =========================
def _read_raw_lines(path: str) -> List[str]:
    raw: List[str] = []
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext in IMAGE_EXTS:
            ocr_text = ocr_image(path)
            if ocr_text:
                for line in ocr_text.splitlines():
                    s = line.strip()
                    if s and not s.startswith(("#", "//")):
                        raw.append(s)
            if not raw:
                return []
        else:
            with open(path, "r", encoding="utf-8-sig") as f:
                for line in f:
                    s = line.strip()
                    if s and not s.startswith(("#", "//")):
                        raw.append(s)
    except Exception:
        return []
    return raw

def _parse_raw_lines(raw: List[str]) -> List[SplitPoint]:
    def _convert_cumulative(out: List[SplitPoint]) -> List[SplitPoint]:
        if len(out) < 2:
            return out
        times = [d.time for d in out]
        if all(times[i] < times[i+1] for i in range(len(times)-1)) and times[-1] > 120:
            prev = 0.0
            result: List[SplitPoint] = []
            for d in out:
                cum = d.time
                split_t = cum - prev
                prev = cum
                result.append(SplitPoint(
                    round=d.round,
                    frames=max(1, int(round(split_t * FPS))),
                    time=split_t,
                ))
            return result
        return out

    def numbered(out: List[SplitPoint]) -> List[SplitPoint]:
        for i, d in enumerate(out):
            if d.round == 0:
                d.round = i + 1
        return out

    # Strategy 0: standalone timestamps
    ts_line_pat = re.compile(r"^\d{1,2}:\d{2}\.\d{3}$")
    rows: List[SplitPoint] = []
    for line in raw:
        if ts_line_pat.match(line):
            tm = parse_time(line)
            rows.append(SplitPoint(round=len(rows) + 1, frames=int(tm * FPS), time=tm))
        else:
            rows.clear()
            break
    if rows:
        return numbered(_convert_cumulative(rows))

    # Strategy 1: delimited (round frames time)
    time_col_pat = re.compile(r"^\d{1,2}:\d{2}\.\d{3}$")
    rows = []
    for line in raw:
        parts = line.replace(",", " ").replace("|", " ").replace("\t", " ").split()
        if not parts:
            rows.clear()
            break
        try:
            rnd = int(parts[0])
            fr = int(parts[1])
            if time_col_pat.match(parts[2]):
                tm = parse_time(parts[2])
            else:
                tm = float(parts[2])
            rows.append(SplitPoint(round=rnd, frames=fr, time=tm))
        except (ValueError, IndexError):
            rows.clear()
            break
    if rows:
        return numbered(rows)

    # Strategy 2: verbose "Round X took Y Frames or MM:SS.mmm"
    pat_verbose = re.compile(
        r"Round\s+(\d+)\s+took\s+(\d+)\s+Frame[s]?\s+or\s+(\d+:\d+\.\d+)", re.IGNORECASE)
    rows = []
    for line in raw:
        m = pat_verbose.search(line)
        if m:
            rows.append(SplitPoint(
                round=int(m.group(1)),
                frames=int(m.group(2)),
                time=parse_time(m.group(3)),
            ))
        else:
            rows.clear()
            break
    if rows:
        return numbered(rows)

    # Strategy 3: single column
    nums: List[float] = []
    for line in raw:
        n = _extract_numbers(line)
        if len(n) == 1:
            nums.append(n[0])
        else:
            nums.clear()
            break
    if nums:
        avg = sum(nums) / len(nums)
        ratio_int = sum(1 for v in nums if abs(v - round(v)) < 1e-6) / len(nums)
        if ratio_int > 0.5 and avg > 50:
            as_frames = True
        elif ratio_int < 0.5 and avg < 500:
            as_frames = False
        else:
            as_frames = avg > 50
        rows = []
        for i, v in enumerate(nums):
            fr, tm = _frames_time(v, as_frames)
            rows.append(SplitPoint(round=i + 1, frames=fr, time=tm))
        return numbered(_convert_cumulative(rows))

    # Strategy 4: two columns
    pairs: List[Tuple[float, float]] = []
    for line in raw:
        n = _extract_numbers(line)
        if len(n) == 2:
            pairs.append((n[0], n[1]))
        else:
            pairs.clear()
            break
    if pairs:
        c0_vals = [p[0] for p in pairs]
        c1_vals = [p[1] for p in pairs]
        c0_avg = sum(c0_vals) / len(pairs)
        c1_avg = sum(c1_vals) / len(pairs)

        def is_round_col(vals: List[float]) -> bool:
            return all(1 <= round(v) <= len(pairs) and abs(v - round(v)) < 1e-6 for v in vals)

        def kind(v: float, vals: List[float], is_rnd: bool) -> str:
            if is_rnd:
                return "round"
            all_non_int = all(abs(vv - round(vv)) > 1e-6 for vv in vals)
            if v > 5000:
                return "frames_total"
            if 50 <= v <= 5000:
                return "time" if all_non_int else "frames"
            if v < 500:
                return "time"
            return "unknown"

        k0 = kind(c0_avg, c0_vals, is_round_col(c0_vals))
        k1 = kind(c1_avg, c1_vals, is_round_col(c1_vals))
        fmap = {"frames", "frames_total"}
        tmap = {"time"}

        if k0 == "round" and k1 in fmap:
            rows = [SplitPoint(round=int(a), frames=int(b), time=b / FPS) for a, b in pairs]
        elif k0 == "round" and k1 in tmap:
            rows = [SplitPoint(round=int(a), frames=int(b * FPS), time=b) for a, b in pairs]
        elif k1 == "round" and k0 in fmap:
            rows = [SplitPoint(round=int(b), frames=int(a), time=a / FPS) for a, b in pairs]
        elif k1 == "round" and k0 in tmap:
            rows = [SplitPoint(round=int(b), frames=int(a * FPS), time=a) for a, b in pairs]
        elif k0 in fmap and k1 in tmap:
            rows = [SplitPoint(round=i+1, frames=int(a), time=b) for i, (a,b) in enumerate(pairs)]
        elif k0 in tmap and k1 in fmap:
            rows = [SplitPoint(round=i+1, frames=int(b), time=a) for i, (a,b) in enumerate(pairs)]
        elif k0 in fmap and k1 in fmap:
            rows = [SplitPoint(round=i+1, frames=int(a), time=b / FPS) if a > b and not (k0 == "frames_total") else SplitPoint(round=i+1, frames=int(b), time=a / FPS) for i, (a,b) in enumerate(pairs)]
        elif k0 in tmap and k1 in tmap:
            rows = [SplitPoint(round=i+1, frames=int(max(a,b)*FPS), time=max(a,b)) for i, (a,b) in enumerate(pairs)]
        else:
            rows = [SplitPoint(round=i+1, frames=int(a), time=b) for i, (a,b) in enumerate(pairs)]
        return numbered(_convert_cumulative(rows))

    # Strategy 5: regex scatter-shot
    ts_pat = re.compile(r"\d+:\d+:\d+(?:\.\d+)?")
    out: List[SplitPoint] = []
    for line in raw:
        cleaned = ts_pat.sub("", line).strip()
        nums = _extract_numbers(cleaned)
        nums = [x for x in nums if x > 0]
        if not nums:
            continue
        rn = len(out) + 1
        if len(nums) >= 3:
            out.append(SplitPoint(round=int(nums[0]), frames=int(nums[1]), time=nums[2]))
        elif len(nums) == 2:
            a, b = nums
            a_is_round = a == int(a) and a <= 200
            b_is_round = b == int(b) and b <= 200
            if a_is_round and b > 50:
                out.append(SplitPoint(round=int(a), frames=int(b), time=b / FPS))
            elif a_is_round and not b_is_round:
                out.append(SplitPoint(round=int(a), frames=int(b * FPS), time=b))
            elif not a_is_round and b_is_round:
                out.append(SplitPoint(round=int(b), frames=int(a * FPS), time=a))
            elif 50 <= a <= 5000 and not (b > 50 and b < 500):
                out.append(SplitPoint(round=rn, frames=int(a), time=b))
            else:
                out.append(SplitPoint(round=rn, frames=int(a), time=b))
        else:
            v = nums[0]
            if v > 50:
                out.append(SplitPoint(round=rn, frames=int(v), time=v / FPS))
            else:
                out.append(SplitPoint(round=rn, frames=int(v * FPS), time=v))
    if out:
        return numbered(out)

    return []

def load_splits(path: str) -> List[SplitPoint]:
    raw = _read_raw_lines(path)
    return _parse_raw_lines(raw)

def load_splits_text(text: str) -> List[SplitPoint]:
    raw = [s.strip() for s in text.splitlines()
           if s.strip() and not s.strip().startswith(("#", "//"))]
    return _parse_raw_lines(raw)

# =========================
# ANALYSIS
# =========================
def analyze(A: List[SplitPoint], B: List[SplitPoint]) -> Tuple[List[ComparisonRow], Summary]:
    rows: List[ComparisonRow] = []
    mom = 0
    a_w = b_w = ties = 0
    ta = tb = 0
    ttA = ttB = 0.0
    n = min(len(A), len(B))

    for i in range(n):
        a = A[i]
        b = B[i]
        df = b.frames - a.frames
        dt = b.time - a.time
        mom += df
        ta += a.frames
        tb += b.frames
        ttA += a.time
        ttB += b.time

        if df > 0:
            a_w += 1
            win = "A"
        elif df < 0:
            b_w += 1
            win = "B"
        else:
            ties += 1
            win = "T"

        rows.append(ComparisonRow(
            round=a.round,
            a_frames=a.frames,
            a_time=a.time,
            cum_a=ttA,
            b_frames=b.frames,
            b_time=b.time,
            cum_b=ttB,
            df=df,
            dt=dt,
            win=win,
            mom=mom,
        ))

    return rows, Summary(
        a_wins=a_w, b_wins=b_w, ties=ties,
        ta=ta, tb=tb, ttA=ttA, ttB=ttB,
        total_rounds=n,
    )

# =========================
# EXPORT
# =========================
def build_export_text(rows: List[ComparisonRow], summary: Summary, nameA: str, nameB: str) -> str:
    lines = []
    lines.append("SPLIT ANALYSIS REPORT")
    lines.append(f"{nameA} vs {nameB}")
    lines.append("=" * 100)
    lines.append("")
    h = f"{'RND':<5}{'A(fr)':<8}{'A(time)':<12}{'B(fr)':<8}{'B(time)':<12}{'DF':<8}{'DT':<10}{'WIN':<6}{'MOM'}"
    lines.append(h)
    lines.append("-" * 100)
    for r in rows:
        a_t = fmt(r.a_time)
        b_t = fmt(r.b_time)
        lines.append(
            f"{r.round:<5}{r.a_frames:<8}{a_t:<12}"
            f"{r.b_frames:<8}{b_t:<12}"
            f"{r.df:+<8}{r.dt:+.3f}   {r.win:<6}{r.mom:+}"
        )
    lines.append("")
    lines.append("=" * 100)
    lines.append("SUMMARY")
    lines.append("=" * 100)
    lines.append(f"Total Rounds: {summary.total_rounds}")
    lines.append(f"A wins: {summary.a_wins}")
    lines.append(f"B wins: {summary.b_wins}")
    lines.append(f"Ties: {summary.ties}")
    lines.append("")
    lines.append(f"A total frames: {summary.ta}  time: {fmt(summary.ttA)}")
    lines.append(f"B total frames: {summary.tb}  time: {fmt(summary.ttB)}")
    lines.append("")
    if summary.ta < summary.tb:
        lines.append("A wins (frames)")
    elif summary.tb < summary.ta:
        lines.append("B wins (frames)")
    else:
        lines.append("Tie (frames)")
    if summary.ttA < summary.ttB:
        lines.append("A wins (time)")
    elif summary.ttB < summary.ttA:
        lines.append("B wins (time)")
    else:
        lines.append("Tie (time)")
    return "\n".join(lines)

def export_report(text: str) -> str:
    os.makedirs(_EXPORT_FOLDER, exist_ok=True)
    path = os.path.join(_EXPORT_FOLDER, f"split_report_{int(time.time())}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path
