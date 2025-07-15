import vapoursynth as vs
core = vs.core

# --- Input/Output Handling ---
if "video_in" in globals():
    # Real-time processing (e.g., via mpv)
    clip = video_in
    vfps = container_fps * 1000
    dfps = display_fps * 1000
    clip = core.std.AssumeFPS(clip, fpsnum=int(vfps), fpsden=1000)
else:
    # Run with vspipe (for standalone testing or batch processing)
    # Ensure you have ffms2 plugin installed for this
    clip = core.ffms2.Source(source=in_filename)
    vfps = container_fps * 1000
    dfps = display_fps * 1000

# --- Format Conversion for Denoising ---
# BM3DCUDA requires 32-bit float format.
# Convert to YUV444PS for CBM3D if chroma denoising is desired,
# otherwise YUV420PS is fine, but 444PS is generally more robust for BM3D.
# We'll stick to YUV420P8 for the final output as per original script.
# The internal processing for BM3DCUDA will be float.
denoise_clip = clip.resize.Bicubic(format=vs.YUV420PS) # Intermediate float format for denoising

# --- BM3DCUDA Denoising ---
# Parameters for BM3DCUDA.BM3D
# sigma: Denoising strength. Adjust as needed. Higher values mean more denoising.
# block_step, bm_range, radius, ps_num, ps_range: Common BM3D parameters.
# chroma=True: Enables CBM3D for chroma channels. Requires YUV444PS input.
# device_id: If you have multiple GPUs, specify which one (0 is typically the first).
# fast=True: Multi-threaded copy, generally faster.
print("[vapoursynth] Applying BM3DCUDA_RTC denoising...")
denoise_clip = core.bm3dcuda_rtc.BM3D(
    denoise_clip,
    sigma=[3.0, 3.0, 3.0], # Sigma for Y, U, V planes. Adjust as needed.
    block_step=[8, 8, 8],
    bm_range=[9, 9, 9],
    radius=0, # Spatial denoising. Use >0 for temporal denoising with BM3Dv2.
    ps_num=[2, 2, 2],
    ps_range=[4, 4, 4],
    chroma=False, # Set to True if using YUV444PS input for chroma denoising
    device_id=0,
    fast=True,
    extractor_exp=0 # Set to a positive integer (e.g., 3) for deterministic output, default 0 for non-deterministic.
)

# Convert back to YUV420P8 for MVTools and final output.
# You might want to experiment with different dither methods here based on output quality.
clip = denoise_clip.resize.Bicubic(format=vs.YUV420P8)

# --- Motion Interpolation (MVTools) ---
# Calculate megapixels (resolution) from the processed clip
mpix = clip.width * clip.height / 1000000

# Set thresholds
ignore_threshold = 1
scene_change_percentage = 99

# Skip interpolation for >FHD content due to performance constraints
if mpix <= 2.1:
    analParams = {
        'overlap': 0,
        'search': 3,
        'truemotion': True,
    }
    blockParams = {
        'thscd1': ignore_threshold,
        'thscd2': int(scene_change_percentage * 255 / 100),
        'mode': 1,
    }

    # Reduce motion interpolation quality for media exceeding HD
    if mpix > 0.9:
        analParams['search'] = 0
        blockParams['mode'] = 0
        quality = 'Low'
    else:
        quality = 'High'

    print(f"\n[vapoursynth] {quality} quality motionflow interpolation: reflowing from {vfps/1000} fps to {dfps/1000} fps.")

    # Super: Prepares the clip for motion analysis
    super = core.mv.Super(clip, pel=4, sharp=2, rfilter=4)
    # Analyse: Calculates forward and backward motion vectors
    mvfw = core.mv.Analyse(super, blksize=32, isb=False, search=analParams['search'], dct=5)
    mvbw = core.mv.Analyse(super, blksize=32, isb=True, search=analParams['search'], dct=5)
    # FlowFPS: Performs the actual frame interpolation
    clip = core.mv.FlowFPS(clip, super, mvbw, mvfw, num=int(dfps), den=1000, mask=1)

# --- Set Output ---
clip.set_output()
