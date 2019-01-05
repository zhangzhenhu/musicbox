#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# 
#
"""
模块用途描述

Authors: zhangzhenhu(acmtiger@gmail.com)
Date:    2019/1/3 12:37
"""
import sys
import argparse
from NEMbox.api import NetEase
import taglib
import os
import pprint
import sqlite3
from sqlitedict import SqliteDict
from datetime import datetime
import json
import requests
import logging
import shutil

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


def save_album_nfo(save_path, info):
    nfo_path = os.path.join(save_path, 'album.nfo')
    with open(nfo_path, 'w') as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
        fh.write('<album>\n')
        fh.write('<title>%(title)s</title>\n' % info)
        fh.write('<artistdesc>%(artistdesc)s</artistdesc>\n' % info)
        fh.write('<year>%(year)s</year>\n' % info)
        for pos, song in enumerate(info['tracks']):
            fh.write("""<track>\n""")
            fh.write('<wangyiTrackID>%s</wangyiTrackID>\n' % song['id'])
            fh.write('<title>%s</title>\n' % song['name'])
            fh.write("<position>%d</position>\n" % (pos + 1))
            # fh.write('<duration>12:50</duration>')
            fh.write('</track>\n')
        fh.write('<releasetype>album</releasetype>\n')
        fh.write('</album>\n')


def save_artist_nfo(save_path, info):
    nfo_path = os.path.join(save_path, 'artist.nfo')
    with open(nfo_path, 'w') as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
        fh.write('<artist>\n')
        fh.write('<name>%(name)s</name>\n' % info)
        fh.write('<wangyiTrackID>%s</wangyiTrackID>\n' % info['id'])
        fh.write('<biography>%(artistdesc)s</biography>\n' % info)
        fh.write('<year>%(year)s</year>\n' % info)
        for pos, album in enumerate(info['albums']):
            fh.write("""<album>\n""")
            fh.write('<title>%s</title>\n' % album['title'])
            fh.write("<year>%d</year>\n" % (pos + 1))
            # fh.write('<duration>12:50</duration>')
            fh.write('</album>\n')
        fh.write('</album>\n')


def get_artist_set_from_tag(tags):
    artists_set = set()
    for a in tags['ARTIST']:
        artists_set.update(a.split(','))
        artists_set.update(a.split('/'))
        artists_set.update(a.split('，'))
        artists_set.update(a.split('；'))
        artists_set.update(a.split(';'))
        artists_set.update(a.split(' '))
    return artists_set


def get_match_song(local_song, net_songs):
    local_artists_set = get_artist_set_from_tag(local_song.tags)
    local_name_lower = local_song.tags['ARTIST'][0].lower().strip()
    for net_song in net_songs:
        id = net_song['id']
        name = net_song['name']
        duration = net_song['duration']
        if name != local_song.tags['TITLE'][0]:
            continue
        # if local_name_lower == '群星':
        #     return net_song
        if local_name_lower == net_song['artists'][0]['name'].lower().strip():
            return net_song

        net_artists_set = {a['name'].strip() for a in net_song['artists']}
        if local_artists_set == net_artists_set:
            return net_song

    return None


def get_track_number_from_album(song_id, album):
    i = 1
    for al in album:
        if al['id'] == song_id:
            return i
        i += 1
    return None


def save_tag(song_path, update_tag):
    song = taglib.File(song_path)
    for key in update_tag.keys():
        if key.upper() in song.tags:
            del song.tags[key.upper()]
    song.tags.update(update_tag)
    song.save()


def save_lrc(song_path, lrc):
    path = song_path.rsplit('.', 1)[0]
    lrc_path = path + '.lrc'
    with open(lrc_path, 'w') as fh:
        fh.write('\n'.join(lrc))


def is_supported(filename):
    for suffix in ['.flac', '.ape']:
        if filename.endswith(suffix):
            return True
    return False


def download_img(url, save_path, filename):
    response = requests.get(url)
    if not response.ok:
        logging.warning("download_img_failed", url)
        return
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    ct = response.headers.get('content-type')
    if 'image' not in ct:
        logging.warning("download_img_content-type_error", url, ct)
        return
    if 'png' in ct:
        suffix = 'png'
    elif 'jpg' in ct:
        suffix = 'jpg'
    else:
        suffix = ct.split('/')[-1]

    file_path = os.path.join(save_path, filename + '.' + suffix)
    with open(file_path, 'wb') as fh:
        fh.write(response.content)
    return


def copy_file(src, dest):
    with open(src, 'rb') as fr:
        with open(dest, 'wb') as fw:
            fw.write(fr.read())


g_song_db = None
g_artist_db = None
g_album_db = None

g_log_file = open("log.err", 'a')


def main(options):
    global g_song_db, g_artist_db, g_album_db, g_log_file
    g_song_db = SqliteDict('./songs.sqlite', autocommit=True, tablename='song')
    g_artist_db = SqliteDict('./songs.sqlite', autocommit=True, tablename='artist')
    g_album_db = SqliteDict('./songs.sqlite', autocommit=True, tablename='album')

    # local_song_path = '/Users/zhangzhenhu/Music/无损音乐/一人一首成名曲8/CD8'
    local_song_path = '/Users/zhangzhenhu/Music/无损音乐/无损单曲集合'
    # local_song_path = '/Volumes/音乐/无损单曲集合'
    # process(os.path.join(local_song_path, '一千零一个愿望-4 IN LOVE.ape'))
    # return
    for filename in os.listdir(local_song_path):
        if not is_supported(filename):
            continue
        process(os.path.join(local_song_path, filename))

    g_log_file.close()


def process(local_song_path, save_path="/Users/zhangzhenhu/Music/mymusic"):
    global g_log_file
    net = NetEase()
    local_song = taglib.File(local_song_path)
    print("")
    print("========本地歌曲=======")
    # pprint.pprint(local_song.tags)
    if 'TITLE' not in local_song.tags or 'ARTIST' not in local_song.tags:
        return
    print(local_song.tags['TITLE'], local_song.tags['ARTIST'], local_song.tags.get('ALBUM', ""))
    title = local_song.tags['TITLE'][0]

    song_result = net.search(keywords=title, stype=1)
    if song_result is None or 'songs' not in song_result:
        print("net_song_not_found", local_song_path, file=g_log_file)
        return

    net_song = get_match_song(local_song, song_result['songs'])

    # pprint.pprint(net_song)

    if net_song is None:
        print("net_song_not_match", local_song_path, file=g_log_file)
        return
    print("----------网易歌曲--------")
    print(net_song['id'], net_song['name'], net_song['album']['name'],
          ','.join([x['name'] for x in net_song['artists']]))
    g_song_db[net_song['id']] = net_song
    # 歌手id，只选取第一个
    artist_id = net_song['artists'][0]['id']
    artist_name = net_song['artists'][0]['name']

    # 获取歌手信息
    artist_json = net.get_artist_desc(artist_id)

    # print(artist_desc)
    if artist_json and artist_json['code'] == 200:
        artist_info = artist_json['artist']
        g_artist_db[artist_id] = artist_info
        artist_img = artist_info['img1v1Url']
        artist_pic = artist_info['picUrl']
    else:
        print("artist_not_found", local_song_path, file=g_log_file)
        return

    # 歌曲所属专辑
    album_info = net_song['album']  # 包括字段 id name size artist
    album_name = album_info['name']
    # print(album)
    # 获取歌曲信息
    # print("========歌曲信息=======")
    song_info = net.songs_detail([net_song['id']])[0]
    album_pic = song_info['al']['picUrl']  # 专辑的图片

    # print(song_lyric)

    # 获取专辑信息
    album_tracks = net.album(album_info['id'])
    g_album_db[album_info['id']] = album_tracks

    #
    net_tags = {
        "ALBUM": album_info['name'],

    }
    if artist_info['briefDesc']:
        net_tags['comment'] = artist_info['briefDesc']
    # 专辑发布时间
    if 'publishTime' in album_info:
        publish_time = datetime.fromtimestamp(album_info['publishTime'] // 1000)
        net_tags['date'] = publish_time.strftime("%Y-%m-%d")
        net_tags['year'] = publish_time.strftime("%Y")
        album_year = publish_time.strftime("%Y")
    else:
        album_year = None

    # 专辑歌曲数量，以及本歌曲在第几
    if len(album_tracks):
        net_tags['TRACKTOTAL'] = str(len(album_tracks))
        track_number = get_track_number_from_album(net_song['id'], album_tracks)
        if track_number is not None:
            net_tags['TRACKNUMBER'] = str(track_number)

    # 获取歌词
    song_lyric = net.song_lyric(net_song['id'])

    net_tags['Lyrics'] = '\n'.join(song_lyric),
    net_tags['wangyi'] = [json.dumps({'song_id': net_song['id'],
                                      'artist_id': artist_id,
                                      'ablum_id': album_info['id'],
                                      })]

    new_artist_path = os.path.join(save_path, artist_name)
    if album_name is not None:
        new_album_path = os.path.join(new_artist_path, album_name)
    else:
        new_album_path = new_artist_path
    if album_year is not None:
        new_album_path = new_album_path
    # if not os.path.exists(new_album_path):
    os.makedirs(new_album_path, exist_ok=True)

    new_song_path = os.path.join(new_album_path, os.path.split(local_song_path)[-1])
    # print(new_song_path)
    # 保存歌词
    save_lrc(new_song_path, song_lyric)

    # 复制音频文件
    if not os.path.exists(new_song_path):
        # copy_file(local_song_path, new_song_path)
        shutil.move(local_song_path, new_song_path)

    download_img(artist_pic, new_artist_path, 'folder')
    download_img(artist_pic, new_artist_path, 'fanart')
    download_img(album_pic, new_album_path, 'cover')

    save_tag(new_song_path, net_tags)

    # 生成nfo文件
    album_nfo = {
        'title': album_info['name'],
        'artistdesc': artist_info['briefDesc'],
        'year': album_year,
        'tracks': album_tracks
    }
    save_album_nfo(new_album_path, album_nfo)
    # pprint.pprint(net.search(keywords="那英", stype=100))
    # pprint.pprint(album_desc[0])
    print("")


if __name__ == "__main__":

    parser = init_option()
    options = parser.parse_args()

    if options.input:

        options.input = open(options.input)
    else:
        options.input = sys.stdin
    main(options)
