import os, tempfile, subprocess, json, uuid
from fastapi import FastAPI, Body, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
import yt_dlp
import openai

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

api = FastAPI(title="Subtitle Maker")

def download_best_video(url, outdir):
    outtmpl = os.path.join(outdir, "%(id)s.%(ext)s")
    # Küçük dosyaları (50MB altı) tercih et; yoksa mp4/best
    ydl_opts = {
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "format": "mp4[filesize<50M]/best[filesize<50M]/mp4/best",
        "quiet": True,
        "noprogress": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
        base = os.path.splitext(path)[0]
        if not path.endswith(".mp4"):
            if os.path.exists(base + ".mp4"):
                path = base + ".mp4"
        return path

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
        base = os.path.splitext(path)[0]
        if not path.endswith(".mp4"):
            if os.path.exists(base + ".mp4"):
                path = base + ".mp4"
        return path

def extract_audio(video_path, outdir):
    audio_path = os.path.join(outdir, "audio.m4a")
    cmd = ["ffmpeg","-y","-i",video_path,"-vn","-acodec","aac",audio_path]
    subprocess.run(cmd, check=True)
    return audio_path

def whisper_srt(audio_path, translate_to):
    if not OPENAI_API_KEY:
        raise HTTPException(400, "OPENAI_API_KEY yok")
    openai.api_key = OPENAI_API_KEY
    kwargs = {
        "model": "whisper-1",
        "file": open(audio_path,"rb"),
        "response_format": "srt"
    }
    if translate_to:
        kwargs["translate"] = True
    resp = openai.Audio.transcribe(**kwargs)
    return resp

def burn_subtitles(video_path, srt_text, outdir):
    srt_path = os.path.join(outdir, "subs.srt")
    with open(srt_path,"w",encoding="utf-8") as f:
        f.write(srt_text)
    out_path = os.path.join(outdir, f"sub_{uuid.uuid4().hex}.mp4")
    vf = "subtitles=subs.srt:force_style='Fontname=Arial,Fontsize=24,PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&,BorderStyle=3,Outline=2,Shadow=0,MarginV=36'"
    cmd = ["ffmpeg","-y","-i",video_path,"-vf",vf,"-c:a","copy",out_path]
    subprocess.run(cmd, cwd=outdir, check=True)
    return out_path

class Req(BaseModel):
    url: str
    translate_to: str | None = "tr"

@api.post("/make_subtitled")
def make_subtitled(data: Req):
    with tempfile.TemporaryDirectory() as td:
        vpath = download_best_video(data.url, td)
        apath = extract_audio(vpath, td)
        srt = whisper_srt(apath, data.translate_to)
        out = burn_subtitles(vpath, srt, td)
        return FileResponse(out, filename=os.path.basename(out), media_type="video/mp4")
@api.post("/transcribe")
def transcribe_only(data: Req):
    with tempfile.TemporaryDirectory() as td:
        vpath = download_best_video(data.url, td)
        apath = extract_audio(vpath, td)
        srt = whisper_srt(apath, data.translate_to)
        return PlainTextResponse(srt, media_type="text/plain; charset=utf-8")
