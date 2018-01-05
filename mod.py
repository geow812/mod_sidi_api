# -*- coding: utf-8 -*-

import copy

import pandas as pd
import numpy as np

from rqalpha.interface import AbstractMod
from rqalpha.environment import Environment
from rqalpha.events import EVENT
from rqalpha.api import *
from utils import *

try:
    from httplib import HTTPConnection
except ImportError:
    from http.client import HTTPConnection
import urllib
import json
import time

import ConfigParser
conf = ConfigParser.ConfigParser()
conf.read("/home/workspace/rqalpha/general.conf")
BASE_PATH = conf.get("sidi", "base_path")
HTTP_URL = conf.get("sidi", "http_url")
HTTP_PORT = conf.get("sidi", "http_port")
slippage = float(conf.get("sidi", "slippage"))
#BASE_PATH="/servlet/json?"
#offline
#HTTP_URL="172.16.126.216"
#HTTP_PORT="8002"
#online
#HTTP_URL="172.16.50.18"
#HTTP_PORT="8009"

HTTP_OK = 200

#slippage=0.002

def sidi_get_position_count(context, account_id):
    res_json =  sidi_get_position(account_id)
    if res_json.has_key('results')==False:
        logger.warn("error position type %s" % res_json)

    if len(res_json['results']) == 0:
        position_data = []
    else:
        position_data = res_json['results'][0]['data']
    
    count = 0
    
    for item in position_data:
        quantity = item['usable_qty']
        if quantity > 0:
            count = count + 1
    return count

def sidi_clear_position(context, bar_dict, account_id):
    res_json =  sidi_get_position(account_id)
    if res_json.has_key('results')==False:
        logger.warn("error position type %s" % res_json)

    if len(res_json['results']) == 0:
        position_data = []
    else:
        position_data = res_json['results'][0]['data']
    for item in position_data:
        market_id = item['market_id']
        if market_id == "SZ":
            suffix = "XSHE"
        elif market_id == "SH":
            suffix = "XSHG"
        stock =  item['stock_code']+"."+suffix


        quantity = item['usable_qty']
        try:
            if quantity != 0:
                logger.warn("SIDI sell out %s" % stock)
                status, result = sidi_order_target(context, bar_dict, stock, 0, account_id, quantity)
        except Exception, e:
            logger.warn(e)
            continue
#调仓函数，买入buy_stocks中股票，卖出不在其中的股票。
#count_type: 0  use context.buy_stock_count  1 use len(buy_stocks) 0不支持仓位控制
def sidi_adjust_position(context, bar_dict, buy_stocks, account_id, count_type=0, position_per=1):
    res_json =  sidi_get_position(account_id)
    if res_json.has_key('results')==False:
        logger.warn("error position type %s" % res_json)

    if len(res_json['results']) == 0:
        position_data = []
    else:
        position_data = res_json['results'][0]['data']
    key_list = []
    num = 0
    for item in position_data:
        market_id = item['market_id']
        if market_id == "SZ":
            suffix = "XSHE"
        elif market_id == "SH":
            suffix = "XSHG"
        stock =  item['stock_code']+"."+suffix

        key_list.append(stock)

        quantity = item['usable_qty']
        if stock not in buy_stocks:
            try:
                #if bar_dict[stock].close < bar_dict[stock].limit_up :
                if quantity != 0:
                    logger.warn("SIDI sell out %s" % stock)
                    status, result = sidi_order_target(context, bar_dict, stock, 0, account_id, quantity)
                    num = num + 1
            except Exception, e:
                logger.warn(e)
                continue

    # waiting for trading done
    time.sleep(10)
    
    position_count = len(position_data) - num
    #logger.warn(len(buy_stocks))
    if len(buy_stocks) == 0:
        return
    if context.buy_stock_count > position_count:
        '''
        if position_per == 1:
            cash = float(sidi_get_cash(account_id)['results'][0]['userable_balance'])
        else:
            cash = float(sidi_get_cash(account_id)['results'][0]['total_assets'])*position_per
        '''
        if count_type == 1:
            #不足 buy_stock_count时用于等权仓位
            cash = float(sidi_get_cash(account_id)['results'][0]['total_assets'])*position_per
            value =  cash / len(buy_stocks)
        else:
            #不足 buy_stock_count时变相控制仓位
            if position_per != 1:
                cash = float(sidi_get_cash(account_id)['results'][0]['userable_balance']) - (float(sidi_get_cash(account_id)['results'][0]['total_assets'])*(1-position_per))
            else:
                cash = float(sidi_get_cash(account_id)['results'][0]['userable_balance'])

            value =  cash / (context.buy_stock_count - position_count)
        logger.warn("total cash %f" % cash)
        for stock in buy_stocks:
            if stock not in key_list:
                logger.warn("SIDI buy %s" % stock)
                sidi_order_target(context, bar_dict, stock, value, account_id)

def sidi_get_cash(account_id):
    funcno = '1106335'
    try:
        path = "funcNo="+funcno+"&portfolio_id="+account_id
        
        status = -1
        ret = -1
        n = 0
        while (status!=HTTP_OK  or ret!="0") and n<3:
            status, result = get_sidi_data(path)
            res_json = json.loads(result)
            ret = res_json['error_no']
            time.sleep(1)
            n = n + 1
    except Exception as e:
        raise e
    return res_json

#撤单
def sidi_undo(account_id, cancel_id):
    funcno = '401151'
    try:
        path = "funcNo="+funcno+"&account_id="+account_id+"&cancel_id="+cancel_id
        
        status = -1
        ret = -1
        n = 0
        while (status!=HTTP_OK  or ret!="0") and n<3:
            status, result = get_sidi_data(path)
            res_json = json.loads(result)
            ret = res_json['error_no']
            time.sleep(1)
            n = n + 1
    except Exception as e:
        raise e
    return res_json

#可撤销委托查询
def sidi_get_revocable(account_id):
    funcno = '1106327'
    try:
        path = "funcNo="+funcno+"&account_id="+account_id
        
        status = -1
        ret = -1
        n = 0
        while (status!=HTTP_OK  or ret!="0") and n<3:
            status, result = get_sidi_data(path)
            res_json = json.loads(result)
            ret = res_json['error_no']
            time.sleep(1)
            n = n + 1
    except Exception as e:
        raise e
    
    if res_json.has_key('results')==False:
        logger.warn("error position type %s" % res_json)

    if len(res_json['results']) == 0:
        position_data = []
    else:
        position_data = res_json['results'][0]['data']

    res_json = position_data

    return res_json

#all_data: 是否返回所有数据， 默认True只返回
def sidi_get_position(account_id, all_data=True):
    funcno = '402113'
    try:
        path = "funcNo="+funcno+"&account_id="+account_id
        
        status = -1
        ret = -1
        n = 0
        while (status!=HTTP_OK  or ret!="0") and n<3:
            status, result = get_sidi_data(path)
            res_json = json.loads(result)
            ret = res_json['error_no']
            time.sleep(1)
            n = n + 1
    except Exception as e:
        raise e

    if all_data == False:    
        if res_json.has_key('results')==False:
            logger.warn("error position type %s" % res_json)

        if len(res_json['results']) == 0:
            position_data = []
        else:
            position_data = res_json['results'][0]['data']
       
        res_json = position_data

    return res_json

#parameter:
#   value for buy   when sell it's not useful
#   sell_amount for sell   when buy it's not useful
def sidi_order_target(context, bar_dict, code, value, account_id, sell_amount=0):
    funcno = '401150'
    try:
        name = instruments(code).symbol
        if "XSH" in code:
            stkcode = code[:6]
            tmp = code[7:]
            if tmp == "XSHG":
                market = "SH"
            elif tmp == "XSHE":
                market = "SZ"
        else:
            stkcode = code
        #sell
        if value == 0:
            trade_type = '1'
            amount = sell_amount
            #滑点0.5%
            price = bar_dict[code].close * (1-slippage)
        #buy
        else:
            trade_type = '0'
            #滑点0.5%
            price = bar_dict[code].close * (1+slippage)
            if price < 0.1 and price > -0.1:
                logger.warn('error price')
                return -1, 01
            amount = int(value/price / 100)*100
        logger.warn(value)
        #logger.warn(amount)
        price = str(price)
        amount = str(amount)
        path = "funcNo="+funcno+"&account_id="+account_id+"&market="+market+\
                "&stkcode="+stkcode+"&stockName="+name+"&price="+price+"&amount="+amount+"&trade_type="+trade_type
        logger.warn(BASE_PATH+path)
        
        status = -1
        ret = -1
        n = 0
        while (status!=HTTP_OK or ret=="-3013") and n<3:
            status, result = get_sidi_data(path)
            res_json = json.loads(result)
            ret = res_json['error_no']
            time.sleep(1)
            n = n + 1
        
        logger.warn(str(status)+','+str(result))
    except Exception as e:
        raise e
    return status, result

def get_sidi_data(path):
    http_client = HTTPConnection(HTTP_URL, HTTP_PORT)

    result = None
    path=BASE_PATH + path
    try:
        http_client.request('GET', path)
        response = http_client.getresponse()
        if response.status == HTTP_OK:
            result = response.read()
        else:
            result = response.read()
        return response.status, result
    except Exception as e:
        raise e
    return -1, result
    
def sidi_get_holding(account_id):
    res_json =  sidi_get_position(account_id)
    if res_json.has_key('results')==False:
        logger.warn("error position type %s" % res_json)
    
    if len(res_json['results']) == 0:
        position_data = []
    else:
        position_data = res_json['results'][0]['data']
    key_list = []
    num = 0 
    for item in position_data:
        market_id = item['market_id']
        if market_id == "SZ":
            suffix = "XSHE"
        elif market_id == "SH":
            suffix = "XSHG"
        stock =  item['stock_code']+"."+suffix

        key_list.append(stock)
    return key_list 
   
class SidiApiMod(AbstractMod):
    def start_up(self, env, mod_config):                    
        
        from rqalpha.api.api_base import register_api
        # api
        register_api('sidi_get_position', sidi_get_position)
        register_api('sidi_get_cash', sidi_get_cash)
        register_api('sidi_order_target', sidi_order_target)
        register_api('sidi_adjust_position', sidi_adjust_position)
        register_api('sidi_clear_position', sidi_clear_position)
        register_api('sidi_get_position_count', sidi_get_position_count)
        register_api('sidi_get_holding', sidi_get_holding)
        register_api('sidi_get_revocable', sidi_get_revocable)
        register_api('sidi_undo', sidi_undo)
               
    def tear_down(self, code, exception=None):
        pass
        
