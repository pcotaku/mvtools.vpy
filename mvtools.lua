import vapoursynth as vs
core = vs.core
clip = video_in.resize.Bicubic(format=vs.YUV420P8)
vden = 1000
vfps = container_fps*vden
dfps = display_fps*vden
if not (clip.width > 3000 or clip.height > 2000 or vfps > dfps):
    vfps_num = int(container_fps * 1e8)
    vfps_den = int(1e8)
    dfps_num = int(dfps * 1e4)
    dfps_den = int(1e4)
    clip = core.std.AssumeFPS(clip, fpsnum=vfps, fpsden=vden)
    print("[mvtools.lua] Converting this video's frame rate from",vfps/vden,"fps to",dfps_num/dfps_den,"fps.")
    super = core.mv.Super(clip, pel=2, sharp=0, rfilter=2)
    mvfw = core.mv.Analyse(super, blksize=32, isb=False, search=3, dct=5)
    mvbw = core.mv.Analyse(super, blksize=32, isb=True,  search=3, dct=5)
    clip = core.mv.FlowFPS(clip, super, mvbw, mvfw, num=dfps, den=vden, mask=1)
clip.set_output()
