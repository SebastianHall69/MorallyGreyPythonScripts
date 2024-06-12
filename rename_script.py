import os
import re


console = 'PS1'
path = f"games/{console}" # Set path to iterate over files
filter_text = '\+' # Choose which text to replace
replace_text = ' ' # Choose text that it should be replaced with

s = set()


for (dirpath, dirnames, filenames) in os.walk(path):
    for filename in filenames:
        if re.search(filter_text, filename):
            new_filename = re.sub(filter_text, replace_text, filename)
            #print(filename, ' ---> ', new_filename)
            if new_filename in s:
                print(f"Collision with {filename}")
            s.add(new_filename)
            os.rename(f"{path}/{filename}", f"{path}/{new_filename}")
