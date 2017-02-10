import socket
import pip
import binascii
import traceback
import io

try:
  from crc16 import crc16xmodem
except:
  pip.main(['install', "crc16"])
  from crc16 import crc16xmodem

class ScreenPacketParser:
  def __init__(self, addr=0):
    self.args = { }
    self.addr = addr
    self.server = addr == 0
    
  def readNumber(self, reader, length=1):
    self.lastPos = reader.tell()
    data = binascii.unhexlify(reader.read(length * 2))
    return int(data, 16)
  
  def readByte(self, reader, length=2):
    self.lastPos = reader.tell()
    data = reader.read(length)
    return int(data, 16)

  def readChar(self, reader):
    return chr(self.readByte(reader))
            
  def expectByte(self, reader, byte):
    if(type(byte) == int): byte = chr(byte)
    result = chr(self.readByte(reader))
    if(result != byte): raise(Exception("Unexpected byte %d (expected %d)" % (ord(result), ord(byte))))

  def expectNumber(self, reader, number):
    readNumber = self.readNumber(reader, 2)
    if(readNumber != number): raise(Exception("Unexpected %d (expected %d)" % (readNumber, number)))
      
  def expectEnd(self, reader):
    result = reader.read(1)
    if (result != ''): raise(Exception("Expected end, read byte %s" % result))
    
  def parseLogin(self, reader, arglen):
    self.args['password'] = binascii.unhexlify(reader.read(arglen * 2))
    
  def parsePacket(self, reader):
    if self.server:
      self.expectByte(reader, 21)
      self.expectByte(reader, 21)
    else:
      self.expectByte(reader, 15)
      self.expectByte(reader, 15)
    self.expectByte(reader, 3)
    # screen address
    self.expectNumber(reader,1)
    if self.server:
      self.expectNumber(reader,254)
    cmdLen = self.readNumber(reader, 3)
    cmd = self.readChar(reader)
    if cmd == 'G' and self.server:
      self.packetType = 'login'
      self.parseLogin(reader, cmdLen - 1)
    elif cmd == 'G':
      self.packetType = 'login-ok'
      result = self.readChar(reader)
      self.args['result'] = result == 'Y'
    elif cmd == 'P' and self.server:
      self.packetType = 'program'
    elif cmd == 'P':
      self.packetType = 'program-ok'
      result = self.readChar(reader)
      self.args['result'] = result == 'Y'
    checksum = reader.read(8)
    self.expectByte(reader, 4)
    if not self.server:
      self.expectByte(reader, 4)
    self.expectEnd(reader)
  
  def __str__(self):
    return self.packetType + " " + str(self.args)
    
  def parse(self, data):
    reader = io.BytesIO(data)
    try:
      self.parsePacket(reader)
    except Exception as e:
      print("At pos %d: %s" % (self.lastPos, e.message))
  
class ScreenPacketBuilder:
  serverHeader = "0F0F03"
  clientHeader = "151503"
  def __init__(self, src=254, dst=1):
    self.src = src
    self.dst = dst
    
  def numberToHex(self, number, length=2):
    result = hex(number)[2:].upper()
    return binascii.hexlify(result.rjust(length, '0'))
  
  def buildBody(self, packetType, args):
    result = ""
    if packetType == 'login':
      if 'password' in args:
        password = args['password']
      else:
        password = ''
      result = "G" + password[:8].ljust(8, ' ')
    elif packetType == "login-ok":
      result = "GY"
    elif packetType == "program":
      result = "P"
    elif packetType == "program-ok":
      result = "PY"
    else:
      raise Exception("Unknown packet type: " + packetType)
    return result
    
  def buildPacket(self, packetType, args={}):
    msg = "%02X" % self.dst
    if self.src > 0: msg += "%02X" % self.src
    body = self.buildBody(packetType, args)
    msg += "%03X" % len(body)
    msg += body
    checksum = self.numberToHex(crc16xmodem(msg))
    header = self.clientHeader
    if self.src == 0: header = self.serverHeader
    msg = header + binascii.hexlify(msg) + checksum + "04"
    if self.src == 0: msg += "04"
    print(msg)
    return msg
    
class ScreenClient:
  state = 'init'
  def __init__(self, host, port):
    self.host = host
    self.port = port
    self.builder = ScreenPacketBuilder()
    
    
  def connect(self):
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.sock.connect((self.host, self.port))
    self.state = "connected"
    
  def login(self):
    if self.state != "connected":
      raise Exception("Login while not connected")
    print("Starting login")
    packet = self.builder.buildPacket("login")
    self.sock.send(packet)
    self.state = "login"
    response = self.sock.recv(1024)
    packet = ScreenPacketParser(254)
    packet.parse(response)
    print(packet)
    if packet.packetType != 'login-ok' or packet.args['result'] != True:
      raise Exception("Login Failure")
    self.state = "authenticated"
    
  def program(self):
    if self.state != "authenticated":
      raise Exception("Program while not authenticated")
    print("Starting programming mode")
    packet = self.builder.buildPacket("program")
    self.sock.send(packet)
    self.state = "enter-program"
    response = self.sock.recv(1024)
    packet = ScreenPacketParser(254)
    packet.parse(response)
    print(packet)
    if packet.packetType != 'program-ok' or packet.args['result'] != True:
      raise Exception("Login Failure")
    self.state = "program-enabled"
    
if __name__ == "__main__":
  HOST, PORT = "localhost", 10001
  client = ScreenClient(HOST, PORT)
  try: 
    client.connect()
    client.login()
    client.program()
  except Exception as e:
    print e.message
    traceback.print_exc()