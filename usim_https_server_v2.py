###########################################################
#
#                 USIM https server API
#                 ---------------------
###########################################################
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
# 3. Send arbitrary APDUs:
# --------------------------------------
# https://<domain | IP address>/?type=apdu&hex=00A40000023F00
#
# Returns:
# {
#     "data": "",
#     "sw1": "90",
#     "sw2": "00"
# }
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

#path for the server.pem file:
PATH = '/home/user/https/server.pem'


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def __init__(self, modem, reader, *args, **kwargs):
        self.modem = modem
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
                imsi = return_imsi(self.modem, self.reader)
                message = json.dumps({'imsi': imsi}, indent = "\t")
                self.API_Ok(message)
            elif params['type'] == 'rand-autn':
                rand = params['rand']
                autn = params['autn']
                res, ck, ik = return_res_ck_ik(self.modem, self.reader, rand, autn)
                message = json.dumps({'res': res, 'ck': ck, 'ik': ik}, indent = "\t")
                self.API_Ok(message)
            elif params['type'] == 'apdu':
                hexstring = params['hex']
                data, sw1, sw2 = return_apdu(self.modem, self.reader, hexstring)
                message = json.dumps({'data': data, 'sw1': sw1, 'sw2': sw2}, indent = "\t")
                self.API_Ok(message)

            else:
                self.API_Error(501, "Error")             
        except:
            self.API_Error(501, "Error")                    
        

#abstraction functions
def return_imsi(serial_interface, reader_index):
    if serial_interface is not None:
        return get_imsi(serial_interface)
    else:
        return read_imsi(reader_index)
        
def return_res_ck_ik(serial_interface, reader_index, rand, autn):
    if serial_interface is not None:
        return get_res_ck_ik(serial_interface, rand, autn)
    else:
        return read_res_ck_ik(reader_index, rand, autn)

def return_apdu(serial_interface, reader_index, hexstring):
    if serial_interface is not None:
        return get_apdu(serial_interface, hexstring)
    else:
        return read_apdu(reader_index, hexstring)
        
#modem functions
def get_imsi(ser):

    imsi = None
     
    CLI = []
    CLI.append('AT+CIMI\r\n')
    
    a = time.time()
    for i in range(len(CLI)):
        ser.write(CLI[i].encode())
        buffer = ''
        while "OK\r\n" not in buffer and "ERROR\r\n" not in buffer:
            buffer +=  ser.read().decode("utf-8")           
            if time.time()-a > 0.5:
                ser.write(CLI[i].encode())
                a = time.time() +1           
        if i==0:    
            for m in buffer.split('\r\n'):
                if len(m) == 15:
                    imsi = m       

    return imsi


def get_res_ck_ik(ser, rand, autn):
    res = None
    ck = None
    ik = None

    CLI = []  
    #CLI.append('AT+CRSM=178,12032,1,4,0\r\n')
    CLI.append('AT+CSIM=14,"00A40000023F00"\r\n')
    CLI.append('AT+CSIM=14,"00A40000022F00"\r\n')
    CLI.append('AT+CSIM=42,"00A4040010A0000000871002FFFFFFFF8903050001"\r\n')
    CLI.append('AT+CSIM=78,\"008800812210' + rand.upper() + '10' + autn.upper() + '\"\r\n')

    a = time.time()
    for i in CLI:
        ser.write(i.encode())
        buffer = ''
    
        while "OK" not in buffer and "ERROR" not in buffer:
            buffer +=  ser.read().decode("utf-8")
        
            if time.time()-a > 0.5:
                ser.write(i.encode())
                a = time.time() + 1
                
    for i in buffer.split('"'):
        if len(i)==4:
            if i[0:2] == '61':
                len_result = i[-2:]
    
    LAST_CLI = 'AT+CSIM=10,"00C00000' + len_result + '\"\r\n'
    ser.write(LAST_CLI.encode())
    buffer = ''
    
    while "OK\r\n" not in buffer and "ERROR\r\n" not in buffer:
        buffer +=  ser.read().decode("utf-8")
        
    for result in buffer.split('"'):
        if len(result) > 10:
            res = result[4:20]
            ck = result[22:54]
            ik = result[56:88]  
   
    return res, ck, ik

def get_apdu(ser, hexstring):
    data = None
    sw1 = None
    sw2 = None

    CLI = []  
    CLI.append('AT+CSIM=' + str(len(hexstring)) + ',"' + hexstring + '"\r\n')

    a = time.time()
    for i in CLI:
        ser.write(i.encode())
        buffer = ''
    
        while "OK" not in buffer and "ERROR" not in buffer:
            buffer +=  ser.read().decode("utf-8")
        
            if time.time()-a > 0.5:
                ser.write(i.encode())
                a = time.time() + 1
                
    for m in buffer.split('\r\n'):
        if m[0:5] == '+CSIM':
            data = m.split('"')[1][:-4]
            sw1 = m.split('"')[1][-4:-2]
            sw2 = m.split('"')[1][-2:]
            break
            
    return data, sw1, sw2




#reader functions
def bcd(chars):
    bcd_string = ""
    for i in range(len(chars) // 2):
        bcd_string += chars[1+2*i] + chars[2*i]
    return bcd_string

def int2hex(num):  #up to 255
    return hexlify(bytes([num])).decode('utf-8')

def read_imsi(connection):
    imsi = None

    data, sw1, sw2 = connection.transmit(toBytes('00A40000023F00'))     
    data, sw1, sw2 = connection.transmit(toBytes('00A40000027F20'))
    data, sw1, sw2 = connection.transmit(toBytes('00A40000026F07'))
    data, sw1, sw2 = connection.transmit(toBytes('00B0000009'))  
    result = toHexString(data).replace(" ","")
    imsi = bcd(result)[-15:]
    
    return imsi

def read_res_ck_ik(connection, rand, autn):
    res = None
    ck = None
    ik = None

    data, sw1, sw2 = connection.transmit(toBytes('00A40000023F00'))    
    data, sw1, sw2 = connection.transmit(toBytes('00A40000022F00')) 
    data, sw1, sw2 = connection.transmit(toBytes('00A4040010A0000000871002FFFFFFFF8903050001'))   
    data, sw1, sw2 = connection.transmit(toBytes('008800812210' + rand.upper() + '10' + autn.upper()))   
    if sw1 == 97:
        data, sw1, sw2 = connection.transmit(toBytes('00C00000') + [sw2])         
        result = toHexString(data).replace(" ", "")
        res = result[4:20]
        ck = result[22:54]
        ik = result[56:88]          

    return res, ck, ik

def read_apdu(connection, hexstring):
    
    data = None
    sw1 = None
    sw2 = None

    data, sw1, sw2 = connection.transmit(toBytes(hexstring))    
    data = toHexString(data).replace(" ", "")
    return data, int2hex(sw1), int2hex(sw2)




####### Main #######
parser = OptionParser()    
parser.add_option("-m", "--modem", dest="modem", help="modem port (i.e. COMX, or /dev/ttyUSBX)") 
parser.add_option("-r", "--reader", dest="reader", help="reader index (i.e. 0, 1, 2, ...)")  
(options, args) = parser.parse_args()

modem_connection = None
if options.modem is not None:
    try:
        modem_connection = serial.Serial(options.modem,38400, timeout=0.5,xonxoff=True, rtscts=True, dsrdtr=True, exclusive =True)
    except:
        pass
    

reader_connection = None
if options.reader is not None:
    try:
        r = readers()
        reader_connection = r[int(options.reader)].createConnection()
        reader_connection.connect()
    except:
        pass


if modem_connection is None and reader_connection is None:
    print('No modem/reader. \nExiting.')
    exit()

handler = partial(SimpleHTTPRequestHandler, modem_connection, reader_connection)

httpd = HTTPServer(('', 443), handler)
httpd.socket = ssl.wrap_socket (httpd.socket,certfile=PATH, server_side=True)
httpd.serve_forever()

# server.pem can be created using the following tool (example for a self signed certificate valid for 365 days):
# openssl req -new -x509 -keyout server.pem -out server.pem -days 365 -nodes 

