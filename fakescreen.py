import SocketServer
import screenclient
class LedTcpHandler(SocketServer.BaseRequestHandler):
  status = 'init'
  def handlePacket(self, packet):
    if packet.packetType == 'login':
      self.status = "loggedin"
      response = self.builder.buildPacket("login-ok")
      self.request.send(response)
    if packet.packetType == 'program':
      self.status = "programming"
      response = self.builder.buildPacket("program-ok")
      self.request.send(response)
    if packet.packetType == 'exit-program':
      self.status = "loggedin"
      response = self.builder.buildPacket("exit-program-ok")
      self.request.send(response)
    if packet.packetType == "set-text":
      self.status = "settext"
      response = self.builder.buildPacket("set-text-ok")
      self.request.send(response)
      
  def handle(self):
    print "Connection from {}".format(self.client_address[0])
    self.builder = screenclient.ScreenPacketBuilder(0, 1)
    while True:
      data = self.request.recv(1024)
      if not data: break
      packet = screenclient.ScreenPacketParser(0)
      print("<< " + data)
      packet.parse(data)
      print(packet)
      self.handlePacket(packet)
    print "Connection closed"

if __name__ == "__main__":
  HOST, PORT = "localhost", 10001
  server = SocketServer.TCPServer((HOST, PORT), LedTcpHandler)
  server.allow_reuse_address = True
  try: 
    server.serve_forever()
  finally:
    server.shutdown()