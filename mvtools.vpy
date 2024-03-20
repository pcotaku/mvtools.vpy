# vim: set ft=python:

# see the README at https://gist.github.com/phiresky/4bfcfbbd05b3c2ed8645
# source: https://github.com/mpv-player/mpv/issues/2149
# source: https://github.com/mpv-player/mpv/issues/566
# source: https://github.com/haasn/gentoo-conf/blob/nanodesu/home/nand/.mpv/filters/mvtools.vpy

import vapoursynth

core = vapoursynth.core
# ref: http://avisynth.org.ru/mvtools/mvtools2.html#functions
# default is 400, less means interpolation will only happen when it will work well
ignore_threshold=140
# if n% of blocks change more than threshold then don't interpolate at all (default is 51%)
scene_change_percentage=15

dst_fps = display_fps

if "video_in" in globals():
    # realtime
    clip = video_in
    # Needed because clip FPS is missing
    src_fps_num = int(container_fps * 1e8)
    src_fps_den = int(1e8)
    clip = core.std.AssumeFPS(clip, fpsnum = src_fps_num, fpsden = src_fps_den)
else:
    # run with vspipe
    clip = core.ffms2.Source(source=in_filename)
    dst_fps=float(dst_fps)

# resolution in megapixels. 1080p ≈ 2MP, 720p ≈ 1MP
mpix = clip.width * clip.height / 1000000

# Skip interpolation for >FHD content due to performance constraints
if not (mpix > 2.1):
    analParams = {
        'overlap': 0,
        'search': 3,
        'truemotion': True,
        'chroma': True,
        'blksize':16,
        'searchparam':2
    }
    blockParams = {
        'thscd1': ignore_threshold,
        'thscd2': int(scene_change_percentage*255/100),
        'mode': 1,
    }

    if mpix > 2.1:
        # set motion interpolation resolution quality to low when interpolating frames for videos exceeding FHD res.
        # see the description of these parameters in http://avisynth.org.ru/mvtools/mvtools2.html#functions
        analParams['search'] = 0
        blockParams['mode'] = 0
        quality = 'low'
    else:
        quality = 'high'


    dst_fps_num = int(dst_fps * 1e4)
    dst_fps_den = int(1e4)
    print("[vapoursynth] Reflowing from {} fps to {} fps (quality={})".format(clip.fps_num/clip.fps_den,dst_fps_num/dst_fps_den,quality))
    
    super = core.mv.Super(clip, pel=2, sharp=2, rfilter=4)
    mvfw = core.mv.Analyse(super, blksize=16, isb=False, search=3, dct=5)
    mvbw = core.mv.Analyse(super, blksize=16, isb=True,  search=3, dct=5)
    clip = core.mv.FlowFPS(clip, super, mvbw, mvfw, num=dst_fps_num, den=dst_fps_den, mask=1)

clip.set_output()
