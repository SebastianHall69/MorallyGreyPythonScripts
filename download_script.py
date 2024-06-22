import io
import os.path

import click
import json
import requests
import re
import time
import warnings
import zipfile

from datetime import datetime
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


class MimeType(Enum):
    ZIP = 'application/zip'
    SEVEN_ZIP = 'application/x-7z-compressed'

    def __str__(self):
        return self.value


# Globals
game_id_to_url = {}


def get_console_from_cli_option(cli_option):
    console_map = {
        'xbox': Console.XBOX,
        'ps1': Console.PLAYSTATION_1,
        'ps2': Console.PLAYSTATION_2,
        'ps3': Console.PLAYSTATION_3,
        'nes': Console.NINTENDO,
        'snes': Console.SUPER_NINTENDO,
        'n64': Console.NINTENDO_64,
        'gc': Console.GAMECUBE
    }
    return console_map.get(cli_option)


def get_default_directory(console):
    return f"games/{console}"


def get_base_url(console):
    url_2 = 'https://download2.vimm.net'
    url_3 = 'https://download3.vimm.net'
    url_2_set = [Console.PLAYSTATION_2, Console.XBOX]
    url_3_set = [
        Console.NINTENDO_64,
        Console.PLAYSTATION_1,
        Console.GAMECUBE,
        Console.PLAYSTATION_3,
        Console.NINTENDO,
        Console.SUPER_NINTENDO
    ]

    if console in url_2_set:
        return url_2
    elif console in url_3_set:
        return url_3
    else:
        print(f"No verified download base URL for {console}. Reverting to a default")
        return url_3


def get_file_name_from_response(response):
    disposition = response.headers.get('Content-Disposition')
    file_name = disposition.split('="')[-1].split('.')[0].strip()
    return file_name


def get_mime_type_from_response(response):
    return response.headers.get('Content-Type')


def save_7z_file(response, directory):
    with SevenZipFile(io.BytesIO(response.content), mode='r') as z:
        z.extractall(directory)


def save_zip_file(response, directory):
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        z.extractall(directory)


def save_file(response, base_directory):
    mime_type = get_mime_type_from_response(response)
    file_name = get_file_name_from_response(response)
    save_directory = os.path.join(base_directory, file_name)
    create_directory(save_directory)

    if mime_type == MimeType.ZIP.value:
        save_zip_file(response, save_directory)
    elif mime_type == MimeType.SEVEN_ZIP.value:
        save_7z_file(response, save_directory)
    else:
        raise Exception(f"Unrecognized file type: {mime_type}")


def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def log_failed_game_download(game_url, console):
    with open(f"failed_game_downloads_{console}.txt", 'a+') as file:
        file.write(f"{game_url}\n")


def get_game_urls(console, first_letter, last_letter):
    print(f"Retrieving game urls for {console} games...")

    game_urls = []
    page_urls = []
    base_url = 'https://vimm.net/vault'

    for letter in [chr(x) for x in range(ord(first_letter), ord(last_letter) + 1)]:
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


def remove_blocked_game_ids(game_ids, blocked_game_ids):
    return [x for x in game_ids if x not in blocked_game_ids]


def get_game_ids_from_urls(game_urls, console):
    print('Retrieving game ids from site...')

    game_id_regex = r'var allMedia = \[{"ID":(\d+),'
    game_ids = []

    # Find all game ids
    current_game_num = 1
    for game_url in game_urls:
        try:
            time.sleep(0.5)
            page_html = requests.get(game_url).text
            game_id = re.search(game_id_regex, page_html).group(1)
            game_ids.append(game_id)
            game_id_to_url[game_id] = game_url
            print(f"game {current_game_num}/{len(game_urls)}\turl: {game_url}\tgame id: {game_id}")
        except Exception as err:
            print(f"FAILURE TO FIND GAME ID FOR game {current_game_num}/{len(game_urls)}, url: {game_url}")
            print(f"ERROR: {err}")
            log_failed_game_download(game_url, console)
        finally:
            current_game_num += 1

    return game_ids


def download_game(game_id, directory, console):
    download_url = f"{get_base_url(console)}/download/?mediaId={game_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0',
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
        warnings.warn(f"Failed to download game with game id {game_id}, url: {game_id_to_url.get(game_id)}")
        warnings.warn(f"Status code: {response.status_code}")
        warnings.warn(f"Reason: {response.reason}")
        log_failed_game_download(game_id_to_url[game_id], console)
    else:
        save_file(response, directory)
        print('Finished\n')


def get_current_time():
    return datetime.now().strftime('%b %d %I:%M:%S %p')


def download_games(game_ids, directory, console):
    print(f"Beginning download on {len(game_ids)} games\n")
    current_game_num = 1
    for game_id in game_ids:
        print(f"({current_game_num}/{len(game_ids)}) - game id: {game_id} - time: {get_current_time()}")
        download_game(game_id, directory, console)
        current_game_num += 1


def cache_game_ids(game_ids, console):
    json_data = json.dumps(game_ids)
    with open(f"cached_game_ids_{console}.json", 'w') as file:
        file.write(json_data)


def get_cached_game_ids(console):
    try:
        with open(f"cached_game_ids_{console}.json", 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return None


def filter_game_ids(game_ids, blocked_game_ids, first_game_id):
    if first_game_id is not None:
        index = game_ids.index(first_game_id)
        game_ids = game_ids[index:]

    return remove_blocked_game_ids(game_ids, blocked_game_ids)


def get_game_ids(first_letter, last_letter, console, blocked_game_ids, first_game_id):
    if get_cached_game_ids(console) is None:
        print(f"No cached game ids found for {console}")
        game_urls = get_game_urls(console, first_letter, last_letter)
        game_ids = get_game_ids_from_urls(game_urls, console)
        cache_game_ids(game_ids, console)
    else:
        print(f"Using cached game ids for {console}")
        game_ids = get_cached_game_ids(console)

    return filter_game_ids(game_ids, blocked_game_ids, first_game_id)


@click.command()
@click.option('-s', '--start', default='A', help='Letter of the alphabet to start on', )
@click.option('-e', '--end', default='Z', help='Letter of the alphabet to end on')
@click.option('-d', '--directory', help='Directory to store games in')
@click.option('-g', '--first-game-id', help='First game id to download')
@click.option('-c', '--console', required=True, help='Console to download game for',
              type=click.Choice(['xbox', 'ps1', 'ps2', 'ps3', 'nes', 'snes', 'n64', 'gc']))
def main(start, end, directory, first_game_id, console):
    # Configuration
    first_letter = start
    last_letter = end
    console = get_console_from_cli_option(console)
    download_directory = get_default_directory(console) if directory is None else directory
    blocked_game_ids = ['29']

    # Download games
    create_directory(download_directory)
    game_ids = get_game_ids(first_letter, last_letter, console, blocked_game_ids, first_game_id)
    download_games(game_ids, download_directory, console)

    # We are done :)
    print('Finished task')


if __name__ == "__main__":
    main()
