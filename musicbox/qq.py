#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# 
#
"""
模块用途描述

Authors: zhangzhenhu(acmtiger@gmail.com)
Date:    2019/1/5 10:39
"""
import sys
from musicbox import Platform, PlayList, Song, Album, Artist
from musicbox import update_song_metadata, download_from_url, save_album_nfo
import requests
import os
import json
import random
import time
import base64
import logging

logger = logging.getLogger("QQMusic")
# logger.addHandler(logging.StreamHandler)

headers = {
    # 'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 5.1.1; vivo x5s l Build/LMY48Z)',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
    'Referer': 'https://y.qq.com/portal/profile.html'}

"""
songType  String 说明： 歌曲类型 
    可选值：
    0 - 库内歌曲
    1 - 库外歌曲
    111 - 低品质
    112 - 铃声
    113 - 伴奏
    
alertid	String	
    说明： 受阻提示语ID

msgid	String	
    说明： msg提示语id

interval	String	
    说明： 总时长（秒数） 
    
       
"""


def parse_mid_from_url(url):
    return url.split('?', 1)[0].rsplit('/', 1)[-1].split('.')[0]


class QQArtist(Artist):
    pass

    @property
    def mid(self):
        return self['mid']

    def do_extend_info(self):
        return self

    @property
    def img_url(self):
        # "https://y.gtimg.cn/music/photo_new/T001R300x300M000003Hk8ck2WMjKV.jpg?max_age=2592000"
        return "https://y.gtimg.cn/music/photo_new/T001R300x300M000{}.jpg?max_age=2592000".format(self.mid)

    def save_img(self, save_path):
        img_path = os.path.join(save_path, 'folder.jpg')
        download_from_url(self.img_url, img_path)


class QQAlbum(Album):

    @property
    def mid(self):
        return self['mid']

    def do_extend_info(self):
        """
        下载更多的信息字段
        :return:
        """
        url = 'https://shc.y.qq.com/v8/fcg-bin/fcg_v8_album_info_cp.fcg'
        query = {"albummid": self.mid,  # 专辑mid
                 "g_tk": "5381",
                 "jsonpCallback": "getAlbumInfoCallback",
                 "loginUin": "0",
                 "hostUin": "0",
                 "format": "jsonp",
                 "inCharset": "utf8",
                 "outCharset": "utf-8",
                 "notice": "0",
                 "platform": "yqq",
                 "needNewCode": "0",
                 }

        url += "?" + '&'.join(["%s=%s" % (k, v) for k, v in query.items()])

        r = requests.get(url=url, headers=headers)
        text = r.text
        s = text.strip().lstrip('getAlbumInfoCallback(').rstrip(')')
        json_loads = json.loads(s)
        if 'data' not in json_loads:
            pass
            return self
        self.update(json_loads['data'])
        return self

    @property
    def img_url(self):
        return "https://y.gtimg.cn/music/photo_new/T002R300x300M000{}.jpg?max_age=2592000".format(self.mid)

    def save_img(self, save_path):
        img_path = os.path.join(save_path, 'cover.jpg')
        download_from_url(self.img_url, img_path)

    def save_nfo(self, save_path):
        # 生成nfo文件
        album_nfo = {
            'title': self['name'],
            'artistdesc': self['desc'],
            'year': self['aDate'].split('-')[0],
        }
        if self.get('list', []):
            album_nfo['tracks'] = [
                {"qq_id": s['songid'],
                 'qq_mid': s['songmid'],
                 'name': s['songname']
                 } for s in self.get('list', []) if s]

        save_album_nfo(save_path, album_nfo)


class QQSong(Song):
    """

    """

    def __init__(self, *args, **kwargs):
        super(QQSong, self).__init__(*args, **kwargs)
        self.guid = int(random.random() * 2147483647) * int(time.time() * 1000) % 10000000000
        self.guid = '1234567890'
        self._vkey = None
        self.album = None
        self.artists = None

    @property
    def name(self):
        return self.get('songname') or self.get('name')

    @property
    def albumid(self):
        return self.get('albumid') or self.get('album', {}).get('id')

    @property
    def albummid(self):
        return self.get('albummid') or self.get('album', {}).get('mid')

    @property
    def albumname(self):
        return self.get('albumname') or self.get('album', {}).get('name')

    @property
    def id(self):
        return self.get('songid') or self.get('id')

    @property
    def mid(self):
        return self.get('songmid') or self.get('mid')

    @property
    def url(self):
        """
        歌曲在 QQ 音乐 web 版中的页面链接
        :return:
        """
        return 'https://y.qq.com/n/yqq/song/{}.html'.format(self.mid)

    @property
    def lyric_url(self):
        return 'https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg?g_tk=753738303&songmid=' + self.mid

    def get_lyric(self):
        """
        获得歌词和翻译（如果有的话）
        :return: { lyric: ..., trans: ...}
        """
        if self.get('lyric', None) is not None:
            return self['lyric']

        lrc_url = self.lyric_url
        headers = {
            'Referer': 'https://y.qq.com/portal/player.html',
            'Cookie': 'skey=@LVJPZmJUX; p',  # 此处应该对应了 g_tk 和 skey 的关系，因此需要提供 skey 参数才可以获取
            # 我已经退出登录这个 skey 了，因此不会有安全问题的
        }
        resp = requests.get(lrc_url, headers=headers)
        lrc_dict = json.loads(resp.text[18:-1])
        data = {'lyric': '', 'trans': ''}
        if lrc_dict.get('lyric'):
            data['lyric'] = base64.b64decode(lrc_dict['lyric']).decode()
        if lrc_dict.get('trans'):
            data['trans'] = base64.b64decode(lrc_dict['trans']).decode()
        self['lyric'] = data
        return self['lyric']

    @property
    def song_url(self):
        """
        歌曲的播放链接，每次访问生成一个新的
        :return:
        """
        filename = 'C400{}.m4a'.format(self.mid)
        return 'http://dl.stream.qqmusic.qq.com/{}?vkey={}&guid={}&fromtag=30'.format(filename, self.vkey,
                                                                                      self.guid)

    @property
    def vkey(self):
        return '1146B2D2E8D3E2E9990266B0D1476AAA4B2D058DB61EF7C98F1A6A44C3A4E2ECF8FDE15B5CE0DA8BED5048D10953F5F19F9817F6836212F4'

        if self._vkey is not None:
            return self._vkey

        url = 'https://c.y.qq.com/base/fcgi-bin/fcg_music_express_mobile3.fcg'
        filename = 'C400{}.m4a'.format(self.mid)
        params = {
            'format': 'json',
            'platform': 'yqq',
            'cid': '205361747',
            'songmid': self.mid,
            'filename': filename,
            'guid': self.guid
        }
        rst = requests.get(url, params=params)
        self._vkey = json.loads(rst.text)['data']['items'][0]['vkey']
        return self._vkey

    def get_media_link(self, media_mid):
        type_info = [['M500', 'mp3'], ['M800', 'mp3'], ["A000", 'ape'], ['F000', 'flac']]
        dl_url = 'http://streamoc.music.tc.qq.com/{prefix}{media_mid}.{type}?vkey={vkey}&guid=1234567890&uin=1008611&fromtag=8'
        dl = []
        for item in type_info:
            s_url = dl_url.format(prefix=item[0], media_mid=media_mid, type=item[1], vkey=self.vkey)
            dl.append(s_url)
        return dl

    def extend(self, mid=None):
        self.do_extend_info(mid=mid)
        self.album = QQAlbum(self['album']).do_extend_info()
        self.artists = [QQArtist(a).do_extend_info() for a in self['singer']]
        return self

    def do_extend_info(self, mid=None):
        if mid is None:
            mid = self.mid
        info_url = 'https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg?songmid={songmid}&tpl=yqq_song_detail&format=json&callback=getOneSongInfoCallback&g_tk=5381&jsonCallback=getOneSongInfoCallback&loginUin=0&hostUin=0&format=json&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq&needNewCode=0'
        url = info_url.format(songmid=mid)
        # try:
        r = requests.get(url=url, headers=headers)
        json = r.json()
        self.update(json['data'][0])
        return None

    def save_song(self, save_path, type_policy=['flac', 'ape', 'dts'], ):
        if 'file' not in self:
            self.do_extend_info()
        song_file_name = self._song_file_name()

        s_url = None
        file_type = None
        for ft in type_policy:
            _ft = 'size_' + ft
            if _ft in self['file'] and self['file'][_ft] > 10000000:
                s_url = self._get_dl_link(ft=ft)
                file_type = ft
                break

        if s_url is None:
            logger.warning('未找到合适音质的音频 %s', song_file_name)
            return -1, None

        song_file_path = os.path.join(save_path, song_file_name + '.' + file_type)
        # 下载音乐文件
        # /if os.path.exists(song_file_path):
        #     logger.warning('歌曲已存在 %s', song_file_path)
        # else:
        return download_from_url(s_url, song_file_path, headers, min_size=1000 * 1000 * 5), song_file_path
        # return

    def _song_file_name(self, filename_pattern="{name}-{artist}"):
        artist_name = self.artists[0]['name']
        song_file_name = filename_pattern.format(name=self.name,
                                                 artist=artist_name
                                                 )
        return song_file_name

    def download(self, save_path,
                 group=True,
                 ):
        artist_name = self.artists[0]['name']
        if group:
            artist_path = os.path.join(save_path, artist_name)
            album_path = os.path.join(artist_path, self.albumname)
            song_path = album_path
        else:
            song_path = save_path
        # os.makedirs(song_path, exist_ok=True)
        # media_mid = self['strMediaMid'] or self['file']['media_mid']

        song_file_name = self._song_file_name()

        logger.info('%s 下载歌曲' % song_file_name)
        ret, song_file_path = self.save_song(song_path)
        if ret < 0:
            logger.error('%s 歌曲下载失败' % song_file_name)
            return
        # 下载歌词
        logger.info('%s 下载歌词' % song_file_name)
        lyric = self.get_lyric()['lyric']
        lyric_file_path = os.path.join(song_path, song_file_name + '.lrc')
        with open(lyric_file_path, 'w') as fh:
            fh.write(lyric)
            fh.close()

        song_tags = {
            'comment': self.album['desc'],
            'date': self['time_public'],
            'genre': self.album['genre'],
            'language': self.album['lan'],
            'Lyrics': lyric,
            'qq': json.dumps({'album': self['album'],
                              'artist': self['singer'],
                              'mid': self['mid'],
                              'id': self['mid'],
                              })
        }
        # 更新歌曲metadata
        update_song_metadata(song_file_path, song_tags)

        # 下载图片
        logger.info('%s 下载专辑封面' % song_file_name)
        self.album.save_img(album_path)
        logger.info('%s 下载歌手封面' % song_file_name)
        self.artists[0].save_img(artist_path)

        self.album.save_nfo(album_path)

    def _get_dl_link(self, ft='flac'):

        # vkey = ''
        vkey = '1807FB4D65616A26F8063D4AC7DF72D63BF4ACA9CE87B1E63CB19A7472B9E577C5D3A3E2A81546DECD066194E09116E0A54DF62713C80DB9'

        media_mid = self.get('strMediaMid', None) or self['file']['media_mid']
        if ft == 'flac':
            return 'http://streamoc.music.tc.qq.com/F000{media_mid}.flac?vkey={vkey}&guid={guid}&uin=1008611&fromtag=8'.format(
                media_mid=media_mid, vkey=vkey, guid=self.guid)
        elif ft == "ape":
            return 'http://streamoc.music.tc.qq.com/A000{media_mid}.ape?vkey={vkey}&guid={guid}&uin=1008611&fromtag=8'.format(
                media_mid=media_mid, vkey=vkey, guid=self.guid)


class QQPlayList(PlayList):

    def get_songs(self):
        info_songlist = self['songlist']
        for item in info_songlist:
            # songmid = item['songmid']
            # info = get_single_info(songmid, vkey, do=False)
            # download(info, down_path)
            # songlist.append(info)
            yield QQSong(item)

    @property
    def name(self):
        # playlist_name
        return self['dissname']

    @property
    def desc(self):
        # playlist_desc
        return self['desc']

    @property
    def log(self):
        # playlist_logo =
        return self['logo']

    @property
    def songnum(self):
        return self['songnum']

    @property
    def songids(self):
        return self['songids'].split(',')


class QQMusic(Platform):
    headers = {'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 5.1.1; vivo x5s l Build/LMY48Z)',
               'Referer': 'https://y.qq.com/portal/profile.html'}

    def get_artist_by_url(self, url):
        """

        :param url:  https://y.qq.com/n/yqq/singer/003Hk8ck2WMjKV.html
        :return:
        """
        mid = parse_mid_from_url(url)
        return self.get_artist_by_mid(mid)

    def get_artist_by_mid(self, mid):
        url = "https://c.y.qq.com/v8/fcg-bin/fcg_v8_singer_track_cp.fcg"
        query = [
            'g_tk=5381',
            'loginUin=1152921504766965228',
            'hostUin=0',
            'format=json',
            'inCharset=utf8',
            'outCharset=utf-8',
            'notice=0',
            'platform=yqq.json',
            'needNewCode=0',
            'singermid=' + mid,
            'order=listen',
            'begin=0',
            'num=30',
            'songstatus=1'
        ]
        url += '?' + '&'.join(query)
        r = requests.get(url=url, headers=headers)
        data = r.json()

        for m in data['data']['list']:
            yield QQSong(m['musicData'])

    def get_song_by_url(self, url):
        """

        :param url:  https://y.qq.com/n/yqq/song/003cZo6332umkR.html
        :return:
        """
        return self.get_song_by_mid(parse_mid_from_url(url))

    def get_song_by_mid(self, mid):
        pass
        song = QQSong().extend(mid=mid)
        return song

    def get_playlist_by_url(self, url):
        pass

    def get_playlist_by_id(self, id):
        list_url = 'https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg?type=1&json=1&utf8=1&onlysong=0&disstid={playlist_id}&format=jsonp&g_tk=5381&jsonpCallback=playlistinfoCallback&loginUin=0&hostUin=0&format=jsonp&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq&needNewCode=0'
        url_format = list_url.format(playlist_id=id)
        r = requests.get(url_format, headers=headers)
        text = r.text
        s = text.lstrip('playlistinfoCallback(').rstrip(')')
        json_loads = json.loads(s)
        cdlist_info = json_loads['cdlist'][0]
        logger.info('歌单<%s>  %d songs' % (cdlist_info['dissname'], cdlist_info['songnum']))
        return QQPlayList(cdlist_info)

    def search(self, page_num, page_size, song_name):
        search_url = 'http://c.y.qq.com/soso/fcgi-bin/client_search_cp?ct=24&qqmusic_ver=1298&new_json=1&remoteplace=txt.yqq.center&t=0&aggr=1&cr=1&catZhida=1&lossless=0&flag_qc=0&p={page_num}&n={page_size}&w={song_name}&jsonpCallback=searchCallbacksong2020&format=json&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq&needNewCode=0'.format(
            page_num=page_num, page_size=page_size, song_name=song_name)
        r = requests.get(search_url, headers=headers)
        json = r.json()
        return json

    def down_by_artist(self, mid, save_path='/Users/zhangzhenhu/Music/mymusic/'):

        for song in self.get_artist_by_mid(mid):
            print("")
            song.extend()
            song.download(save_path)

    def download_by_playlist(self, id, save_path):
        playlist = qq.get_playlist_by_id(id=id)  # 我自己的
        for song in list(playlist.get_songs()):
            print("")
            song.extend()
            song.download(save_path)

    def download_song_by_mid(self, mid, save_path='/Users/zhangzhenhu/Music/mymusic/'):
        song = self.get_song_by_mid(mid)
        song.extend(mid)
        song.download(save_path)


if __name__ == "__main__":

    """
    qq 无损音乐下载网站 http://music.mzz.pub/
    vkey 可以从这个网站获取
    """
    qq = QQMusic()

    # qq.down_by_artist('002btzGY28mJnT')
    qq.download_song_by_mid('002KFiXS2EJTrs')
    quit()

    # playlist = qq.get_playlist_by_id(id='863753969')
    # playlist = qq.get_playlist_by_id(id='1750851590')
    # playlist = qq.get_playlist_by_id(id='6074955672') # 2018年度单曲分享量Top 100
    # playlist = qq.get_playlist_by_id(id='6076150222') # 2018年度欧美热歌 Top 100
    # playlist = qq.get_playlist_by_id(id='1737653534') # 欧美经典2005-2015
    # playlist = qq.get_playlist_by_id(id='2671455190') # 「华语经典」光阴的故事
    # playlist = qq.get_playlist_by_id(id='2940933712') # 90年代—经典的粤语歌曲
    playlist = qq.get_playlist_by_id(id='6132621120')  # 2018年度动漫热歌 Top 50
    playlist = qq.get_playlist_by_id(id='1974019582')  # 仙剑十年，那些让人难以割舍的仙侠情结
    playlist = qq.get_playlist_by_id(id='6310253775')  # 我自己的
    for song in list(playlist.get_songs()):
        print("")
        song.extend()
        song.download('/Users/zhangzhenhu/Music/mymusic/')

    print('fdsf')
