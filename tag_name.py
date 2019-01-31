#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# 
#
"""
模块用途描述

Authors: zhangzhenhu(acmtiger@gmail.com)
Date:    2019/1/5 22:24
"""
import sys
import argparse
import os
import glob
import taglib

__version__ = 1.0


def init_option():
    """
    初始化命令行参数项
    Returns:
        OptionParser 的parser对象
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", dest="input",
                        help=u"输入文件；默认标准输入设备")
    parser.add_argument("-o", "--output", dest="output",
                        help=u"输出文件；默认标准输出设备")
    return parser


def get_lrc(filepath=""):
    # ori_lrc = ori_name.replace('.ape', 'lrc')
    if os.path.exists(filepath.replace('.flac', '.lrc')):
        return filepath.replace('.flac', '.lrc')
    if os.path.exists(filepath.replace('.flac', '.lyric')):
        return filepath.replace('.flac', '.lyric')


def main(options):
    files = glob.glob('/Users/zhangzhenhu/Music/mymusic/*/*/*.lyric')

    # print(files[:10])
    for filepath in files:
        # song = taglib.File(filepath)
        # ori_name = os.path.basename(filepath)
        # if 'TITLE' not in song.tags:
        #     continue
        # title = song.tags['TITLE'][0]
        # artist = song.tags['ARTIST'][0]
        #
        # new_name = "%s-%s.flac" % (title, artist)
        # if new_name == ori_name:
        #     continue
        # dir_path = os.path.dirname(filepath)

        # old_lrc = get_lrc(filepath)
        # new_lrc = os.path.join(dir_path, new_name.replace('.flac', '.lrc'))
        # new_song = os.path.join(dir_path, new_name)

        # print(old_lrc, new_lrc)
        # if old_lrc is not None:
        #     os.rename(old_lrc, new_lrc)
        # print(filepath, new_song)
        # os.rename(filepath, new_song)
        print(filepath)
        # os.rename(filepath,filepath.replace('.lyric','.lrc'))

if __name__ == "__main__":

    parser = init_option()
    options = parser.parse_args()

    if options.input:

        options.input = open(options.input)
    else:
        options.input = sys.stdin
    main(options)
