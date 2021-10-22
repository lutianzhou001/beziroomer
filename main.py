#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math
from urllib import request
from bs4 import BeautifulSoup
import re
import ssl
import requests
import xlrd
from xlutils.copy import copy

ssl._create_default_https_context = ssl._create_unverified_context

url_1 = 'https://sh.ziroom.com/z/z1-p'
url_2 = '/?c=c%E6%94%BF%E5%AD%A6%E8%B7%AF-t2-m20-g1134727022526'
amap_key = '1f3ad2180b430afedf65bc37925c5472'
amap_get_location = 'https://restapi.amap.com/v3/geocode/geo?address='
amap_get_route_bicycling = 'https://restapi.amap.com/v4/direction/bicycling?'
office_address = input("请输入你的通勤地点")
a_min_threshold = input("请输入最大容忍房屋面积（下限）")
a_max_threshold = input("请输入最大容忍房屋面积（上限）")
p_threshold = input("请输入最大出价")
t_threshold = input("请输入最大容忍通勤时间（分钟）")


def get_cord_of_address(address):
    response = requests.get(amap_get_location + address + '&key=' + amap_key)
    location = response.json()['geocodes'][0]['location']
    return location


def get_time_between_destinatios(cord1, cord2):
    response = requests.get(
        amap_get_route_bicycling + 'origin=' + cord1 + '&' + 'destination=' + cord2 + '&key=' + amap_key)
    duration = response.json()['data']['paths'][0]['duration']
    return duration


def f_of_price(p, p_threshold):
    p = float(p)
    p_threshold = float(p_threshold)
    return -100 / p_threshold / p_threshold * p * p + 100


def f_of_time(t, t_threshold):
    t = float(t)
    t_threshold = float(t_threshold)
    t_threshold = t_threshold * 60
    return -100 / t_threshold / t_threshold * t * t + 100


def f_of_area(a, a_min_threshold, a_max_threshold):
    a = float(a)
    a_min_threshold = float(a_min_threshold)
    a_max_threshold = float(a_max_threshold)
    return -100 / (a_min_threshold - a_max_threshold) / (a_min_threshold - a_max_threshold) * (a - a_max_threshold) * (
            a - a_max_threshold) + 100


def index_of_str(s1, s2):
    n1 = len(s1)
    n2 = len(s2)
    for i in range(n1 - n2 + 1):
        if s1[i:i + n2] == s2:
            return i
    else:
        return -1


def write_to_excel(path, value):
    count = len(value)
    workbook = xlrd.open_workbook(path)
    sheets = workbook.sheet_names()
    worksheet = workbook.sheet_by_name(sheets[0])
    rows_old = worksheet.nrows
    new_workbook = copy(workbook)
    new_worksheet = new_workbook.get_sheet(0)
    for j in range(0, count):
        new_worksheet.write(rows_old, j, value[j])
    new_workbook.save(path)


houses = []

for i in range(1, 2):
    url = url_1 + str(i) + url_2
    print('第' + str(i) + '页' + '数据: ' + url)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'}
    page = request.Request(url, headers=headers)
    page_info = request.urlopen(page).read().decode('utf-8')
    soup = BeautifulSoup(page_info, 'html.parser')
    pic_wraps = soup.find_all('a', {'class': 'pic-wrap'})
    for pic_wrap in pic_wraps:
        if re.match('//sh.ziroom.com/x/', pic_wrap['href']) is not None:
            house_href = 'https:' + pic_wrap['href']
            # request for details
            detail = request.Request(house_href, headers=headers)
            detail_info = request.urlopen(detail).read().decode('utf-8')
            soup_detail = BeautifulSoup(detail_info, 'html.parser')
            # find roommates
            roommates = soup_detail.find_all('p', {'class': 'person'})
            room = []
            gender = []
            c11n = []
            job = []
            face = ''
            area = ''
            for roommate in roommates:
                house_names = roommate.find_all('span', {'class': 'housename'})
                for house_name in house_names:
                    room.append(house_name.text)
                spans = roommate.find_all('span')
                if spans[0].text in ['男', '女']:
                    if len(spans) == 2:
                        gender.append(spans[0].text)
                        c11n.append(spans[1].text)
                    if len(spans) == 3:
                        gender.append(spans[0].text)
                        c11n.append(spans[1].text)
                        job.append(spans[2].text)
            features = soup_detail.find_all('dd')
            for feature in features:
                if re.match('.', feature.text) is not None and re.match('朝', feature.text) is None:
                    area = feature.text[0:len(feature.text) - 1]
                    if re.match('约', feature.text):
                        area = feature.text[1:len(feature.text) - 1]
                if re.match('朝', feature.text) is not None:
                    face = feature.text
                    break
            res = pic_wrap.find('img', {'alt': re.compile(r"租房户型实景图")})
            if res is not None:
                index = index_of_str(res['alt'], '租房户型实景图')
                if index != -1:
                    patten = re.compile(r'[0-9]')
                    j = 1
                    house_price = 0
                    while patten.match(res['alt'][index - j]):
                        house_price = house_price + int(res['alt'][index - j]) * pow(10, j - 1)
                        j = j + 1
                    home_address = '上海市' + res['alt'][4:index - j + 1]
                    # Retrieve the cord
                    home_cord = get_cord_of_address(home_address)
                    office_cord = get_cord_of_address(office_address)
                    time_bicycling = get_time_between_destinatios(home_cord, office_cord)
            print([house_href, house_price, home_address, home_cord, office_cord, time_bicycling, room, face,
                   area, gender,
                   c11n, job])
            f = 0.20 * f_of_area(area, a_min_threshold, a_max_threshold) + 0.5 * f_of_price(house_price,
                                                                                            p_threshold) + 0.3 * f_of_time(
                time_bicycling, t_threshold)
            print('正在写入数据')
            write_to_excel('./ziroom.xls',
                           [house_href, house_price, home_address, home_cord, office_cord, time_bicycling, room, face,
                            area, gender,
                            c11n, job, f])
            house = [house_href, house_price, home_address, home_cord, office_cord, time_bicycling, room, face,
                     area, gender,
                     c11n, job, f]
            houses.append(house)
# 敏感性分析
# if some condition changes, will the result change at the same time?
# price change
# rerange houses

minf = float('inf')
min_sen = float('inf')
for house in houses:
    if house[12] < minf:
        minf = house[12]
        minp = house[1]

for house in houses:
    delta = house[12] - minf
    if delta > 0:
        print(minp)
        C = f_of_price(minp, p_threshold) - f_of_price(house[1], p_threshold) - delta / 0.50
        p_threshold_new = math.sqrt(-100 * (minp * minp - house[1] * house[1]) / C)
        p_sen = p_threshold_new / float(p_threshold) - 1
        if p_sen < min_sen:
            min_sen = p_sen

print(min_sen)
