import os
import re
import sys
import json
import time
import asyncio
import requests
import subprocess
import urllib.parse
from urllib.parse import quote, urlparse
import yt_dlp
import cloudscraper
import m3u8
import core as helper
from utils import progress_bar
from vars import API_ID, API_HASH, BOT_TOKEN
from aiohttp import ClientSession
from pyromod import listen
from subprocess import getstatusoutput
from pytube import YouTube
from aiohttp import web
import logging
from logging.handlers import RotatingFileHandler
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pyrogram.enums import ChatType
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logging.basicConfig(
    level=logging.ERROR,
    format=
    "%(asctime)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler("logs.txt", maxBytes=50000000, backupCount=10),
        logging.StreamHandler(),
    ],
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging = logging.getLogger()
# Initialize the bot
bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

my_name = "Mr_X45"

cookies_file_path = os.getenv("COOKIES_FILE_PATH", "/modules/youtube_cookies.txt")

import os
import subprocess

def pwdlx_video(url: str, output_filename: str):
    cmd = [
        "yt-dlp",
        "--newline",
        "--merge-output-format", "mp4",
        "--remux-video", "mp4",
        "--concurrent-fragments", "8",
        "--downloader", "aria2c",
        "--downloader-args",
        "aria2c:-x16 -s16 -k1M -j16 --file-allocation=none",
        "-o", output_filename,
        url,
    ]

    subprocess.run(cmd, check=True)
    return output_filename
    

def extract_content_id(url):
  """URL se content ID extract karega"""
  try:
    if "contentId=" in url:
      print("Found 'contentId=' in URL", flush=True)
      parts = url.split("contentId=")

      if len(parts) > 1:
        content_id = parts[1]
        print(f"Initial split content ID: {content_id}", flush=True)

        # 1. URL parameters ('?' ya '&') se split karein taaki baaki ka URL hat jaye
        for char in ["?", "&"]:
          if char in content_id:
            content_id = content_id.split(char)[0]
            print(
                f"After removing query params ('{char}'): {content_id}",
                flush=True,
            )

        # 2. Agar end me '.m3u8' hai toh use hatao
        if content_id.endswith(".m3u8"):
          content_id = content_id[:-5]  # .m3u8 exactly 5 characters ka hota hai
          print(f"After removing trailing .m3u8: {content_id}", flush=True)
        # Back-up check agar URL ke beech me kahin string ke sath .m3u8 laga ho
        elif ".m3u8" in content_id:
          content_id = content_id.split(".m3u8")[0]
          print(f"After inline .m3u8 split: {content_id}", flush=True)

        print(f"✅ Extracted content ID: {content_id}", flush=True)
        return content_id

    print("❌ No content ID found in URL", flush=True)
    return None

  except Exception as e:
    print(f"❌ Error extracting content ID: {e}", flush=True)
    return None
      


def get_jw_signed_url(content_id, access_token):

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en",
        "Origin": "https://web.classplusapp.com",
        "Referer": "https://web.classplusapp.com/",
        "Region": "IN",
        "User-Agent": "Mozilla/5.0",
        "X-Access-Token": access_token,
    }

    # 1. First try: contentId
    content_api = (
        "https://api.classplusapp.com/cams/uploader/video/"
        f"jw-signed-url?contentId={quote(content_id, safe='')}"
    )

    print("[1] Trying contentId...")

    r = requests.get(
        content_api,
        headers=headers,
        timeout=15
    )

    print(f"[CONTENT] Status: {r.status_code}")

    if r.ok:
        data = r.json()
        signed_url = data.get("url")

        if signed_url:
            hostname = (urlparse(signed_url).hostname or "").lower()

            print(f"[CONTENT] Host: {hostname}")

            # Akamai URL → directly use it
            if hostname == "akamai-cdn.classplusapp.com":
                print("[+] Akamai signed URL found")
                return signed_url

    # 2. Fallback: same ID as liveSessionId
    print("[2] Content URL not Akamai")
    print("[+] Trying liveSessionId API...")

    live_api = (
        "https://api.classplusapp.com/cams/uploader/video/"
        f"jw-signed-url?liveSessionId={quote(content_id, safe='')}"
        "&isAgora=2"
    )

    r = requests.get(
        live_api,
        headers=headers,
        timeout=15
    )

    print(f"[LIVE] Status: {r.status_code}")
    r.raise_for_status()

    data = r.json()
    signed_url = data.get("url")

    if not signed_url:
        print("[!] Live signed URL not found")
        return None

    print("[+] Live signed URL received")

    return signed_url


def new_classplus_cdn(url, raw_text2, output_filename):
    format_selector = (
        f"bestvideo[height<={raw_text2}]"
        f"+bestaudio/best[height<={raw_text2}]"
    )

    cmd = [
        "yt-dlp",
        "--newline",
        "-f", format_selector,
        "--merge-output-format", "mp4",
        "--remux-video", "mp4",
        "--concurrent-fragments", "8",
        "--downloader", "aria2c",
        "--downloader-args",
        "aria2c:-x16 -s16 -k1M -j16 --file-allocation=none",

        "--add-header",
        "Origin: https://web.classplusapp.com",

        "--add-header",
        "Referer: https://web.classplusapp.com/",

        "-o",
        output_filename,
        url,
    ]

    subprocess.run(cmd, check=True)

    return output_filename
    
class Data:
    START = (
        "🌟 Welcome Dear🧸😘 {0}! 🌟\n\n"
    )
# Define the start command handler
@bot.on_message(filters.command("start"))
async def start(client: Client, msg: Message):
    if msg.from_user:
        tgname = msg.from_user.mention
    elif msg.chat.type == ChatType.CHANNEL:
        tgname = msg.chat.title or "None"
    else:
        tgname = "None"
        
    start_message = await client.send_message(
        msg.chat.id,
        Data.START.format(tgname)
    )

    await asyncio.sleep(1)
    await start_message.edit_text(
        Data.START.format(tgname) +
        "Initializing Uploader bot...😚🤖\n\n"
        "Progress: [⬜⬜⬜⬜⬜⬜⬜⬜⬜] 0%\n\n"
    )

    await asyncio.sleep(1)
    await start_message.edit_text(
        Data.START.format(tgname) +
        "Loading features...😗⏳\n\n"
        "Progress: [🟥🟥🟥⬜⬜⬜⬜⬜⬜] 25%\n\n"
    )
    
    await asyncio.sleep(1)
    await start_message.edit_text(
        Data.START.format(tgname) +
        "This may take a moment, sit back and relax!🫣💪\n\n"
        "Progress: [🟧🟧🟧🟧🟧⬜⬜⬜⬜] 50%\n\n"
    )

    await asyncio.sleep(1)
    await start_message.edit_text(
        Data.START.format(tgname) +
        "Checking Bot Status...😙🔍\n\n"
        "Progress: [🟨🟨🟨🟨🟨🟨🟨⬜⬜] 75%\n\n"
    )

    await asyncio.sleep(1)
    await start_message.edit_text(
        Data.START.format(tgname) +
        "Checking status Okay... Command is Private Dear🫂.**Bot Made BY @rahulx45_vibe**🔍\n\n"
        "Progress:[🟩🟩🟩🟩🟩🟩🟩🟩🟩] 100%\n\n"
    )

@bot.on_message(filters.command(["stop"]) )
async def restart_handler(_, m):
    await m.reply_text("⚪**WORK IS STOPPED**🔵", True)
    os.execl(sys.executable, sys.executable, *sys.argv)


@bot.on_message(filters.command(["Mrx45"]) )
async def txt_handler(bot: Client, m: Message):
    editable = await m.reply_text(
        f"╭───❮ **MR_X45 TXT LEECHER** ❯───►\n"
        f"│\n"
        f"├──» **SEND ME THE TXT FILE TO BEGIN** 📥\n"
        f"├──» **JUST WAIT AND WATCH THE MAGIC** ⚡\n"
        f"│\n"
        f"╰───╭⚡ **POWERED BY MR_X45** ⚡╯───►"
    )
    input: Message = await bot.listen(editable.chat.id)
    x = await input.download()
    await input.delete(True)
    file_name, ext = os.path.splitext(os.path.basename(x))
    credit = f"@rahulx45_vibe"
    token = f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzYxNTE3MzAuMTI2LCJkYXRhIjp7Il9pZCI6IjYzMDRjMmY3Yzc5NjBlMDAxODAwNDQ4NyIsInVzZXJuYW1lIjoiNzc2MTAxNzc3MCIsImZpcnN0TmFtZSI6IkplZXYgbmFyYXlhbiIsImxhc3ROYW1lIjoic2FoIiwib3JnYW5pemF0aW9uIjp7Il9pZCI6IjVlYjM5M2VlOTVmYWI3NDY4YTc5ZDE4OSIsIndlYnNpdGUiOiJwaHlzaWNzd2FsbGFoLmNvbSIsIm5hbWUiOiJQaHlzaWNzd2FsbGFoIn0sImVtYWlsIjoiV1dXLkpFRVZOQVJBWUFOU0FIQEdNQUlMLkNPTSIsInJvbGVzIjpbIjViMjdiZDk2NTg0MmY5NTBhNzc4YzZlZiJdLCJjb3VudHJ5R3JvdXAiOiJJTiIsInR5cGUiOiJVU0VSIn0sImlhdCI6MTczNTU0NjkzMH0.iImf90mFu_cI-xINBv4t0jVz-rWK1zeXOIwIFvkrS0M"
    try:    
        with open(x, "r") as f:
            content = f.read()
        content = content.split("\n")
        links = []
        for i in content:
            links.append(i.split("://", 1))
        os.remove(x)
    except:
        await m.reply_text("Are yaar **txt** file Bhejni thi \n\n **Chal koi na tap on** /Teddy **Or*   /Bear **then** \n\n **resend txt file to me again🫂.**")
        os.remove(x)
        return
   
    await editable.edit(f"╭───❮ **TOTAL LINKS FOUND:** `{len(links)}` ❯───►\n├──» **ENTER START INDEX:** *(DEFAULT IS 1)* 🔢\n╰───╭⚡ **[ Mr_X45 Studio ]** ⚡╯───►")
    input0: Message = await bot.listen(editable.chat.id)
    raw_text = input0.text
    await input0.delete(True)
    try:
        arg = int(raw_text)
    except:
        arg = 1
    await editable.edit(f"**ENTER YOUR BATCH NAME OR SEND** `/Rahul` **FOR EXTRACTING NAME FROM TEXT FILENAME.**")
    input1: Message = await bot.listen(editable.chat.id)
    raw_text0 = input1.text
    await input1.delete(True)
    if raw_text0 == '/Rahul':
        b_name = file_name
    else:
        b_name = raw_text0

    await editable.edit(
        f"╭───❮ **SELECT RESOLUTION** ❯───►\n"
        f"├──» **144**\n"
        f"├──» **240**\n"
        f"├──» **360**\n"
        f"├──» **480**\n"
        f"├──» **720**\n"
        f"├──» **1080**\n"
        f"╰───╭⚡ **[ Mr_X45 ]** ⚡╯───►"
    )
    input2: Message = await bot.listen(editable.chat.id)
    raw_text2 = input2.text
    await input2.delete(True)
    try:
        if raw_text2 == "144":
            res = "256x144"
        elif raw_text2 == "240":
            res = "426x240"
        elif raw_text2 == "360":
            res = "640x360"
        elif raw_text2 == "480":
            res = "854x480"
        elif raw_text2 == "720":
            res = "1280x720"
        elif raw_text2 == "1080":
            res = "1920x1080" 
        else: 
            res = "UN"
    except Exception:
            res = "UN"
    
    await editable.edit(f"╭───❮ **CREDITS SETUP** ❯───►\n├──» **ENTER UPLOADER NAME OR SEND** `/Rahul` **FOR DEFAULT** 🎓\n╰───╭⚡ **[ @rahulx45_vibe ]** ⚡╯───►")
    input3: Message = await bot.listen(editable.chat.id)
    raw_text3 = input3.text
    await input3.delete(True)
    if raw_text3 == '/Cutie':
        CR = credit
    else:
        CR = raw_text3
        
    await editable.edit(f"╭───❮ **PW TOKEN SETUP** ❯───►\n├──» **ENTER PW TOKEN OR SEND** `/X45` **FOR DEFAULT** 🔑\n╰───╭⚡ **[ Mr_X45 Studio ]** ⚡╯───►")
    input4: Message = await bot.listen(editable.chat.id)
    raw_text4 = input4.text
    await input4.delete(True)
    if raw_text4 == '/vip':
        access_token = token
    else:
        access_token = raw_text4
        
    await editable.edit(f"╭───❮ **THUMBNAIL SETUP** ❯───►\n├──» **SEND THUMBNAIL URL** (Ending with .jpg) **OR SEND** `no` 🖼️\n╰───╭⚡ **[ Mr_X45 Studio ]** ⚡╯───►")
    input6 = message = await bot.listen(editable.chat.id)
    raw_text6 = input6.text
    await input6.delete(True)
    await editable.delete()

    thumb = input6.text
    if thumb.startswith("http://") or thumb.startswith("https://"):
        getstatusoutput(f"wget '{thumb}' -O 'thumb.jpg'")
        thumb = "thumb.jpg"
    else:
        thumb == "no"

    count =int(raw_text)    
    try:
        for i in range(arg-1, len(links)):

            Vxy = links[i][1].replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","")
            url = "https://" + Vxy
            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(url, headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language': 'en-US,en;q=0.9', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Referer': 'http://www.visionias.in/', 'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36', 'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"',}) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)

            if "acecwply" in url:
                cmd = f'yt-dlp -o "{name}.%(ext)s" -f "bestvideo[height<={raw_text2}]+bestaudio" --hls-prefer-ffmpeg --no-keep-video --remux-video mkv --no-warning "{url}"'
                

            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(url, headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language': 'en-US,en;q=0.9', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Referer': 'http://www.visionias.in/', 'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36', 'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"',}) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)

            elif 'https://contentId=' in url or 'contentHashIdl=' in url:
                content_id = extract_content_id(url)
                cpurl = get_jw_signed_url(content_id, access_token)
                print(f"Fetched URL: {cpurl}") # Debugging ke liye
                url = cpurl
                print(f"CP Url: {url}")
            
            
            elif '/master.mpd' in url or "/dash/" in url or ".mp4?" in url or "?Signature=" in url or "d1d34p8vz63oiq.cloudfront.net" in url or "parentId=" in url or "childId=" in url:
                if "parentId=" in url or "childId=" in url:
                    url = f"https://ankitshakyaxapi.vercel.app/download?mpd_url={url}&token={raw_text4}&quality={raw_text2}"
                else:
                    url = f"https://ankitshakyaxapi.vercel.app/download?mpd_url={url}&quality={raw_text2}"
                    
            name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("#", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
            name = f'{str(count).zfill(3)}) {name1[:60]} {my_name}'
                      
            
            if "edge.api.brightcove.com" in url:
                bcov = 'bcov_auth=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE3MjQyMzg3OTEsImNvbiI6eyJpc0FkbWluIjpmYWxzZSwiYXVzZXIiOiJVMFZ6TkdGU2NuQlZjR3h5TkZwV09FYzBURGxOZHowOSIsImlkIjoiZEUxbmNuZFBNblJqVEROVmFWTlFWbXhRTkhoS2R6MDkiLCJmaXJzdF9uYW1lIjoiYVcxV05ITjVSemR6Vm10ak1WUlBSRkF5ZVNzM1VUMDkiLCJlbWFpbCI6Ik5Ga3hNVWhxUXpRNFJ6VlhiR0ppWTJoUk0wMVdNR0pVTlU5clJXSkRWbXRMTTBSU2FHRnhURTFTUlQwPSIsInBob25lIjoiVUhVMFZrOWFTbmQ1ZVcwd1pqUTViRzVSYVc5aGR6MDkiLCJhdmF0YXIiOiJLM1ZzY1M4elMwcDBRbmxrYms4M1JEbHZla05pVVQwOSIsInJlZmVycmFsX2NvZGUiOiJOalZFYzBkM1IyNTBSM3B3VUZWbVRtbHFRVXAwVVQwOSIsImRldmljZV90eXBlIjoiYW5kcm9pZCIsImRldmljZV92ZXJzaW9uIjoiUShBbmRyb2lkIDEwLjApIiwiZGV2aWNlX21vZGVsIjoiU2Ftc3VuZyBTTS1TOTE4QiIsInJlbW90ZV9hZGRyIjoiNTQuMjI2LjI1NS4xNjMsIDU0LjIyNi4yNTUuMTYzIn19.snDdd-PbaoC42OUhn5SJaEGxq0VzfdzO49WTmYgTx8ra_Lz66GySZykpd2SxIZCnrKR6-R10F5sUSrKATv1CDk9ruj_ltCjEkcRq8mAqAytDcEBp72-W0Z7DtGi8LdnY7Vd9Kpaf499P-y3-godolS_7ixClcYOnWxe2nSVD5C9c5HkyisrHTvf6NFAuQC_FD3TzByldbPVKK0ag1UnHRavX8MtttjshnRhv5gJs5DQWj4Ir_dkMcJ4JaVZO3z8j0OxVLjnmuaRBujT-1pavsr1CCzjTbAcBvdjUfvzEhObWfA1-Vl5Y4bUgRHhl1U-0hne4-5fF0aouyu71Y6W0eg'
                url = url.split("bcov_auth")[0]+bcov
                
            if "youtu" in url:
                ytf = f"b[height<={raw_text2}][ext=mp4]/bv[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]"
            else:
                ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"
            
            if "jw-prod" in url:
                cmd = f'yt-dlp -o "{name}.mp4" "{url}"'

            elif "youtube.com" in url or "youtu.be" in url:
                cmd = f'yt-dlp --cookies youtube_cookies.txt -f "{ytf}" "{url}" -o "{name}".mp4'

            else:
                cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

                        
                cc = f"📁 **𝐎𝐅𝐅𝐈𝐂𝐈𝐀𝐋 𝐕𝐈𝐃𝐄𝐎 𝐋𝐄𝐂𝐓𝐔𝐑𝐄** 🎬\n|\n|-◆ **𝐓𝐈𝐓𝐋𝐄 ->** 〖 {name1} 〗 🎬⚡\n|\n|-◆ **𝐁𝐀𝐓𝐂𝐇 ->** 〖 {b_name} 〗 🚨\n|\n|-◆ **𝐄𝐗𝐓𝐑𝐀𝐂𝐓𝐄𝐃 𝐁𝐘 ->** {CR} 👑\n|\n\\_________________________\n\n═══『 **𝐌𝐫_𝐗𝟒𝟓** 』═══"
                cc1 = f"📁 **𝐎𝐅𝐅𝐈𝐂𝐈𝐀𝐋 𝐒𝐓𝐔𝐃𝐘 𝐃𝐎𝐂𝐔𝐌𝐄𝐍𝐓** 📚\n|\n|-◆ **𝐓𝐈𝐓𝐋𝐄 ->** 〖 {name1} 〗 📚✨\n|\n|-◆ **𝐁𝐀𝐓𝐂𝐇 ->** 〖 {b_name} 〗 🍁\n|\n|-◆ **𝐄𝐗𝐓𝐑𝐀𝐂𝐓𝐄𝐃 𝐁𝐘 ->** {CR} 🌸\n|\n\\_________________________\n\n═══『 **𝐌𝐫_𝐗𝟒𝟓** 』═══"
                ccimg = f"🖼 **𝐎𝐅𝐅𝐈𝐂𝐈𝐀𝐋 𝐈𝐌𝐀𝐆𝐄 𝐍𝐎𝐓𝐄𝐒** 🖼\n|\n|-◆ **𝐓𝐈𝐓𝐋𝐄 ->** 〖 {name1} 〗 🖼✨\n|\n|-◆ **𝐁𝐀𝐓𝐂𝐇 ->** 〖 {b_name} 〗 🍁\n|\n|-◆ **𝐄𝐗𝐓𝐑𝐀𝐂𝐓𝐄𝐃 𝐁𝐘 ->** {CR} 🌸\n|\n\\_________________________\n\n═══『 **𝐌𝐫_𝐗𝟒𝟓** 』═══"
            
                if "drive" in url:
                    try:
                        ka = await helper.download(url, name)
                        copy = await bot.send_document(chat_id=m.chat.id,document=ka, caption=cc1)
                        count+=1
                        os.remove(ka)
                        time.sleep(1)
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue
                        
                elif ".pdf" in url:
                    try:
                        cmd = f'yt-dlp -o "{name}.pdf" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                        count += 1
                        os.remove(f'{name}.pdf')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count += 1
                        continue
                        
                elif ".pdf" in url:
                    try:
                        await asyncio.sleep(4)
                        url = url.replace(" ", "%20")
                        scraper = cloudscraper.create_scraper()
                        response = scraper.get(url)
                        if response.status_code == 200:
                            with open(f'{name}.pdf', 'wb') as file:
                                file.write(response.content)
                            await asyncio.sleep(4)
                            copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                            count += 1
                            os.remove(f'{name}.pdf')
                        else:
                            await m.reply_text(f"Failed to download PDF: {response.status_code} {response.reason}")
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count += 1
                        continue
                        
                elif any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png"]):
                    try:
                        await asyncio.sleep(4)
                        url = url.replace(" ", "%20")
                        scraper = cloudscraper.create_scraper()
                        response = scraper.get(url)
                        if response.status_code == 200:
                            with open(f'{name}.jpg', 'wb') as file:
                                file.write(response.content)
                            await asyncio.sleep(2)
                            copy = await bot.send_photo(chat_id=m.chat.id, photo=f'{name}.jpg', caption=ccimg)
                            count += 1
                            os.remove(f'{name}.jpg')
                        else:
                            await m.reply_text(f"Failed to download Image: {response.status_code} {response.reason}")
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        await asyncio.sleep(2)
                        return
                    except Exception as e:
                        await m.reply_text(f"An error occurred: {str(e)}")
                        await asyncio.sleep(4)

                elif '/master.mpd' in url or ".mp4?" in url or "?Signature=" in url or "d1d34p8vz63oiq.cloudfront.net" in url or "parentId=" in url or "childId=" in url:
                    Show = f"**Physics Wallah**\n\n✰🖥️𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐢𝐧𝐠 𝗪𝗮𝗶𝘁..🤖🚀»\n\n📝 Title:- `{name}\n\n🖥️ 𝐐𝐮𝐥𝐢𝐭𝐲 » {raw_text2}`\n\n**🔗 𝐔𝐑𝐋 »** `{url}`\n\n**𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲🧸: ✦ @rahulx45_vibe"
                    prog = await m.reply_text(Show)
                    output_filename = f"{name}.mp4"
                    res_file = pwdlx_video(url, output_filename)
                    filename= res_file
                    await prog.delete(True)
                    await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
                    count += 1
                    time.sleep(1)
                    continue
                    
                elif 'akamai-cdn.classplusapp.com' in url:
                    Show = f"**```ClassPlus```**\n\n✰🖥️𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐢𝐧𝐠 𝗪𝗮𝗶𝘁..🤖🚀»\n\n📝 Title:- `{name}\n\n🖥️ 𝐐𝐮𝐥𝐢𝐭𝐲 » {raw_text2}`\n\n**🔗 𝐔𝐑𝐋 »** `{url}`\n\n**𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲🧸: ✦ @rahulx45_vibe"
                    prog = await m.reply_text(Show)
                    output_filename = f"{name}.mp4"
                    res_file = new_classplus_cdn(url, raw_text2, output_filename)
                    filename = res_file
                    await prog.delete(True)
                    await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
                    count += 1
                    time.sleep(e.x)
                    continue
                
                else:
                    Show = f"✰🖥️𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐢𝐧𝐠 𝗪𝗮𝗶𝘁..🤖🚀»\n\n📝 Title:- `{name}\n\n🖥️ 𝐐𝐮𝐥𝐢𝐭𝐲 » {raw_text2}`\n\n**🔗 𝐔𝐑𝐋 »** `{url}`\n\n**𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲🧸: ✦ @rahulx45_vibe"
                    prog = await m.reply_text(Show)
                    res_file = await helper.download_video(url, cmd, name)
                    filename = res_file
                    await prog.delete(True)
                    await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
                    count += 1
                    time.sleep(1)

    except Exception as e:
        await m.reply_text(e)
    await m.reply_text("✅ 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲 𝐃𝐨𝐧𝐞")
                        
@bot.on_message(filters.command(["Official"]) )
async def txt_handler(bot: Client, m: Message):
    editable = await m.reply_text(
        f"╭───❮ **MR_X45 TXT LEECHER** ❯───►\n"
        f"│\n"
        f"├──» **SEND ME THE TXT FILE TO BEGIN** 📥\n"
        f"├──» **JUST WAIT AND WATCH THE MAGIC** ⚡\n"
        f"│\n"
        f"╰───╭⚡ **POWERED BY MR_X45** ⚡╯───►"
    )
    input: Message = await bot.listen(editable.chat.id)
    x = await input.download()
    await input.delete(True)
    file_name, ext = os.path.splitext(os.path.basename(x))
    credit = f"@rahulx45_vibe"
    token = f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzYxNTE3MzAuMTI2LCJkYXRhIjp7Il9pZCI6IjYzMDRjMmY3Yzc5NjBlMDAxODAwNDQ4NyIsInVzZXJuYW1lIjoiNzc2MTAxNzc3MCIsImZpcnN0TmFtZSI6IkplZXYgbmFyYXlhbiIsImxhc3ROYW1lIjoic2FoIiwib3JnYW5pemF0aW9uIjp7Il9pZCI6IjVlYjM5M2VlOTVmYWI3NDY4YTc5ZDE4OSIsIndlYnNpdGUiOiJwaHlzaWNzd2FsbGFoLmNvbSIsIm5hbWUiOiJQaHlzaWNzd2FsbGFoIn0sImVtYWlsIjoiV1dXLkpFRVZOQVJBWUFOU0FIQEdNQUlMLkNPTSIsInJvbGVzIjpbIjViMjdiZDk2NTg0MmY5NTBhNzc4YzZlZiJdLCJjb3VudHJ5R3JvdXAiOiJJTiIsInR5cGUiOiJVU0VSIn0sImlhdCI6MTczNTU0NjkzMH0.iImf90mFu_cI-xINBv4t0jVz-rWK1zeXOIwIFvkrS0M"
    try:    
        with open(x, "r") as f:
            content = f.read()
        content = content.split("\n")
        links = []
        for i in content:
            links.append(i.split("://", 1))
        os.remove(x)
    except:
        await m.reply_text("Are yaar **txt** file Bhejni thi \n\n **Chal koi na tap on** /Teddy **Or*    /Bear **then** \n\n **resend txt file to me again🫂.**")
        os.remove(x)
        return
   
    await editable.edit(f"╭───❮ **TOTAL LINKS FOUND:** `{len(links)}` ❯───►\n├──» **ENTER START INDEX:** *(DEFAULT IS 1)* 🔢\n╰───╭⚡ **[ Mr_X45 Studio ]** ⚡╯───►")
    input0: Message = await bot.listen(editable.chat.id)
    raw_text = input0.text
    await input0.delete(True)
    try:
        arg = int(raw_text)
    except:
        arg = 1
    await editable.edit(f"**ENTER YOUR BATCH NAME OR SEND** `/Rahul` **FOR EXTRACTING NAME FROM TEXT FILENAME.**")
    input1: Message = await bot.listen(editable.chat.id)
    raw_text0 = input1.text
    await input1.delete(True)
    if raw_text0 == '/Rahul':
        b_name = file_name
    else:
        b_name = raw_text0

    await editable.edit(
        f"╭───❮ **SELECT RESOLUTION** ❯───►\n"
        f"├──» **144**\n"
        f"├──» **240**\n"
        f"├──» **360**\n"
        f"├──» **480**\n"
        f"├──» **720**\n"
        f"├──» **1080**\n"
        f"╰───╭⚡ **[ Mr_X45 ]** ⚡╯───►"
    )
    input2: Message = await bot.listen(editable.chat.id)
    raw_text2 = input2.text
    await input2.delete(True)
    try:
        if raw_text2 == "144":
            res = "256x144"
        elif raw_text2 == "240":
            res = "426x240"
        elif raw_text2 == "360":
            res = "640x360"
        elif raw_text2 == "480":
            res = "854x480"
        elif raw_text2 == "720":
            res = "1280x720"
        elif raw_text2 == "1080":
            res = "1920x1080" 
        else: 
            res = "UN"
    except Exception:
            res = "UN"
    
    await editable.edit(f"╭───❮ **CREDITS SETUP** ❯───►\n├──» **ENTER UPLOADER NAME OR SEND** `/Rahul` **FOR DEFAULT** 🎓\n╰───╭⚡ **[ @rahulx45_vibe ]** ⚡╯───►")
    input3: Message = await bot.listen(editable.chat.id)
    raw_text3 = input3.text
    await input3.delete(True)
    if raw_text3 == '/Love':
        CR = credit
    else:
        CR = raw_text3
        
    await editable.edit(f"╭───❮ **PW TOKEN SETUP** ❯───►\n├──» **ENTER PW TOKEN OR SEND** `/X45` **FOR DEFAULT** 🔑\n╰───╭⚡ **[ Mr_X45 Studio ]** ⚡╯───►")
    input4: Message = await bot.listen(editable.chat.id)
    raw_text4 = input4.text
    await input4.delete(True)
    if raw_text4 == '/vip':
        access_token = token
    else:
        access_token = raw_text4
        
    await editable.edit(f"╭───❮ **THUMBNAIL SETUP** ❯───►\n├──» **SEND THUMBNAIL URL** (Ending with .jpg) **OR SEND** `no` 🖼️\n╰───╭⚡ **[ Mr_X45 Studio ]** ⚡╯───►")
    input6 = message = await bot.listen(editable.chat.id)
    raw_text6 = input6.text
    await input6.delete(True)
    await editable.delete()

    thumb = input6.text
    if thumb.startswith("http://") or thumb.startswith("https://files.catbox.moe/mwhput.jpg"):
        getstatusoutput(f"wget '{thumb}' -O 'thumb.jpg'")
        thumb = "thumb.jpg"
    else:
        thumb == "no"

    count =int(raw_text)    
    try:
        for i in range(arg-1, len(links)):

            Vxy = links[i][1].replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","")
            url = "https://" + Vxy
            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(url, headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language': 'en-US,en;q=0.9', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Referer': 'http://www.visionias.in/', 'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36', 'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"',}) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)

            if "acecwply" in url:
                cmd = f'yt-dlp -o "{name}.%(ext)s" -f "bestvideo[height<={raw_text2}]+bestaudio" --hls-prefer-ffmpeg --no-keep-video --remux-video mkv --no-warning "{url}"'
                

            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(url, headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language': 'en-US,en;q=0.9', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Referer': 'http://www.visionias.in/', 'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36', 'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"',}) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)

            elif 'https://contentId=' in url or 'contentHashIdl=' in url:
                content_id = extract_content_id(url)
                cpurl = get_jw_signed_url(content_id, access_token)
                print(f"Fetched URL: {cpurl}")
                url = cpurl
                print(f"CP Url: {url}")
            
            
            elif '/master.mpd' in url or "/dash/" in url or ".mp4?" in url or "?Signature=" in url or "d1d34p8vz63oiq.cloudfront.net" in url or "parentId=" in url or "childId=" in url:
                if "parentId=" in url or "childId=" in url:
                    url = f"https://ankitshakyaxapi.vercel.app/download?mpd_url={url}&token={raw_text4}&quality={raw_text2}"
                else:
                    url = f"https://ankitshakyaxapi.vercel.app/download?mpd_url={url}&quality={raw_text2}"
                    
            name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("#", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
            name = f'{str(count).zfill(3)}) {name1[:60]} {my_name}'
          

            if "edge.api.brightcove.com" in url:
                bcov = 'bcov_auth=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE3MjQyMzg3OTEsImNvbiI6eyJpc0FkbWluIjpmYWxzZSwiYXVzZXIiOiJVMFZ6TkdGU2NuQlZjR3h5TkZwV09FYzBURGxOZHowOSIsImlkIjoiZEUxbmNuZFBNblJqVEROVmFWTlFWbXhRTkhoS2R6MDkiLCJmaXJzdF9uYW1lIjoiYVcxV05ITjVSemR6Vm10ak1WUlBSRkF5ZVNzM1VUMDkiLCJlbWFpbCI6Ik5Ga3hNVWhxUXpRNFJ6VlhiR0ppWTJoUk0wMVdNR0pVTlU5clJXSkRWbXRMTTBSU2FHRnhURTFTUlQwPSIsInBob25lIjoiVUhVMFZrOWFTbmQ1ZVcwd1pqUTViRzVSYVc5aGR6MDkiLCJhdmF0YXIiOiJLM1ZzY1M4elMwcDBRbmxrYms4M1JEbHZla05pVVQwOSIsInJlZmVycmFsX2NvZGUiOiJOalZFYzBkM1IyNTBSM3B3VUZWbVRtbHFRVXAwVVQwOSIsImRldmljZV90eXBlIjoiYW5kcm9pZCIsImRldmljZV92ZXJzaW9uIjoiUShBbmRyb2lkIDEwLjApIiwiZGV2aWNlX21vZGVsIjoiU2Ftc3VuZyBTTS1TOTE4QiIsInJlbW90ZV9hZGRyIjoiNTQuMjI2LjI1NS4xNjMsIDU0LjIyNi4yNTUuMTYzIn19.snDdd-PbaoC42OUhn5SJaEGxq0VzfdzO49WTmYgTx8ra_Lz66GySZykpd2SxIZCnrKR6-R10F5sUSrKATv1CDk9ruj_ltCjEkcRq8mAqAytDcEBp72-W0Z7DtGi8LdnY7Vd9Kpaf499P-y3-godolS_7ixClcYOnWxe2nSVD5C9c5HkyisrHTvf6NFAuQC_FD3TzByldbPVKK0ag1UnHRavX8MtttjshnRhv5gJs5DQWj4Ir_dkMcJ4JaVZO3z8j0OxVLjnmuaRBujT-1pavsr1CCzjTbAcBvdjUfvzEhObWfA1-Vl5Y4bUgRHhl1U-0hne4-5fF0aouyu71Y6W0eg'
                url = url.split("bcov_auth")[0]+bcov
                
            if "youtu" in url:
                ytf = f"b[height<={raw_text2}][ext=mp4]/bv[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]"
            else:
                ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"
            
            if "jw-prod" in url:
                cmd = f'yt-dlp -o "{name}.mp4" "{url}"'

            elif "youtube.com" in url or "youtu.be" in url:
                cmd = f'yt-dlp --cookies youtube_cookies.txt -f "{ytf}" "{url}" -o "{name}".mp4'

            else:
                cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

            cc = f"📁 **𝐎𝐅𝐅𝐈𝐂𝐈𝐀𝐋 𝐕𝐈𝐃𝐄𝐎 𝐋𝐄𝐂𝐓𝐔𝐑𝐄** 🎬\n|\n|-◆ **𝐓𝐈𝐓𝐋𝐄 ->** 〖 {name1} 〗 🎬⚡\n|\n|-◆ **𝐁𝐀𝐓𝐂𝐇 ->** 〖 {b_name} 〗 🚨\n|\n|-◆ **𝐄𝐗𝐓𝐑𝐀𝐂𝐓𝐄𝐃 𝐁𝐘 ->** {CR} 👑\n|\n\\_________________________\n\n═══『 **𝐌𝐫_𝐗𝟒𝟓** 』═══"
            cc1 = f"📁 **𝐎𝐅𝐅𝐈𝐂𝐈𝐀𝐋 𝐒𝐓𝐔𝐃𝐘 𝐃𝐎𝐂𝐔𝐌𝐄𝐍𝐓** 📚\n|\n|-◆ **𝐓𝐈𝐓𝐋𝐄 ->** 〖 {name1} 〗 📚✨\n|\n|-◆ **𝐁𝐀𝐓𝐂𝐇 ->** 〖 {b_name} 〗 🍁\n|\n|-◆ **𝐄𝐗𝐓𝐑𝐀𝐂𝐓𝐄𝐃 𝐁𝐘 ->** {CR} 🌸\n|\n\\_________________________\n\n═══『 **𝐌𝐫_𝐗𝟒𝟓** 』═══"
            ccimg = f"🖼 **𝐎𝐅𝐅𝐈𝐂𝐈𝐀𝐋 𝐈𝐌𝐀𝐆𝐄 𝐍𝐎𝐓𝐄𝐒** 🖼\n|\n|-◆ **𝐓𝐈𝐓𝐋𝐄 ->** 〖 {name1} 〗 🖼✨\n|\n|-◆ **𝐁𝐀𝐓𝐂𝐇 ->** 〖 {b_name} 〗 🍁\n|\n|-◆ **𝐄𝐗𝐓𝐑𝐀𝐂𝐓𝐄𝐃 𝐁𝐘 ->** {CR} 🌸\n|\n\\_________________________\n\n═══『 **𝐌𝐫_𝐗𝟒𝟓** 』═══"
                
            if "drive" in url:
                    try:
                        ka = await helper.download(url, name)
                        copy = await bot.send_document(chat_id=m.chat.id,document=ka, caption=cc1)
                        count+=1
                        os.remove(ka)
                        time.sleep(1)
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue
                        
            elif ".pdf" in url:
                    try:
                        cmd = f'yt-dlp -o "{name}.pdf" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                        count += 1
                        os.remove(f'{name}.pdf')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count += 1
                        continue
                        
            elif ".pdf" in url:
                    try:
                        await asyncio.sleep(4)
                        url = url.replace(" ", "%20")
                        scraper = cloudscraper.create_scraper()
                        response = scraper.get(url)
                        if response.status_code == 200:
                            with open(f'{name}.pdf', 'wb') as file:
                                file.write(response.content)
                            await asyncio.sleep(4)
                            copy = await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                            count += 1
                            os.remove(f'{name}.pdf')
                        else:
                            await m.reply_text(f"Failed to download PDF: {response.status_code} {response.reason}")
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        count += 1
                        continue
                        
            elif any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png"]):
                    try:
                        await asyncio.sleep(4)
                        url = url.replace(" ", "%20")
                        scraper = cloudscraper.create_scraper()
                        response = scraper.get(url)
                        if response.status_code == 200:
                            with open(f'{name}.jpg', 'wb') as file:
                                file.write(response.content)
                            await asyncio.sleep(2)
                            copy = await bot.send_photo(chat_id=m.chat.id, photo=f'{name}.jpg', caption=ccimg)
                            count += 1
                            os.remove(f'{name}.jpg')
                        else:
                            await m.reply_text(f"Failed to download Image: {response.status_code} {response.reason}")
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        await asyncio.sleep(2)
                        return
                    except Exception as e:
                        await m.reply_text(f"An error occurred: {str(e)}")
                        await asyncio.sleep(4)

            elif '/master.mpd' in url or ".mp4?" in url or "?Signature=" in url or "d1d34p8vz63oiq.cloudfront.net" in url or "parentId=" in url or "childId=" in url:
                Show = f"**Physics Wallah**\n\n✰🖥️𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐢𝐧𝐠 𝗪𝗮𝗶𝘁..🤖🚀»\n\n📝 Title:- `{name}\n\n🖥️ 𝐐𝐮𝐥𝐢𝐭𝐲 » {raw_text2}`\n\n**🔗 𝐔𝐑𝐋 »** `{url}`\n\n**𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲🧸: ✦ @rahulx45_vibe"
                prog = await m.reply_text(Show)
                output_filename = f"{name}.mp4"
                res_file = pwdlx_video(url, output_filename)
                filename= res_file
                await prog.delete(True)
                await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
                count += 1
                time.sleep(1)
                continue
                    
            elif 'akamai-cdn.classplusapp.com' in url:
                Show = f"**```ClassPlus```**\n\n✰🖥️𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐢𝐧𝐠 𝗪𝗮𝗶𝘁..🤖🚀»\n\n📝 Title:- `{name}\n\n🖥️ 𝐐𝐮𝐥𝐢𝐭𝐲 » {raw_text2}`\n\n**🔗 𝐔𝐑𝐋 »** `{url}`\n\n**𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲🧸: ✦ @rahulx45_vibe"
                prog = await m.reply_text(Show)
                output_filename = f"{name}.mp4"
                res_file = new_classplus_cdn(url, raw_text2, output_filename)
                filename = res_file
                await prog.delete(True)
                await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
                count += 1
                time.sleep(e.x)
                continue
                
            else:
                Show = f"✰🖥️𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐢𝐧𝐠 𝗪𝗮𝗶𝘁..🤖🚀»\n\n📝 Title:- `{name}\n\n🖥️ 𝐐𝐮𝐥𝐢𝐭𝐲 » {raw_text2}`\n\n**🔗 𝐔𝐑𝐋 »** `{url}`\n\n**𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲🧸: ✦ @rahulx45_vibe"
                prog = await m.reply_text(Show)
                res_file = await helper.download_video(url, cmd, name)
                filename = res_file
                await prog.delete(True)
                await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
                count += 1
                time.sleep(1)

    except Exception as e:
        await m.reply_text(e)
    await m.reply_text("✅ 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲 𝐃𝐨𝐧𝐞")


bot.run()
