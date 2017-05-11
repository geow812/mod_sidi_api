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

BASE_PATH="/servlet/json?"
HTTP_URL="172.16.126.216"
HTTP_PORT="8002"
HTTP_OK = 200

#ACCOUNT_ID='2380'

slippage=0.002

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

def sidi_get_position(account_id):
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
            #滑点0.2%
            price = bar_dict[code].close * (1-slippage)
        #buy
        else:
            trade_type = '0'
            #滑点0.2%
            price = bar_dict[code].close * (1+slippage)
            amount = int(value/price / 100)*100
        
        price = str(price)
        amount = str(amount)
        path = "funcNo="+funcno+"&account_id="+account_id+"&market="+market+\
                "&stkcode="+stkcode+"&stockName="+name+"&price="+price+"&amount="+amount+"&trade_type="+trade_type
        print BASE_PATH+path
        
        status = -1
        ret = -1
        n = 0
        while (status!=HTTP_OK or ret=="-3013") and n<3:
            status, result = get_sidi_data(path)
            res_json = json.loads(result)
            ret = res_json['error_no']
            time.sleep(1)
            n = n + 1
        
        print status, result
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
    
    
class SidiApiMod(AbstractMod):
    def start_up(self, env, mod_config):                    
        
        from rqalpha.api.api_base import register_api
        # api
        register_api('sidi_get_position', sidi_get_position)
        register_api('sidi_get_cash', sidi_get_cash)
        register_api('sidi_order_target', sidi_order_target)
               
    def tear_down(self, code, exception=None):
        pass
        
