import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import cgi
import argparse
import urllib
import ssl
from influxdb import InfluxDBClient
import datetime
import functions_for_write_to_influxdb


g_verbose   = False
g_verbose_2 = False
g_fulljson  = False
g_logfile = str()

# Default redirection to console
redirect_to_file = sys.__stdout__

#连接influxdb数据库
client = InfluxDBClient(host='10.75.61.31', port=8086, username='root', password='root',database='wwl_telemetry')

# Special function to redirect the output to console/file
def print_log(*args):
    print(*args, file=redirect_to_file)
    redirect_to_file.flush()

class S(BaseHTTPRequestHandler):
    def _set_headers(self):  
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):  
        self._set_headers()
        f = open("index.html", "r")
        bys = f.read().encode()  
        self.wfile.write(bys)   

    def do_POST(self):  
        # Respond 200 OK
        self._set_headers()
        self.send_response(200)
        self.end_headers()

        # Process headers
        (action, url, ver) = self.requestline.split()  
        tm_http_ver  = self.headers.get('TM-HTTP-Version')  
        tm_http_cnt  = self.headers.get('TM-HTTP-Content-Count')
        ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
        data_len     = int(self.headers['Content-Length'])
        print_log(">>> URL            :",  url)
        print_log(">>> TM-HTTP-VER    :",  tm_http_ver)
        print_log(">>> TM-HTTP-CNT    :",  tm_http_cnt)
        print_log(">>> Content-Type   :",  ctype)
        print_log(">>> Content-Length :",  data_len)

        if (g_verbose):
            dn_list = [];
            dn_data = {};

            if ctype == 'multipart/form-data':
                form = cgi.FieldStorage(
                        fp      = self.rfile,
                        headers = self.headers,
                        environ = {'REQUEST_METHOD':'POST',
                                   'CONTENT_TYPE':self.headers['Content-Type'],})
                dn_list = form.keys()  
                if (g_verbose_2):
                    for dn in dn_list:
                        dn_data[dn] = form.getlist(dn)
                    #print(dn_data) 
            else:
                (root, nw, dn_raw) = url.split('/') 
                dn = urllib.parse.unquote(dn_raw)
                dn_list.append(dn)
                if (g_verbose_2):
                    data = self.rfile.read(int(self.headers['Content-Length']))
                    dn_data[dn] = [data]
                    #print(dn_data) 

            # output
            for dn in dn_list:
                body = {}
                body["tags"] = {}
                print_log("    Path => %s" % (dn))
                body["measurement"] = dn
                if g_verbose_2 or g_fulljson:
                    for payload in dn_data[dn]:
                        if ctype == 'multipart/form-data':
                            json_data = json.loads(payload, encoding='UTF-8')
                        elif ctype == 'application/json':
                            json_data = json.loads(payload.decode(), encoding='UTF-8')
                        if not json_data:
                            continue
                        print_log("            node_id_str   : %s" % (json_data['node_id_str']))
                        body["tags"]["node_id_str"] = json_data['node_id_str']
                        print_log("            collection_id : %s" % (json_data['collection_id']))
                        body["tags"]["collection_id"] = json_data['collection_id']
                        print_log("            data_source   : %s" % (json_data['data_source']))
                        body["tags"]["data_source"] = json_data['data_source']
                        if g_fulljson:
                            print_log("            data          : ")
                            result = functions_for_write_to_influxdb.fun_dict[body["measurement"]](json_data['data']) #按照show命令的不同整理fields字段的数据
                            body["fields"] = result
                            body["time"] = datetime.datetime.utcnow().isoformat("T")  
                            print_log("---------------------------------------------")
                            client.write_points([body])
                        else:
                            print_log("            data          : %80.80s ..." % (json_data['data']))

        else:
            self.rfile.read(int(self.headers['Content-Length']))

        print_log("")

def run(server_class=HTTPServer, handler_class=S, port=9000, certfile="", keyfile=""):
    server_address = ('', port) 
    httpd = server_class(server_address, handler_class) 
    print_log('Starting httpd on port %d...' % (port))
    if (g_verbose == True):
        print_log('verbose      = True')
    if (g_verbose_2 == True):
        print_log('more verbose = True')
    if (g_fulljson == True):
        print_log('print full json = True')
    if g_logfile:
        print_log("Redirect to file:{}".format(g_logfile))
    if certfile:
        httpd.socket = ssl.wrap_socket(httpd.socket, certfile=certfile, keyfile=keyfile, server_side=True) 
    httpd.serve_forever()

def parse_cmdline_arguments(cmd_args):
    '''
    Parse the command line arguments
    '''
    global g_port, g_verbose, g_verbose_2, g_fulljson, g_cert, g_key, g_logfile

    if not cmd_args:
        parser = argparse.ArgumentParser()
        parser.add_argument('-v',  dest='verbose', action='store_true', default=False, help="verbose")
        parser.add_argument('-vv', dest='more_verbose', action='store_true', default=False, help="more verbose")
        parser.add_argument('-vvv', dest='most_verbose', action='store_true', default=False, help="print full json")
        parser.add_argument('-p', '--port', dest='port', action='store', default=50001, help="server listening port")
        parser.add_argument('-c', '--certfile', dest='certfile', action='store', default="", help="Secure with SSL certificate")
        parser.add_argument('-k', '--keyfile', dest='keyfile', action='store', default="", help="SSL key")
        parser.add_argument('-f', '--logfile', dest='logfile', action='store', default="", help="Log file to redirect output")
        args = parser.parse_args()
    else:
        args = cmd_args

    g_port      = args.port
    g_verbose   = args.verbose  
    g_verbose_2 = args.more_verbose  
    g_fulljson  = args.most_verbose 
    g_cert      = args.certfile
    g_key       = args.keyfile
    g_logfile   = args.logfile  

    
    if g_fulljson:
        g_verbose_2 = True
    if g_verbose_2:
        g_verbose = True

def main(cmd_args=list()):
    global redirect_to_file

    parse_cmdline_arguments(cmd_args) 
    if g_logfile:
        redirect_to_file = open(g_logfile, "w+")
        sys.stderr = redirect_to_file

    run(port=int(g_port), certfile=g_cert, keyfile=g_key)  

    if g_logfile:
        redirect_to_file.close()
        sys.stderr = sys.__stderr__

if __name__ == "__main__":
    main()
