#!/usr/bin/env python3
"""Render the visual-decision replay and a standalone two-panel handoff demo.

Python 3.10+, Pillow, ffmpeg, ffprobe. All visual previews are native tool images.
All inputs are the public source recording, observations, and sanitized trace.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont

SIZE=(1600,900)
INK='#151515';BLUE='#176bce';MUTED='#626262';LINE='#ccd2da';WASH='#edf4fc'
VIDEO_BOX=(44,159,950,669)
EVIDENCE_BOX=(979,159,1555,483)
NODES={'main':(44,721,478,818),'subagent':(583,721,1017,818),'backend':(1122,721,1556,818)}
LABELS={'main':'Main agent','subagent':'Subagent','backend':'Backend'}
DEFAULTS={'main':'Retain the task goal and reports.','subagent':'Choose and inspect the physical action.','backend':'Execute and return fresh observations.'}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def font_path(bold=False):
    paths=[Path('/System/Library/Fonts/Supplemental')/('Arial Bold.ttf' if bold else 'Arial.ttf'),Path('/usr/share/fonts/truetype/dejavu')/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'),Path('C:/Windows/Fonts')/('arialbd.ttf' if bold else 'arial.ttf')]
    return next(str(p) for p in paths if p.exists())

def wrap(draw,text,font,width):
    rows=[];row=''
    for word in text.split():
        next_row=f'{row} {word}'.strip()
        if row and draw.textlength(next_row,font=font)>width:rows.append(row);row=word
        else:row=next_row
    if row:rows.append(row)
    return rows

def fit(image,box):
    width=box[2]-box[0];height=box[3]-box[1]
    ratio=min(width/image.width,height/image.height)
    result=image.resize((round(image.width*ratio),round(image.height*ratio)),Image.Resampling.LANCZOS)
    return result,(box[0]+(width-result.width)//2,box[1]+(height-result.height)//2)

def arrow(draw,points,color=BLUE):
    draw.line(points,fill=color,width=4,joint='curve')
    a,b=points[-2:];angle=math.atan2(b[1]-a[1],b[0]-a[0]);length=13
    draw.polygon([b,(b[0]-length*math.cos(angle-.5),b[1]-length*math.sin(angle-.5)),(b[0]-length*math.cos(angle+.5),b[1]-length*math.sin(angle+.5))],fill=color)

def connection(flow):
    a,b=[NODES[x] for x in flow]
    if abs(list(NODES).index(flow[0])-list(NODES).index(flow[1]))==1:
        right=a[0]<b[0]
        return [(a[2]+8 if right else a[0]-8,769),(b[0]-8 if right else b[2]+8,769)]
    # A separate upper path connects main and backend without passing through Subagent.
    return [((a[0]+a[2])/2,713),((a[0]+a[2])/2,690),((b[0]+b[2])/2,690),((b[0]+b[2])/2,713)]

def path_point(points,fraction):
    lengths=[math.dist(a,b) for a,b in zip(points,points[1:])]
    remaining=sum(lengths)*fraction
    for a,b,length in zip(points,points[1:],lengths):
        if remaining<=length:
            ratio=remaining/length if length else 0
            return a[0]+(b[0]-a[0])*ratio,a[1]+(b[1]-a[1])*ratio
        remaining-=length
    return points[-1]

def panel(replay,phase,index,count,fonts,visual):
    canvas=Image.new('RGB',SIZE,'white');draw=ImageDraw.Draw(canvas)
    draw.text((44,30),'RobotUse',font=fonts['brand'],fill=INK)
    draw.text((263,38),'Language → visual choice → robot action',font=fonts['title'],fill=INK)
    draw.text((44,93),replay['task'],font=fonts['subtitle'],fill=MUTED)
    draw.text((44,132),replay['motion_label'].upper(),font=fonts['small_bold'],fill=MUTED)
    draw.text((979,132),phase['visual']['label'].upper(),font=fonts['small_bold'],fill=BLUE)
    draw.rectangle(VIDEO_BOX,outline=INK,width=2);draw.rectangle(EVIDENCE_BOX,fill='#f8fafc',outline=INK,width=2)
    resized,pos=fit(visual,EVIDENCE_BOX);canvas.paste(resized,pos)
    draw.text((979,504),phase['visual']['kind'].upper(),font=fonts['small_bold'],fill=BLUE)
    y=537
    for line in wrap(draw,phase['detail'],fonts['caption_bold'],565)[:3]:
        draw.text((979,y),line,font=fonts['caption_bold'],fill=INK);y+=33
    y+=10
    for line in wrap(draw,phase['visual']['note'],fonts['small'],565)[:2]:
        draw.text((979,y),line,font=fonts['small'],fill=MUTED);y+=25
    for node,box in NODES.items():
        active=node==phase['active_node'];draw.rectangle(box,fill=WASH if active else 'white',outline=BLUE if active else LINE,width=3 if active else 2)
        draw.text((box[0]+17,box[1]+11),LABELS[node],font=fonts['node'],fill=BLUE if active else INK)
        for i,line in enumerate(wrap(draw,phase['messages'].get(node,replay['task'] if node=='main' else DEFAULTS[node]),fonts['node_small'],400)[:2]):
            draw.text((box[0]+17,box[1]+49+23*i),line,font=fonts['node_small'],fill=MUTED)
    arrow(draw,connection(phase['flow']))
    draw.text((44,841),f'{index+1:02d} / {count:02d} · {phase["title"]}',font=fonts['caption_bold'],fill=BLUE)
    draw.text((44,877),'Original tool images + recorded execution · Reading pauses added · Captions summarize logged decisions',font=fonts['footer'],fill=MUTED)
    return canvas

def read_exact(stream,length):
    chunks=[]
    while length:
        part=stream.read(length)
        if not part:return None
        chunks.append(part);length-=len(part)
    return b''.join(chunks)

def encoder(path,size,fps):
    return subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{size[0]}x{size[1]}','-r',str(fps),'-i','pipe:0','-an','-c:v','libx264','-preset','medium','-crf','21','-pix_fmt','yuv420p','-map_metadata','-1','-movflags','+faststart',str(path)],stdin=subprocess.PIPE)

def main():
    root=Path(__file__).resolve().parent.parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=root);parser.add_argument('--fps',type=int,default=18)
    parser.add_argument('--case',default='all');args=parser.parse_args();root=args.root
    for name in ['ffmpeg','ffprobe']:
        if not shutil.which(name):raise RuntimeError(f'{name} required')
    directory=root/'assets/media';timeline_path=root/'data/handoff.json';timeline=json.loads(timeline_path.read_text())
    regular,bold=font_path(),font_path(True)
    fonts={key:ImageFont.truetype(bold if weight else regular,size) for key,size,weight in [('brand',42,True),('title',34,False),('subtitle',25,False),('small_bold',18,True),('small',20,False),('node',27,True),('node_small',19,False),('caption_bold',25,True),('footer',16,False)]}
    for replay in timeline['cases']:
        if args.case not in ('all',replay['id']):continue
        frames=[];source_fps=1
        if replay.get('source_video_file'):
            source=directory/replay['source_video_file']
            metadata=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate','-of','json',str(source)]))['streams'][0]
            width,height=metadata['width'],metadata['height'];num,den=map(int,metadata['r_frame_rate'].split('/'));source_fps=num/den
            decoder=subprocess.Popen(['ffmpeg','-v','error','-i',str(source),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE)
            while (raw:=read_exact(decoder.stdout,width*height*3)) is not None:frames.append(Image.frombytes('RGB',(width,height),raw))
            decoder.stdout.close()
            if decoder.wait() or not frames:raise RuntimeError('Source decode failed')
        else:width,height=1280,720
        demo=directory/replay['demo_file'];motion=directory/replay['video_file'];poster=directory/replay['demo_file'].replace('.mp4','.jpg')
        composite_encoder=encoder(demo,SIZE,args.fps);motion_encoder=encoder(motion,(width,height),args.fps);output_count=0
        try:
            for index,phase in enumerate(replay['phases']):
                visual=Image.open(directory/phase['visual']['file']).convert('RGB');base=panel(replay,phase,index,len(replay['phases']),fonts,visual)
                duration=phase['end_s']-phase['start_s'];count=round(duration*args.fps)
                camera_sequence=phase.get('camera_sequence',[])
                cameras=[Image.open(directory/entry['file']).convert('RGB') for entry in camera_sequence]
                for n in range(count):
                    if cameras:
                        camera_index=min(n*len(cameras)//count,len(cameras)-1);source_frame=cameras[camera_index]
                    else:
                        source_time=phase['source_start_s']+(phase['source_end_s']-phase['source_start_s'])*n/count
                        source_frame=frames[min(round(source_time*source_fps),len(frames)-1)]
                    canvas=base.copy();resized,pos=fit(source_frame,VIDEO_BOX);canvas.paste(resized,pos)
                    x,y=path_point(connection(phase['flow']),(n/args.fps*.8)%1)
                    draw=ImageDraw.Draw(canvas);draw.ellipse((x-6,y-6,x+6,y+6),fill=BLUE)
                    if cameras:
                        draw.rectangle((45,635,949,668),fill='white')
                        draw.text((58,641),f'Recorded camera observation · capture +{camera_sequence[camera_index]["offset_s"]:.1f} s',font=fonts['small'],fill=MUTED)
                    motion_encoder.stdin.write(source_frame.tobytes());composite_encoder.stdin.write(canvas.tobytes());output_count+=1
                if index==1:canvas.save(poster,quality=92)
        finally:composite_encoder.stdin.close();motion_encoder.stdin.close()
        if composite_encoder.wait() or motion_encoder.wait():raise RuntimeError('Encoding failed')
        manifest_path=root/'data/media.json';manifest=json.loads(manifest_path.read_text());outputs=[demo,motion,poster];names={p.name for p in outputs};manifest['files']=[x for x in manifest['files'] if x['file'] not in names]
        for path in outputs:
            entry={'file':path.name,'kind':'visual_handoff_demo' if path==demo else 'execution_with_decision_holds' if path==motion else 'poster','bytes':path.stat().st_size,'sha256':digest(path),'source_timeline':'data/handoff.json','source_timeline_sha256':digest(timeline_path),'case_id':replay['id'],'representation':replay['timing_note']}
            if path.suffix=='.mp4':entry.update(width=SIZE[0] if path==demo else width,height=SIZE[1] if path==demo else height,fps=args.fps,duration_s=output_count/args.fps)
            manifest['files'].append(entry)
        manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
        print(json.dumps({'case':replay['id'],'frames':output_count,'duration_s':output_count/args.fps,'outputs':[str(p) for p in outputs]},indent=2))

if __name__=='__main__':main()
