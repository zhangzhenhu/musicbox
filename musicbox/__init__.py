import taglib
import abc
from tqdm import tqdm
import os
import requests
from urllib.request import urlopen

import logging

"""
https://www.bzqll.com/2018/10/39.html
"""
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger("Download")


# logger.addHandler(logging.StreamHandler)

def save_album_nfo(save_path, info):
    """

    :param save_path:
    :param info:  title artistdesc year
    :return:
    """
    nfo_path = os.path.join(save_path, 'album.nfo')
    with open(nfo_path, 'w') as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
        fh.write('<album>\n')
        fh.write('<title>%(title)s</title>\n' % info)
        fh.write('<artistdesc>%(artistdesc)s</artistdesc>\n' % info)
        fh.write('<year>%(year)s</year>\n' % info)
        for pos, song in enumerate(info.get('tracks',[])):
            fh.write("""<track>\n""")
            fh.write('<wangyiTrackID>%s</wangyiTrackID>\n' % song.get('netease_id', ""))
            fh.write('<QQTrackID>%s</QQTrackID>\n' % song.get('qq_id', ''))
            fh.write('<QQTrackMID>%s</QQTrackMID>\n' % song.get('qq_mid', ''))
            fh.write('<title>%s</title>\n' % song['name'])
            fh.write("<position>%d</position>\n" % (pos + 1))
            # fh.write('<duration>12:50</duration>')
            fh.write('</track>\n')
        fh.write('<releasetype>album</releasetype>\n')
        fh.write('</album>\n')


def update_song_metadata(song_path, update_tag):
    song = taglib.File(song_path)
    for key in update_tag.keys():
        if key.upper() in song.tags:
            del song.tags[key.upper()]
    song.tags.update(update_tag)
    song.save()


class Platform:

    def get_song_by_id(self, id):
        pass

    def get_artist_by_id(self, id):
        pass

    def get_album_by_id(self, id):
        pass

    def get_playlist_by_url(self, url):
        pass

    def get_playlist_by_id(self, id):
        pass

    def search(self, keyword):
        pass

    def download_song_by_id(self, id):
        pass


class PlayList(dict):

    @abc.abstractmethod
    def get_songs(self):
        pass


class Artist(dict):
    pass


class Album(dict):
    pass


class Song(dict):
    pass


def download_from_url(url, dst, headers=None, min_size=1):
    """
    @param: url to download file
    @param: dst place to put the file
    """
    global logger
    # contetn_size = int(urlopen(url).info().get('Content-Length', -1))

    """
    print(urlopen(url).info())
    # output
    Server: AliyunOSS
    Date: Tue, 19 Dec 2017 06:55:41 GMT
    Content-Type: application/octet-stream
    Content-Length: 29771146
    Connection: close
    x-oss-request-id: 5A38B7EDCE2B804FFB1FD51C
    Accept-Ranges: bytes
    ETag: "9AA9C1783224A1536D3F1E222C9C791B-6"
    Last-Modified: Wed, 15 Nov 2017 10:38:33 GMT
    x-oss-object-type: Multipart
    x-oss-hash-crc64ecma: 14897370096125855628
    x-oss-storage-class: Standard
    x-oss-server-time: 4
    """
    filename = os.path.basename(dst)
    first_byte = 0
    if os.path.exists(dst):
        file_size = os.path.getsize(dst)
    else:
        file_size = 0
    # if first_byte >= file_size:
    #     return file_size
    # header = {"Range": "bytes=%s-%s" % (first_byte, file_size)}
    req = requests.get(url, headers=headers, stream=True)

    if not req.ok:
        logger.error('%s 下载错误 %s %s' % (filename, req.status_code, req.reason))
        return -1

    content_size = int(req.headers.get('Content-Length', -1))
    if content_size < min_size:  # 1000 * 1000 * 5:
        req.close()
        logger.info('%s 网络文件太小', filename, content_size)
        return 0
    if file_size >= content_size:
        req.close()
        logger.info('%s 文件已存在', filename, )
        return 0

    pbar = tqdm(
        total=content_size, initial=0,
        unit='B', unit_scale=True, desc=filename)

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with(open(dst, 'wb')) as f:
        for chunk in req.iter_content(chunk_size=10240):
            if chunk:
                f.write(chunk)
                pbar.update(10240)
        f.close()
    pbar.close()
    req.close()

    return content_size
