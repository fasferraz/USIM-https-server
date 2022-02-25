###################################################################
#
#        USIM https server API version 3 (uses card module)
#        --------------------------------------------------
###################################################################
# Examples:
#
# 1. Get imsi:
# --------
# https://<domain | IP address>/?type=imsi
#
# Returns:
# {
#     "imsi": "123456789012345"
# }
#
# 2. Get res, ck, ik for a given rand, autn:
# --------------------------------------
# https://<domain | IP address>/?type=rand-autn&rand=D6BA0C396BCE3189EF8B49FAF3F67462&autn=B46F17E0F84F8000E6693AE37446963E
#
# Returns:
# {
#     "res": "FCCB24ADFBA66882",
#     "ck": "5AFF52E6AAC652024111C33D3F886786",
#     "ik": "26D77E75251C7DA4BB5645367115E4A8"
# }
#
###########################################################

import ssl
import json
import serial
import time

from http.server import HTTPServer, BaseHTTPRequestHandler
from optparse import OptionParser
from urllib.parse import urlsplit, parse_qs
from functools import partial
from smartcard.System import readers
from smartcard.util import toHexString,toBytes
from binascii import hexlify, unhexlify

from card.USIM import *

#path for the server.pem file:
PATH = '/home/fabricio/Documents/https/server.pem'


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def __init__(self, reader, *args, **kwargs):
        self.reader = reader

        # BaseHTTPRequestHandler calls do_GET **inside** __init__ !!!
        # So we have to call super().__init__ after setting attributes.
        super().__init__(*args, **kwargs)

    def API_Error(self, error_code, error_msg):
        try:
            message = json.dumps({"error": True,"error_code":error_code,"error_msg":error_msg}, indent = "\t")
            self.send_response(error_code) 
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(message.encode('utf-8'))
            
        except socket.error:
            pass

    def API_Ok(self, message):
        try:
            self.send_response(200) 
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(message.encode('utf-8'))
            
        except socket.error:
            pass

    def do_GET(self):
        try:
            params = {k: v[0] for k, v in parse_qs(urlsplit(self.path).query).items()}
            if params['type'] == 'imsi':
                imsi = return_imsi(self.reader)
                message = json.dumps({'imsi': imsi}, indent = "\t")
                self.API_Ok(message)
            elif params['type'] == 'rand-autn':
                rand = params['rand']
                autn = params['autn']
                res, ck, ik = return_res_ck_ik(self.reader, rand, autn)
                message = json.dumps({'res': res, 'ck': ck, 'ik': ik}, indent = "\t")
                self.API_Ok(message)
            else:
                self.API_Error(501, "Error")             
        except:
            self.API_Error(501, "Error")                    
        

#abstraction functions
def return_imsi(reader_index):
    return read_imsi_2(reader_index)
        
def return_res_ck_ik(reader_index, rand, autn):
    return read_res_ck_ik_2(reader_index, rand, autn)


#reader functions
def read_imsi_2(reader_index):
    a = USIM(int(reader_index))
    return a.get_imsi()
    
def read_res_ck_ik_2(reader_index,rand,autn):
    a = USIM(int(reader_index))
    x = a.authenticate(RAND=toBytes(rand), AUTN=toBytes(autn))
    if len(x) == 1: #AUTS goes in RES position
        return toHexString(x[0]).replace(" ", ""), None, None
    elif len(x) > 2:
        return toHexString(x[0]).replace(" ", ""),toHexString(x[1]).replace(" ", ""),toHexString(x[2]).replace(" ", "") 
    else:
        return None, None, None



####### Main #######
parser = OptionParser()    
parser.add_option("-r", "--reader", dest="reader", help="reader index (i.e. 0, 1, 2, ...)")  
(options, args) = parser.parse_args()

handler = partial(SimpleHTTPRequestHandler, options.reader)

httpd = HTTPServer(('', 443), handler)
httpd.socket = ssl.wrap_socket (httpd.socket,certfile=PATH, server_side=True)
httpd.serve_forever()

# server.pem can be created using the following tool (example for a self signed certificate valid for 365 days):
# openssl req -new -x509 -keyout server.pem -out server.pem -days 365 -nodes 

