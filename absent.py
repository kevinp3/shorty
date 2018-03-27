#! /usr/bin/env python3
"""
Determine which files of a folder are not present in another collection of folders.

Use case:
I have some folders of photos - my "library"
I import the photos from my "camera".
I move the new photos around in the library, and possibly rename them.
I delete some of the photos on my camera, but not all.
I take new photos on the camera.
Now I want to import only the new ones....

Note that this applies to other situations:
I might have a series of backup CDs (remember those?) that I want to combine.
Various reorganizations of my music library
....

For ease of documentation, I'll refer to camera and library

As an extra assistance, by specifying --rmdups, I will delete files on the "camera"
that are already accounted for in the library.  After doing the rmdups, all remaining
files on the camera can be copied to the library without duplication.

Plan of attack:
I have 50k+ files in my library, so its evaluation performance should be good :-)
Fewer files on the camera.

Thinking about the files on the camera, because of compression, mostly the files
are different lengths.  If a camera file has length X and the library has *no* file
of length X, then the camera file is "new".

If the library does have one/some files of length X, I need to examine more closely.
I'll use "filecmp" to test each of those library files against the camera one.

The pre-check using lengths is an example of a Bloom Filter, https://en.wikipedia.org/wiki/Bloom_filter
"""

import os
import filecmp
import argparse


def survey_library(folders):
    """Build a dictionary keyed by file length.
        length: list of files of that length
    """
    res = {}
    cnt = 0
    for folder in folders:
        for dpath, dirs, fnames in os.walk(folder):
            for base_fname in fnames:
                cnt += 1
                base_fpath = os.path.join(dpath, base_fname).replace('\\', '/')
                try:
                    flen = os.stat(base_fpath).st_size
                    fpaths = res.setdefault(flen, [])
                    fpaths.append(base_fpath)
                except (FileNotFoundError, IOError):
                    # If it won't stat, don't consider it.  But report...
                    print("Error stat-ing:", base_fpath)
                    pass

    # just out of curiosity, how good it my key choice?
    # It would be perfect if no length has more than one file.
    dups = 0
    for fpaths in res.values():
        if len(fpaths) > 1:
            dups += 1
    print("nFiles:", cnt)
    print("nLengths:", len(res))
    print("Lengths with more than 1 file:", dups)

    return res


def locate(tgt_fpath, survey):
    """Given a fpath on the "camera", determine if present in the survey of the library.
        I could just return True/False, but returning the library fpath/None might be more interesting.

        filecmp.cmp has a fast sanity check mode, and a full test.
    """
    flen = os.stat(tgt_fpath).st_size
    fpaths = survey.get(flen, ())
    if not fpaths:
        return None

    for fbase_path in fpaths:
        # print('  '*5, tgt_fpath, fbase_path)
        if not filecmp.cmp(tgt_fpath, fbase_path, shallow=True):
            continue        # early reject, try other candidates
        if filecmp.cmp(tgt_fpath, fbase_path, shallow=False):
            # identically equal
            return fbase_path

    return None


def main(camera_folder, library_folders, rmdups=False):
    surveyed = survey_library(library_folders)
    absent = []
    cnt = 0

    not_needed = []
    for i_path, i_dirnames, i_filenames in os.walk(camera_folder):
        for fname in i_filenames:
            cnt += 1
            fpath = os.path.join(i_path, fname).replace('\\', '/')
            found = locate(fpath, surveyed)
            if found:
                print(fpath, "==>", found)
                not_needed.append(fpath)
            else:
                absent.append(fpath)

    print('%d needed to import out of %d total' % (len(absent), cnt))
    for fpath in sorted(absent):
        print('Missing:', fpath)
    print('%d needed to import out of %d total' % (len(absent), cnt))

    if rmdups:
        for fpath in not_needed:
            print('Deleting:', fpath)
            try:
                os.remove(fpath)
            except Exception as e:
                print("    Error in deletion:", fpath, e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Determine which files in the first folder (camera) are not present in the (library) folders.')
    parser.add_argument('new_folder',
                        help='camera folder to evaluate')
    parser.add_argument('dest_folders', nargs='*',
                        help='library folders to evaluate')
    parser.add_argument('--rmdups', action='store_true',
                        help='DELETE files in the camera folder which are already in the library (but may be named differently).')

    args = parser.parse_args()
    main(args.new_folder, args.dest_folders, args.rmdups)


