import io
import os.path

import magic
import requests
import re
import time
import warnings
import zipfile

from enum import Enum
from py7zr import SevenZipFile


# Enums
class Console(Enum):
    XBOX = 'Xbox'
    PLAYSTATION_1 = 'PS1'
    PLAYSTATION_2 = 'PS2'
    PLAYSTATION_3 = 'PS3'
    NINTENDO = 'NES'
    SUPER_NINTENDO = 'SNES'
    NINTENDO_64 = 'N64'
    GAMECUBE = 'GameCube'

    def __str__(self):
        return self.value


class FileType(Enum):
    ZIP = 'application/zip'
    SEVEN_ZIP = 'application/x-7z-compressed'

    def __str__(self):
        return self.value


# Globals
media_id_to_game_url = {}


def save_7z_file(response, directory):
    with SevenZipFile(io.BytesIO(response.content), mode='r') as z:
        z.extractall(directory)


def save_zip_file(response, directory):
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        z.extractall(directory)


def save_file(response, directory):
    file_type = magic.from_buffer(response.content, mime=True)
    if file_type == FileType.ZIP.value:
        save_zip_file(response, directory)
    elif file_type == FileType.SEVEN_ZIP.value:
        save_7z_file(response, directory)
    else:
        raise Exception(f"Unrecognized file type: {file_type}")


def log_failed_game_download(game_url):
    with open('failed_game_downloads.txt', 'a+') as file:
        file.write(f"{game_url}\n")


def get_game_urls(console):
    print('Retrieving game urls...')

    game_urls = []
    page_urls = []
    base_url = 'https://vimm.net/vault'

    for letter in [chr(x) for x in range(ord('A'), ord('Z') + 1)]:
        page_urls.append(f"{base_url}/{console}/{letter}")
    page_urls.append(f"https://vimm.net/vault/?p=list&system={console}&section=number")

    current_page_num = 1
    for page_url in page_urls:
        time.sleep(0.5)
        print(f"Getting page {current_page_num} of {len(page_urls)}")
        current_page_num += 1

        page_text = requests.get(page_url).text
        game_ids = re.findall(r'/vault/(\d+)', page_text)
        for game_id in game_ids:
            game_urls.append(f"{base_url}/{game_id}")

    print('Finished\n')
    return game_urls


def get_media_ids(game_urls):
    print('Retrieving media ids...')

    # media_id_filter_text = r'<input type="hidden" name="mediaId" value="(\d+)">'
    media_id_filter_text = r'var allMedia = \[{"ID":(\d+),'
    media_ids = []

    current_game_num = 1
    for game_url in game_urls:
        try:
            time.sleep(0.5)
            game_page_text = requests.get(game_url).text
            media_id = re.search(media_id_filter_text, game_page_text).group(1)
            media_ids.append(media_id)
            media_id_to_game_url[media_id] = game_url
            print(f"game {current_game_num}/{len(game_urls)}\turl: {game_url}\t\tmedia_id: {media_id}")
        except Exception as err:
            print(f"FAILURE TO FIND MEDIA ID FOR game {current_game_num}/{len(game_urls)}, url: {game_url}. SKIPPING ENTRY")
            print(f"ERROR: {err}")
            log_failed_game_download(game_url)
        finally:
            current_game_num += 1

    print('Finished\n')
    return media_ids


def download_game(media_id, directory):
    print(f"Downloading media id {media_id}")

    download_url = f"https://download3.vimm.net/download/?mediaId={media_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0',
        'Accept': 'text/htmlapplication/xhtml+xmlapplication/xml;q=0.9image/avifimage/webp*/*;q=0.8',
        'Accept-Language': 'en-USen;q=0.5',
        'Accept-Encoding': 'gzip deflate br',
        'Connection': 'keep-alive',
        'Referer': 'https://vimm.net/',
        'Cookie': 'counted=1; __cf_bm=mgBDnr5d8YXy4Ro2Hk5lqvLvcoVJ1KSpdHun2aCi8Qw-1684816769-0-AQHC3lEpoc9ubik/wsy/4obPltr5/KVKOSUpdry74VH9c02KRluN7NI1QntLLwy8Yet76Pl+kSYbTM6satDqZ1WY1ju1s7uzryKQ0CaQWf3i',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-site',
        'Sec-Fetch-User': '?1',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache'
    }
    
    time.sleep(5)
    response = requests.get(download_url, headers=headers, stream=True)
    if not response.ok:
        warnings.warn(f"Failed to download game with media id {media_id}, url: {media_id_to_game_url.get(media_id)}")
        warnings.warn(f"Status code: {response.status_code}")
        warnings.warn(f"Reason: {response.reason}")
        log_failed_game_download(media_id_to_game_url[media_id])
    else:
        save_file(response, directory)
        print('Finished\n')


def main():
    # Configuration
    console = Console.PLAYSTATION_1  # Change me to choose games to download
    blocked_media_ids = ['29']
    local_directory = f"games/{console}"
    remote_directory = '/run/media/sebastian/x-station'
    directory = remote_directory  # Change me to choose download location

    # Create directory
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Find games to download
    print(f"Querying game id's for {console} games...")
    game_urls = get_game_urls(console)
    media_ids = get_media_ids(game_urls)

    # Download games
    print(f"Beginning download on {len(media_ids)} games")
    for media_id in media_ids:
        if media_id in blocked_media_ids:
            print(f"Skipping blocked media id: {media_id}")
            continue

        download_game(media_id, directory)

    print("Finished task")


if __name__ == "__main__":
    main()
