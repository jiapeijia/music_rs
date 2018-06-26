import json
import random
import time
import numpy as np
import pickle

def parse_playlist_2_song(in_playlist):
    """
    将输入的歌单数据转换为推荐系统需要的数据，歌单数据为json格式<br/>
    :param in_playlist: 输入的歌单数据，json格式
    :return: 返回推荐系统我们需要的数据格式数据
    """
    # 歌单数据转换为json格式 => json格式你可以认为就是一个key/value键值对, 和字典类似；当做是字典来操作
    data = json.loads(in_playlist)

    # 获取我们需要的数据
    result_data = data['result']
    # 1. 获取歌单数据
    user_id = result_data['userId']
    playlist_id = result_data['id']
    playlist_name = result_data['name']
    playlist_subscribed_count = result_data['subscribedCount']
    playlist_play_count = result_data['playCount']
    playlist_update_time = result_data['updateTime']

    # 2. 过滤数据
    if playlist_subscribed_count < 100 or playlist_play_count < 1000:
        # 当订阅数目小于100或者播放数小于1000的时候，认为该歌单没有什么价值，是一个随便创建的歌单
        return False

    # 3. 获取歌单中的歌曲数据
    song_info = ''
    songs = result_data['tracks']
    for song in songs:
        try:
            # 获取歌曲数据
            song_id = song['id']
            song_name = song['name'].strip()
            song_popularity = song['popularity']

            # 将数据进行一行数据
            song_info += '\t' + '::::'.join([str(song_id), song_name, str(song_popularity)])
        except Exception as e:
            # print(e)
            pass

    # 最终结果返回
    return str(user_id) + "##" + str(playlist_id) + "##" + playlist_name + "##" + str(playlist_update_time) + \
           "##" + str(playlist_subscribed_count) + "##" + str(playlist_play_count) + song_info + "\n"

def parse_playlist_file(in_file, out_file):
    """
    处理歌单数据，让歌单数据的格式符合推荐系统所需要的数据格式，并将最终数据输出到文件中
    :param in_file: 输入的歌单数据文件路径
    :param out_file:  输出的歌单处理后的结果数据
    :return:
    """
    with open(out_file, 'w', encoding='UTF-8') as writer:
        with open(in_file, 'r', encoding='UTF-8') as reader:
            for line in reader:
                # 读取数据并处理成为结果
                result = parse_playlist_2_song(line)

                # 将处理成功的结果输出文件
                if result:
                    writer.writelines(result)

def clip(x, lower_bound, upper_bound):
    """
    截断操作，当x的值大于upper_bound的时候，返回upper_bound；当值小于lower_bound的时候，返回lower_bound；否则直接返回x
    :param x:  需要判断的参数值
    :param lower_bound:  下界
    :param upper_bound:  上界
    :return:
    """
    return np.clip(x, lower_bound, upper_bound)

def is_last_time(playlist_update_time, interval=31536000000):
    '''
    最近修改时间在一年以内的
    '''
    return int(time.time()) * 1000 - int(playlist_update_time) < interval

def parse_playlist_song_rating(playlist_id, playlist_subscribed_count,
                               playlist_play_count, playlist_update_time, song_info):
    """
    将歌单数据和歌曲数据转换成为MovieLens的数据格式: 歌单id 歌曲id 评分 时间戳
    :param playlist_id:  歌单id
    :param playlist_subscribed_count: 歌单订阅次数
    :param playlist_play_count: 歌单播放次数
    :param playlist_update_time: 歌单最近更新时间
    :param song_info: 歌曲信息
    :return:
    """
    try:
        song_id, _, song_popularity = song_info.split('::::')
        # 计算歌单对于歌曲的评分
        # TODO: 实际工作中评分必须根据用户的行为来定
        # 计算规则：使用歌曲的热度作为评分，如果订阅次数超过1000次并且播放次数超过1万次，同时最近修改时间在一年以内的，增加一个权重:1.1；否则设置权重为0.9.9
        # 并将范围缩放到1-10；默认的热度范围为0-100
        w = 0.9
        if float(playlist_play_count) > 10000 and float(playlist_subscribed_count) > 1000 \
           and is_last_time(playlist_update_time):
            w = 1.1
        rating = float(song_popularity) * w
        rating = clip(rating / 10, 1, 10)

        # 返回最终结果
        return ','.join([playlist_id, song_id, str(rating), playlist_update_time])
    except Exception as e:
        # print(e)
        # print(song_info)
        return ''

def parse_playlist_song_rating_file(in_file, out_file):
    """
    将原始数据转换为MovieLens数据，并输出到文件中
    :param in_file:
    :param out_file:
    :return:
    """
    with open(out_file, 'w', encoding='UTF-8') as writer:
        with open(in_file, 'r', encoding='UTF-8') as reader:
            for line in reader:
                # 获取歌单信息
                contents = line.strip().split("\t")
                user_id, playlist_id, playlist_name, playlist_update_time, playlist_subscribed_count, playlist_play_count = \
                    contents[0].split("##")
                playlist_song_info = map(
                    lambda x: parse_playlist_song_rating(playlist_id, playlist_subscribed_count, playlist_play_count,
                                                         playlist_update_time, x), contents[1:])
                playlist_song_info = filter(lambda x: len(x.split(",")) > 2, playlist_song_info)

                # 获取输出信息
                result = "\n".join(playlist_song_info)
                if result:
                    writer.writelines(result)
                    writer.writelines('\n')

def parse_playlist_song_id_2_name(in_file, out_playlist_file, out_song_file):
    """
    需要保存 歌单id=>歌单名 和 歌曲id=>歌曲名 的信息后期备用。
    :param in_file: 初步提取数据后的文件
    :param out_playlist_file:
    :param out_song_file:
    :return:
    """
    # 歌单id和歌单名称的映射字段
    playlist_id_2_name_dict = {}
    # 歌曲id和歌曲名称的映射字段
    song_id_2_name_dict = {}

    # 处理数据
    with open(in_file, 'r', encoding='UTF-8') as reader:
        for line in reader:
            try:
                # 获取歌单信息
                contents = line.strip().split("\t")
                _, playlist_id, playlist_name, _, _, _ = contents[0].split("##")
                playlist_id_2_name_dict[playlist_id] = playlist_name

                # 获取歌曲信息
                for song in contents[1:]:
                    try:
                        song_id, song_name, _ = song.split('::::')
                        song_id_2_name_dict[song_id] = song_name
                    except:
                        print("song format error:", end=song + '\n')
            except:
                print('playlist format error:', end=line + '\n')

    # 进行数据输出（输出形成二进制文件）
    with open(out_playlist_file, 'wb') as playlist_writer:
        pickle.dump(playlist_id_2_name_dict, playlist_writer)
    with open(out_song_file, 'wb') as song_writer:
        pickle.dump(song_id_2_name_dict, song_writer)

# 定义相关变量
song_file_path = './datas/playlist_detail_music_99.json'
music_playlist_song_file_path = './datas/163_music_playlist.txt'
music_playlist_song_suprise_format_file_path = './datas/163_music_playlist_song_suprise_format.txt'
playlist_pkl_file_path = "./datas/playlist.pkl"
song_pkl_file_path = "./datas/song.pkl"

# 数据初步处理
parse_playlist_file(song_file_path, music_playlist_song_file_path)

# 构建评分矩阵
parse_playlist_song_rating_file(music_playlist_song_file_path, music_playlist_song_suprise_format_file_path)

# 提取歌单id->歌单名称；歌曲id->歌曲名称的映射信息
parse_playlist_song_id_2_name(music_playlist_song_file_path, playlist_pkl_file_path, song_pkl_file_path)