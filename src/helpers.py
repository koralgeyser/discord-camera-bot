import asyncio
import io
import pathlib
import shutil
import subprocess
import sys
from typing import List
import os
import zipfile
import aiohttp
import constants
from pathlib import Path

def get_autocomplete(query, choices: List):
    return list(filter(lambda x: query.lower() in x.lower(), choices))[:25]

def get_cogs():
    return [
        Path(file).stem
        for file in os.listdir(constants.COGS_DIR)
        if file.endswith(".py") and not file.startswith("__init__")
    ]

def restart():
    os.execv(sys.executable, ["python"] + sys.argv)

async def async_update(branch: str):
    TMP_DIR = "tmp/"
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    try:
        url = f"https://github.com/koralgeyser/discord-camera-bot/archive/refs/heads/{branch}.zip"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                buffer = io.BytesIO(await r.content.read())

                with zipfile.ZipFile(buffer, "r") as zip:
                    zip.extractall(TMP_DIR)

                path = os.path.join(
                    os.getcwd(),
                    os.path.join(TMP_DIR, os.listdir(TMP_DIR)[0])                
                )
                requirements = os.path.join(path, "requirements.txt")
                res = await asyncio.to_thread(
                    subprocess.run,
                    f"{sys.executable} -m pip install -r {requirements}",
                    shell=True
                )
                res.check_returncode()
                shutil.rmtree("src")
                shutil.copytree(path, os.getcwd(), dirs_exist_ok=True)
    except Exception as e:
        raise e
    finally:
        if os.path.exists(TMP_DIR):
            shutil.rmtree(TMP_DIR)

def get_timelapse_data(name):
    # Only finished timelapses atm
    buffer = io.BytesIO()
    dir = pathlib.Path(f"{constants.FINISHED_TIMELAPSES_DIR}/{name}/")
    # TODO: QOL be fancy and send in chunks if using a pyobj
    with zipfile.ZipFile(buffer, "a", zipfile.ZIP_DEFLATED, False) as archive:
        for path in dir.iterdir():
            with open(path, mode="rb") as fs:
                archive.writestr(path.name, fs.read())
    buffer.seek(0)
    return buffer


from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

def upload_to_google_folder(filename: str, folder_id: str, buffer: io.BytesIO):
    SCOPES = ['https://www.googleapis.com/auth/drive']
    SERVICE_ACCOUNT_FILE = 'google_service.json'

    creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    # create drive api client
    service = build('drive', 'v3', credentials=creds)
    media = MediaIoBaseUpload(buffer, mimetype="application/zip", resumable=True)
    request = service.files().create(
        media_body=media,
        body={'name': filename, 'parents': [folder_id]}
    )
    response = None
    while response is None:
        _, response = request.next_chunk()

def move_dir(src, dest):
    for dir in os.listdir(src):
        move_file(os.path.join(src, dir), os.path.join(dest, dir))

def move_file(src, dest):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.move(src, dest)