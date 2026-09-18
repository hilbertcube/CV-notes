#!/usr/bin/env python3
"""Generate noise-model figures for Part 2, Chapter 1.

Outputs into images/part2/.  Deterministic (fixed seed) so reruns are stable.
Requires only numpy + Pillow.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(__file__), "..", "images", "part2")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
rng = np.random.default_rng(20260917)


def font(sz, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, sz)


def to_u8(a):
    return (np.clip(a, 0, 1) * 255).astype(np.uint8)


def base_scene(h=384, w=384):
    """Clean synthetic scene: gradient, flat patches, edges, fine texture."""
    y, x = np.mgrid[0:h, 0:w].astype(np.float64)
    img = 0.15 + 0.5 * (x / w)                      # smooth background ramp
    cy, cx, r = h * 0.33, w * 0.32, min(h, w) * 0.17
    img[(y - cy) ** 2 + (x - cx) ** 2 < r ** 2] = 0.88      # bright disk
    img[int(.62 * h):int(.86 * h), int(.10 * w):int(.40 * w)] = 0.12   # dark square
    img[int(.62 * h):int(.86 * h), int(.46 * w):int(.72 * w)] = 0.50   # mid square
    # fine concentric texture, to show how noise interacts with detail
    ty, tx = y - h * 0.30, x - w * 0.72
    ring = 0.5 + 0.28 * np.sin(np.sqrt(ty ** 2 + tx ** 2) * 0.55)
    m = (np.abs(ty) < h * 0.18) & (np.abs(tx) < w * 0.20)
    img[m] = ring[m]
    return np.clip(img, 0, 1)


def add_noise(img, kind):
    if kind == "Gaussian":
        return img + rng.normal(0, 0.09, img.shape)
    if kind == "Uniform":
        return img + rng.uniform(-0.16, 0.16, img.shape)
    if kind == "Salt & pepper":
        out, u = img.copy(), rng.random(img.shape)
        out[u < 0.03] = 0.0
        out[u > 0.97] = 1.0
        return out
    if kind == "Rayleigh":
        n = rng.rayleigh(0.07, img.shape)
        return img + n - n.mean()
    if kind == "Gamma (Erlang)":
        n = rng.gamma(2.0, 0.05, img.shape)
        return img + n - n.mean()
    if kind == "Exponential":
        n = rng.exponential(0.07, img.shape)
        return img + n - n.mean()
    if kind == "Poisson (shot)":
        lam = np.clip(img, 0, 1) * 40.0
        return rng.poisson(lam) / 40.0
    if kind == "Speckle (mult.)":
        return img * (1.0 + rng.normal(0, 0.22, img.shape))
    raise ValueError(kind)


def gallery():
    kinds = ["Clean", "Gaussian", "Uniform", "Salt & pepper", "Rayleigh",
             "Gamma (Erlang)", "Exponential", "Poisson (shot)", "Speckle (mult.)"]
    base, T, G, LBL, PAD = base_scene(), 384, 10, 30, 6
    cols = 3
    rows = (len(kinds) + cols - 1) // cols
    W = cols * T + (cols - 1) * G + 2 * PAD
    H = rows * (T + LBL) + (rows - 1) * G + 2 * PAD
    canvas = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(canvas)
    f = font(21, bold=True)
    for i, k in enumerate(kinds):
        arr = base if k == "Clean" else add_noise(base, k)
        r, c = divmod(i, cols)
        x0 = PAD + c * (T + G)
        y0 = PAD + r * (T + LBL + G)
        d.text((x0, y0 + 4), k, fill=0, font=f)
        canvas.paste(Image.fromarray(to_u8(arr)), (x0, y0 + LBL))
    p = os.path.join(OUT, "noise-gallery.png")
    canvas.save(p, optimize=True)
    return p


def stretch(a):
    """Normalise a frame to [0,1] for display (these frames are otherwise near-flat)."""
    lo, hi = np.percentile(a, 0.5), np.percentile(a, 99.5)
    return np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1)


def sensor_frames(h=384, w=384):
    """Synthesise the calibration frames of a real sensor."""
    y, x = np.mgrid[0:h, 0:w].astype(np.float64)
    # --- bias: constant electronic pedestal + read noise + column-wise FPN
    col_fpn = rng.normal(0, 0.0035, (1, w)).repeat(h, 0)
    bias = 0.060 + col_fpn + rng.normal(0, 0.0035, (h, w))
    # --- dark current: thermal signal, amplifier glow in one corner, hot pixels
    glow = 0.030 * np.exp(-(((x - w) ** 2 + y ** 2) / (0.20 * w * h)))
    dark = 0.022 + glow + rng.normal(0, 0.0015, (h, w))          # DSNU
    hot = rng.random((h, w)) < 0.0012
    dark[hot] += rng.uniform(0.25, 0.75, hot.sum())              # hot pixels
    # --- flat field: lens vignetting * pixel gain (PRNU) * dust motes
    r2 = ((x - w / 2) ** 2 + (y - h / 2) ** 2) / (w / 2) ** 2
    flat = np.cos(np.arctan(np.sqrt(r2) * 0.85)) ** 4            # cos^4 falloff
    flat *= 1.0 + rng.normal(0, 0.012, (h, w))                   # PRNU
    for _ in range(5):                                           # dust donuts
        cx, cy, rr = rng.uniform(.1, .9) * w, rng.uniform(.1, .9) * h, rng.uniform(14, 26)
        d2 = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        flat *= 1 - 0.20 * np.exp(-((d2 - rr * 0.55) ** 2) / (2 * (rr * 0.3) ** 2))
    return bias, dark, flat


def calibration():
    truth = base_scene()
    bias, dark, flat = sensor_frames()
    # observed light frame: scene attenuated by flat, plus dark and bias, plus shot+read noise
    ideal = truth * flat + dark + bias
    raw = rng.poisson(np.clip(ideal, 0, None) * 220) / 220 + rng.normal(0, 0.004, truth.shape)
    corrected = (raw - bias - dark) / np.clip(flat, 1e-6, None)

    panels = [("Raw light frame", raw, False),
              ("Master bias (offset + read)", bias, True),
              ("Master dark (+ hot pixels)", dark, True),
              ("Master flat (vignette+dust)", flat, True),
              ("Calibrated result", corrected, False),
              ("Ground truth", truth, False)]
    T, G, LBL, PAD, cols = 384, 10, 30, 6, 3
    rows = 2
    W = cols * T + (cols - 1) * G + 2 * PAD
    H = rows * (T + LBL) + (rows - 1) * G + 2 * PAD
    canvas = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(canvas)
    f = font(19, bold=True)
    for i, (name, arr, do_stretch) in enumerate(panels):
        a = stretch(arr) if do_stretch else np.clip(arr, 0, 1)
        r, c = divmod(i, cols)
        x0 = PAD + c * (T + G)
        y0 = PAD + r * (T + LBL + G)
        d.text((x0, y0 + 4), name, fill=0, font=f)
        canvas.paste(Image.fromarray(to_u8(a)), (x0, y0 + LBL))
    p = os.path.join(OUT, "sensor-calibration.png")
    canvas.save(p, optimize=True)
    return p


def photon_limit():
    """The scene emerging from pure photon shot noise as the photon budget grows.

    Every panel uses a perfect, noiseless detector: the only randomness is the
    arrival statistics of the light itself.
    """
    truth = base_scene()
    levels = [1, 4, 16, 64, 256, 1024]
    T, G, LBL, PAD, cols = 384, 10, 30, 6, 3
    rows = 2
    W = cols * T + (cols - 1) * G + 2 * PAD
    H = rows * (T + LBL) + (rows - 1) * G + 2 * PAD
    canvas = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(canvas)
    f = font(19, bold=True)
    for i, lam in enumerate(levels):
        counts = rng.poisson(truth * lam)
        a = counts / max(counts.max(), 1)
        snr = np.sqrt(lam * truth.max())          # SNR in the brightest region
        r, c = divmod(i, cols)
        x0 = PAD + c * (T + G)
        y0 = PAD + r * (T + LBL + G)
        fmt = f"{snr:.1f}" if snr < 10 else f"{snr:.0f}"
        d.text((x0, y0 + 4), f"{lam} ph/px   SNR {fmt}", fill=0, font=f)
        canvas.paste(Image.fromarray(to_u8(a)), (x0, y0 + LBL))
    p = os.path.join(OUT, "photon-limit.png")
    canvas.save(p, optimize=True)
    return p


if __name__ == "__main__":
    print("wrote", gallery())
    print("wrote", calibration())
    print("wrote", photon_limit())
