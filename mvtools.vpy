import vapoursynth as vs
core = vs.core

if "video_in" in globals():
    # Real-time processing
    clip = video_in
    vfps = container_fps * 1000
    dfps = display_fps * 1000
    clip = core.std.AssumeFPS(clip, fpsnum=int(vfps), fpsden=1000)
else:
    # Run with vspipe
    clip = core.ffms2.Source(source=in_filename)
    vfps = container_fps * 1000
    dfps = display_fps * 1000

# Resize to YUV420P8 format
clip = clip.resize.Bicubic(format=vs.YUV420P8)

# Calculate megapixels (resolution)
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

    print(f"[vapoursynth] {quality} quality motionflow interpolation: reflowing from {vfps/1000} fps to {dfps/1000} fps.")
    super = core.mv.Super(clip, pel=2, sharp=2, rfilter=4)
    mvfw = core.mv.Analyse(super, blksize=32, isb=False, search=analParams['search'], dct=5)
    mvbw = core.mv.Analyse(super, blksize=32, isb=True,  search=analParams['search'], dct=5)
    clip = core.mv.FlowFPS(clip, super, mvbw, mvfw, num=int(dfps), den=1000, mask=1)

clip.set_output()
