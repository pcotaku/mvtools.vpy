import vapoursynth as vs
core = vs.core

# --- Global VapourSynth Core Settings ---
# Reduce CPU threads if thermal throttling is an issue.
# This limits VapourSynth's CPU-based frame processing.
# Adjust 'N' based on your CPU cores and throttling behavior.
# Smaller N = less CPU heat, but slower processing if CPU is bottleneck.
# A value of 1 effectively makes it single-threaded for core ops.
core.num_threads = 16 # Example: Limit to 4 CPU threads (adjust as needed)

if "video_in" in globals():
    clip = video_in
    vfps = container_fps * 1000
    dfps = display_fps * 1000
    clip = core.std.AssumeFPS(clip, fpsnum=int(vfps), fpsden=1000)
else:
    clip = core.ffms2.Source(source=in_filename)
    vfps = container_fps * 1000
    dfps = display_fps * 1000

# --- Format Conversion for Denoising (GPU-Friendly) ---
# BM3DCUDA requires 32-bit float format.
denoise_clip = clip.resize.Bicubic(format=vs.YUV420PS) # Intermediate float format for denoising

# --- BM3DCUDA Denoising (GPU) ---
print("[vapoursynth] Applying BM3DCUDA_RTC denoising...")
denoise_clip = core.bm3dcuda_rtc.BM3D(
    denoise_clip,
    sigma=[3.0, 3.0, 3.0],
    block_step=[8, 8, 8],
    bm_range=[9, 9, 9],
    radius=0,
    ps_num=[2, 2, 2],
    ps_range=[4, 4, 4],
    chroma=False,
    device_id=0,
    fast=True,
    extractor_exp=0
)

# Convert back to YUV420P8 for MVTools and final output.
# You might consider using a GPU-accelerated resizer here if available (e.g., from vs-gpu if you install it)
clip = denoise_clip.resize.Bicubic(format=vs.YUV420P8)

# --- Motion Interpolation (MVTools - Largely CPU-bound) ---
# Calculate megapixels (resolution) from the processed clip
mpix = clip.width * clip.height / 1000000

ignore_threshold = 1
scene_change_percentage = 99

if mpix <= 2.1:
    analParams = {
        'overlap': 0,
        'search': 3, # Keep this value as is, or try '0' for less CPU if needed
        'truemotion': True,
    }
    blockParams = {
        'thscd1': ignore_threshold,
        'thscd2': int(scene_change_percentage * 255 / 100),
        'mode': 1,
    }

    if mpix > 0.9:
        analParams['search'] = 0 # Already optimized for >HD
        blockParams['mode'] = 0
        quality = 'Low'
    else:
        quality = 'High'

    print(f"\n[vapoursynth] {quality} quality motionflow interpolation: reflowing from {vfps/1000} fps to {dfps/1000} fps.")

    super = core.mv.Super(clip, pel=2, sharp=2, rfilter=4)
    # Consider reducing 'dct' here for less CPU, e.g., dct=0 for no DCT
    mvfw = core.mv.Analyse(super, blksize=32, isb=False, search=analParams['search'], dct=5) # Can change dct
    mvbw = core.mv.Analyse(super, blksize=32, isb=True, search=analParams['search'], dct=5) # Can change dct
    clip = core.mv.FlowFPS(clip, super, mvbw, mvfw, num=int(dfps), den=1000, mask=1)

clip.set_output()
