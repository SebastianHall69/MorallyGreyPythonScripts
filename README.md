# MorallyGreyPythonScripts
Like, Python scripts that are morally grey, obviously

## Scripts


### download_script.py
This script is used to automate downloading game roms from an archive website. For downloads that fail, they will be logged in a `failed_game_downloads.txt` file. Please be respectful to the site owners do not remove the sleep / wait time between downloads.

This script supports:
- Selecting which console you want game ROMS for
- Setting the download path for your files
- Downloads of `zip` or `7z` files. Others can be added pretty easily

### rename_script.py
Given a directory, it will iterate over all files in that directory and attempt to rename thoes files according to a regex pattern / replace text that you can set up. This script needs some work, I only used it once. I'll make it better when I use it next time. This is useful for bulk removing region / version info from game files. E.g. `some_game_xxx (USA, JPN) (Ver 1.1).iso` --> `some_game_xxx.iso`

### delete_resources.py
Iterates recursively through a directory and deletes all `_resources` folders. I think I used this for removing old xbmc4gamers artwork at some point.
