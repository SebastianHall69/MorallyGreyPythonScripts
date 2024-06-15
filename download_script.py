import io
import os.path

import click
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


def create_download_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def log_failed_game_download(game_url):
    with open('failed_game_downloads.txt', 'a+') as file:
        file.write(f"{game_url}\n")


def get_game_urls(console, first_letter, last_letter):
    print('Retrieving game urls...')

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


def get_game_ids(game_urls, blocked_game_ids, first_game_id_to_download):
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
            log_failed_game_download(game_url)
        finally:
            current_game_num += 1

    # Trim set of game ids
    if first_game_id_to_download is not None:
        index = game_ids.index(first_game_id_to_download)
        game_ids = game_ids[index:]
    game_ids = remove_blocked_game_ids(game_ids, blocked_game_ids)

    return game_ids


def download_game(game_id, directory):
    download_url = f"https://download3.vimm.net/download/?mediaId={game_id}"
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
        warnings.warn(f"Failed to download game with game id {game_id}, url: {game_id_to_url.get(game_id)}")
        warnings.warn(f"Status code: {response.status_code}")
        warnings.warn(f"Reason: {response.reason}")
        log_failed_game_download(game_id_to_url[game_id])
    else:
        save_file(response, directory)
        print('Finished\n')


def download_games(game_ids, directory):
    for game_id in game_ids:
        print(f"Downloading game id {game_id}")
        download_game(game_id, directory)


@click.command()
@click.option('-s', '--start', default='A', help='Letter of the alphabet to start on', )
@click.option('-e', '--end', default='Z', help='Letter of the alphabet to end on')
@click.option('-d', '--directory', default='games', help='Directory to store games in')
@click.option('-g', '--first-game-id', help='First game id to download')
@click.option('-c', '--console', default='n64', required=True, help='Console to download game for', type=click.Choice(['xbox', 'ps1', 'ps2', 'ps3', 'nes', 'snes', 'n64', 'gc']))
def main(start, end, directory, first_game_id, console):
    # Configuration
    first_letter = start
    last_letter = end
    console = get_console_from_cli_option(console)
    game_directory = get_default_directory(console) if directory is None else directory
    blocked_game_ids = ['29']

    # Create game directory
    create_download_directory(game_directory)

    # Find game urls
    print(f"Querying game id's for {console} games...")
    game_urls = get_game_urls(console, first_letter, last_letter)

    # Find game ids
    print('Retrieving game ids...')
    game_ids = get_game_ids(game_urls, blocked_game_ids, first_game_id)

    # Download games
    print(f"Beginning download on {len(game_ids)} games")
    download_games(game_ids, game_directory)

    # We are done :)
    print("Finished task")


if __name__ == "__main__":
    main()
