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

ACCOUNT_ID='2380'

slippage=0.002

def sidi_order_target(context, bar_dict, code, value):
    funcno = '401150'
    try:
        name = instruments(code).symbol
    except Exception, e:
        print e
        return
    stkcode = code[:6]
    tmp = code[7:]
    if tmp == "XSHG":
        market = "SH"
    elif tmp == "XSHE":
        market = "SZ"
    
    if value == 0:
        trade_type = '1'
        amount = context.portfolio.positions[code].quantity
        #滑点0.2%
        price = bar_dict[code].close * (1-slippage)
    else:
        trade_type = '0'
        #滑点0.2%
        price = bar_dict[code].close * (1+slippage)
        amount = int(value/price / 100)*100
    
    price = str(price)
    amount = str(amount)
    path = "funcNo="+funcno+"&account_id="+ACCOUNT_ID+"&market="+market+\
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
    return status, result

def get_sidi_data(path):
    http_client = HTTPConnection(HTTP_URL, HTTP_PORT)

    result = None
    path=BASE_PATH + path
    try:
        http_client.request('GET', path)
        #headers = {"Authorization": "Bearer " + self.token})
        response = http_client.getresponse()
        if response.status == HTTP_OK:
            result = response.read()
        else:
            result = response.read()
        #if(path.find('.csv?') != -1):
        #    result=result.decode('GBK').encode('utf-8')
        return response.status, result
    except Exception as e:
        raise e
    return -1, result
    
    
class SidiApiMod(AbstractMod):
    def start_up(self, env, mod_config):                    
        
        from rqalpha.api.api_base import register_api
        # api
        #register_api('get_sidi_data', get_sidi_data)
        register_api('sidi_order_target', sidi_order_target)
               
    def tear_down(self, code, exception=None):
        pass
        
