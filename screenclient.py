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
  def __init__(self, addr=0, screenWidth=20, screenHeight=8):
    self.args = { }
    self.addr = addr
    self.server = addr == 0
    self.screenWidth = screenWidth
    self.screenHeight = screenHeight
    
  def readNumber(self, reader, length=1, base=16):
    self.lastPos = reader.tell()
    data = binascii.unhexlify(reader.read(length * 2))
    return int(data, base)
  
  def readByte(self, reader, length=2, base=16):
    self.lastPos = reader.tell()
    data = reader.read(length)
    return int(data, base)

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
  
  def parseSetText(self, reader):
    self.args["program"] = self.readNumber(reader, 2)
    self.args["page"] = self.readNumber(reader, 2)
    self.args["appear"] = int(self.readChar(reader))
    self.args["disappear"] = int(self.readChar(reader))
    self.args["stay"] = self.readNumber(reader, 2, 10)
    expectedScreenSize = self.screenHeight * (self.screenWidth + 2)
    text = binascii.unhexlify(reader.read(2 * expectedScreenSize))
    if len(text) != expectedScreenSize:
      raise Exception("Invalid screen size %d, expected %d" % (len(text), expectedScreenSize))
    self.args['text'] = [text[i+1:i+self.screenWidth+2] for i in range(0,expectedScreenSize, self.screenWidth + 2)]
    
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
    elif cmd == 'H' and self.server:
      self.packetType = 'exit-program'
    elif cmd == 'H':
      self.packetType = 'exit-program-ok'
      result = self.readChar(reader)
      self.args['result'] = result == 'Y'
    elif cmd == 'C' and self.server:
      self.packetType = 'set-text'
      self.parseSetText(reader)
    elif cmd == 'C':
      self.packetType = 'set-text-ok'
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
  
  def buildSetText(self, args):
    if "text" not in args:
      raise Exception("Text arg required but not found")
    msg = "C"
    msg += "%02X" % 1 # program
    msg += "%02X" % 1 # page
    msg += "%01d" % 2 # Appear effect
    msg += "%01d" % 2 # Disppear effect
    msg += "%02d" % 5 # Stay seconds
    msg += "".join([" " + a + " " for a in args["text"]])
    return msg
    
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
    elif packetType == "exit-program":
      result = "H"
    elif packetType == "exit-program-ok":
      result = "HY"
    elif packetType == "set-text":
      result = self.buildSetText(args)
    elif packetType == "set-text-ok":
      result = "CY"
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
    print(">> " + msg)
    return msg
    
class ScreenClient:
  state = 'init'
  def __init__(self, host, port, screenWidth=20, screenHeight=8):
    self.host = host
    self.port = port
    self.builder = ScreenPacketBuilder()
    self.screenWidth = screenWidth
    self.screenHeight = screenHeight
  
  def validateText(self, text):
    if len(text) != self.screenHeight: return "Height expected %d, found %d" % (len(text), self.screenHeight)
    for line in text:
      if len(line) != self.screenWidth: return "Width expected %d, found %d" % (len(line), self.screenWidth)
    return None
    
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
      raise Exception("Program mode Failure")
    self.state = "program-enabled"
   
  def setText(self, text):
    if self.state != "program-enabled":
      raise Exception("SetText while not program-enabled")
    errors = self.validateText(text) 
    if errors != None:
      raise Exception("Invalid text size %s" % errors)
    print("Starting setText")
    packet = self.builder.buildPacket("set-text",{"text": text})
    self.sock.send(packet)
    self.state = "set-text"
    response = self.sock.recv(1024)
    packet = ScreenPacketParser(254)
    packet.parse(response)
    print(packet)
    if packet.packetType != 'set-text-ok' or packet.args['result'] != True:
      raise Exception("SetText Failure")
    self.state = "program-enabled"
     
  def exitProgram(self):
    if self.state != "program-enabled":
      raise Exception("Exit Program while not program-enabled")
    print("Exitting programming mode")
    packet = self.builder.buildPacket("exit-program")
    self.sock.send(packet)
    self.state = "exit-program"
    response = self.sock.recv(1024)
    packet = ScreenPacketParser(254)
    packet.parse(response)
    print(packet)
    if packet.packetType != 'exit-program-ok' or packet.args['result'] != True:
      raise Exception("Exit program mode Failure")
    self.state = "authenticated"
  
if __name__ == "__main__":
  HOST, PORT = "localhost", 10001
  text = [a.rstrip('\n') for a in open("default.txt").readlines()]
  client = ScreenClient(HOST, PORT)
  try: 
    client.connect()
    client.login()
    client.program()
    client.setText(text)
    client.exitProgram()
  except Exception as e:
    print e.message
    traceback.print_exc()