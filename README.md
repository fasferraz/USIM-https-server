# USIM https server API for AKA authentication

This is just a basic https server with an API that exposes IMSI, and AKA algorithm to external clients needing that information.

This allow a remote client to be "USIMless", and retrieve IMSI, and RES, CK and IK remotely.

This is just an example without any authentication/authorization mechanism, but can be easily adapted to support it.

Some applications that I've done that need a dongle or a smartcard reader (eNB, SWu emulator, GBA, etc...), can be adapted to retrieve authentication information through this web service.

I can imagine a usecase: this service running in my Raspberry Pi with a smartcard reader connected to it with my USIM datacard, and I, somewhere in the world with my laptop, using a wifi network to connect to my operator ePDG without any physical USIM card to activate a corporate APN.

The next picture sums it all:

<p align="center"><img src="images/usim-https-server.png" width="100%"></p>


So the API has two basic operations, and returns the information in json format:

- one to obtain the IMSI:
  
  Example:
  - https://<domain | IP address>/?type=imsi


```
 {
     "imsi": "123456789012345"
 }
```
- one to get the RES, CK and IK for a given RAND and AUTN:
  
  Example:
  - https://<domain | IP address>/?type=rand-autn&rand=D6BA0C396BCE3189EF8B49FAF3F67462&autn=B46F17E0F84F8000E6693AE37446963E

```
 {
     "res": "FCCB24ADFBA66882",
     "ck": "5AFF52E6AAC652024111C33D3F886786",
     "ik": "26D77E75251C7DA4BB5645367115E4A8"
 }
```

The application can communicate with the USIM through a modem supporting AT+CSIM command, or through a smartcard reader.

These are the application options:

```
root@ubuntu# python3 usim_https_server.py -h
Usage: usim_https_server.py [options]

Options:
  -h, --help            show this help message and exit
  -m MODEM, --modem=MODEM
                        modem port (i.e. COMX, or /dev/ttyUSBX)
  -r READER, --reader=READER
                        reader index (i.e. 0, 1, 2, etc... Default: 0)

```

The application needs a server.pem file for which a path must be specificed in the code.
I created my self-signed certificate using this command (example for a self signed certificate valid for 365 days):

```
openssl req -new -x509 -keyout server.pem -out server.pem -days 365 -nodes
```



Updated Version (2):
-------------------

Added a third API operation to allow sending/receiving APDU commands with the USIM:


- get the DATA, SW1 and SW2 response for a given APDU:
  
  Example:
  - https://<domain | IP address>/?type=apdu&hex=00A40000023F00

```
 {
     "data": "",
     "sw1": "90",
     "sw2": "00"
 }
```

Since this operation needs a context to be mantained with the USIM, we need to establish the connection, and use the same connection for all API calls, instead of an on-demand model, like the original version.

That's the reason why I choose to keep the two versions.

Example of IMSI retrieval through APDU communication:

```
fabricio@ubuntu:~$ curl -k "https://localhost/?type=apdu&hex=00A40000023F00"
{
	"data": "",
	"sw1": "90",
	"sw2": "00"
}

fabricio@ubuntu:~$ curl -k "https://localhost/?type=apdu&hex=00A40000027F20"
{
	"data": "",
	"sw1": "90",
	"sw2": "00"
}

fabricio@ubuntu:~$ curl -k "https://localhost/?type=apdu&hex=00A40000026F07"
{
	"data": "",
	"sw1": "90",
	"sw2": "00"
}

fabricio@ubuntu:~$ curl -k "https://localhost/?type=apdu&hex=00B0000009"
{
	"data": "082986609410005040",
	"sw1": "90",
	"sw2": "00"
}
```


Updated Version (3):
-------------------

Added a 3rd version (with only smartcard reader support), but using the card.USIM module (https://github.com/mitshell/card) because it handles all types of cards, including blank USIM cards bought in eBay or AliExprees, which was not the case with my other USIM interaction functions used in version 1 and 2.
