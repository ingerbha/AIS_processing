""" This is a small script to remove duplicate Cases and their corresponding _info files"""

from collections import defaultdict
import hashlib
import os
import sys


def chunk_reader(fobj, chunk_size=1024):
    """Generator that reads a file in chunks of bytes"""
    while True:
        chunk = fobj.read(chunk_size)
        if not chunk:
            return
        yield chunk


def get_hash(filename, first_chunk_only=False, hash=hashlib.sha1):
    hashobj = hash()
    file_object = open(filename, 'rb')

    if first_chunk_only:
        hashobj.update(file_object.read(1024))
    else:
        for chunk in chunk_reader(file_object):
            hashobj.update(chunk)
    hashed = hashobj.digest()

    file_object.close()
    return hashed


def check_for_duplicates(paths, hash=hashlib.sha1):
    
    removed_files = False

    hashes_by_size = defaultdict(list)  # dict of size_in_bytes: [full_path_to_file1, full_path_to_file2, ]
    hashes_on_1k = defaultdict(list)  # dict of (hash1k, size_in_bytes): [full_path_to_file1, full_path_to_file2, ]
    hashes_full = {}   # dict of full_file_hash: full_path_to_file_string

    full_file_list = []

    for path in paths:
        for dirpath, dirnames, filenames in os.walk(path):

            # get all files that have the same size - they are the collision candidates
            for filename in filenames:

                full_file_list.append(os.path.join(dirpath, filename))

                full_path = os.path.join(dirpath, filename)
                try:
                    # if the target is a symlink (soft one), this will 
                    # dereference it - change the value to the actual target file
                    full_path = os.path.realpath(full_path)
                    file_size = os.path.getsize(full_path)
                    hashes_by_size[file_size].append(full_path)
                except (OSError,):
                    # not accessible (permissions, etc) - pass on
                    continue


    # For all files with the same file size, get their hash on the 1st 1024 bytes only
    for size_in_bytes, files in hashes_by_size.items():
        if len(files) < 2:
            continue    # this file size is unique, no need to spend CPU cycles on it

        for filename in files:
            try:
                small_hash = get_hash(filename, first_chunk_only=True)
                # the key is the hash on the first 1024 bytes plus the size - to
                # avoid collisions on equal hashes in the first part of the file
                # credits to @Futal for the optimization
                hashes_on_1k[(small_hash, size_in_bytes)].append(filename)
            except (OSError,):
                # the file access might've changed till the exec point got here 
                continue

    # For all files with the hash on the 1st 1024 bytes, get their hash on the full file - collisions will be duplicates
    for __, files_list in hashes_on_1k.items():
        if len(files_list) < 2:
            continue    # this hash of fist 1k file bytes is unique, no need to spend cpy cycles on it

        for filename in files_list:
            try: 
                full_hash = get_hash(filename, first_chunk_only=False)
                duplicate = hashes_full.get(full_hash)
                if duplicate:
                    #print("Duplicate found: {} and {}".format(filename, duplicate))

                    if not 'Case' in duplicate:
                        continue

                    if 'sec-' in duplicate or '_info' in duplicate:
                        continue

                    code = duplicate.replace(".csv","")[-5:]
                    print("Duplicate found code: %s" % format(code))
                    
                    files_to_delete = [s for s in full_file_list if code in s]
                    print("Files to delete:", files_to_delete)

                    for delete_file in files_to_delete:
                        print("Deleting file: ", delete_file)
                        os.remove(delete_file)
                        removed_files = True

                else:
                    hashes_full[full_hash] = filename
            except (OSError,):
                # the file access might've changed till the exec point got here 
                continue
    return removed_files

if __name__ == "__main__":
    files_left = True

    if sys.argv[1:]:
        while files_left:
            files_left = check_for_duplicates(sys.argv[1:])
    else:
        print("Please pass the paths to check as parameters to the script")
        if __name__ == "__main__":
            if sys.argv[1:]:
                check_for_duplicates(sys.argv[1:])
            else:
                print("Please pass the paths to check as parameters to the script")
