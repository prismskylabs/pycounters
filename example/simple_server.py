import SocketServer
from pycounters import shortcuts, reporters, register_counter, counters, report_value, register_reporter, start_auto_reporting

class MyTCPHandler(SocketServer.BaseRequestHandler):
    """
    The RequestHandler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    @shortcuts.time("requests_time")
    @shortcuts.frequency("requests_frequency")
    def handle(self):
        # self.request is the TCP socket connected to the client
        self.data = self.request.recv(1024).strip()
        print "%s wrote:" % self.client_address[0]
        print self.data

        # measure the average length of data
        report_value("requests_data_len",len(self.data))

        # just send back the same data, but upper-cased
        self.request.send(self.data.upper())

if __name__ == "__main__":
    HOST, PORT = "localhost", 9999
    JSONFile = "/tmp/server.counters.json"

    data_len_counter = counters.TotalCounter("requests_data_len") # create the counter
    register_counter(data_len_counter) # register it, so it will start processing events
        
    reporter = reporters.JSONFileReporter(output_file=JSONFile)

    register_reporter(reporter)

    start_auto_reporting()


    # Create the server, binding to localhost on port 9999
    server = SocketServer.TCPServer((HOST, PORT), MyTCPHandler)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()