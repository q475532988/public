import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import cgi
import argparse
import urllib
import ssl

g_verbose   = False
g_verbose_2 = False
g_fulljson  = False
g_logfile = str()

# Default redirection to console
redirect_to_file = sys.__stdout__

# Special function to redirect the output to console/file
def print_log(*args):
    print(*args, file=redirect_to_file)  #默认输出为console，可以重定向到文件
    redirect_to_file.flush()

class S(BaseHTTPRequestHandler):
    def _set_headers(self):   #所有的动作中都必须回复response code、发送headers、结束headers
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):  #如果client没有get动作，这个方法可以不要
        self._set_headers()
        f = open("index.html", "r")
        bys = f.read().encode()   #在python3中需要用bytes类型的
        self.wfile.write(bys)   #发送数据到客户端使用wfile.write，读取数据用rfile.read

    def do_POST(self):   #telemetry吐数据用的是POST
        # Respond 200 OK
        self._set_headers()
        self.send_response(200)
        self.end_headers()

        # Process headers
        (action, url, ver) = self.requestline.split()   #记住这里的requestline，没找到在哪里定义的这个变量
        #print(action,url,ver)  #POST /network/show%20cdp%20neighbors HTTP/1.0
        tm_http_ver  = self.headers.get('TM-HTTP-Version')  #这里在py3使用get方法，没有getheader
        tm_http_cnt  = self.headers.get('TM-HTTP-Content-Count')
        ctype, pdict = cgi.parse_header(self.headers.get('content-type'))#返回两个值，第一个是Content-Type，第二个是其他的选项的键值对字典
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
                #读取表格形式的数据，fp,headers,environ定义如下
                form = cgi.FieldStorage(
                        fp      = self.rfile,
                        headers = self.headers,
                        environ = {'REQUEST_METHOD':'POST',
                                   'CONTENT_TYPE':self.headers['Content-Type'],})
                #form = cgi.parse_multipart(fp=self.rfile, pdict=pdict)   #此方法与如上相同，但此方法不能很好的支持大量数据，也没有如上方法安全
                dn_list = form.keys()  #返回form表格中存储的值的键，这个值不是字典，但与字典类似，可用print(form)查看
                #print(form)
                if (g_verbose_2):
                    for dn in dn_list:
                        dn_data[dn] = form.getlist(dn)#将key对应的值返回到一个list中，测试：会将值当成一整个字符串，所以list中也只有一个值
                    #print(dn_data)  #这个dn_data中有两个值：sys/tm-connection-hello和show clock
            else:
                (root, nw, dn_raw) = url.split('/') #将/network/show%20cdp%20neighbors分割，第一个元素为空
                dn = urllib.parse.unquote(dn_raw)
                dn_list.append(dn)
                if (g_verbose_2):
                    data = self.rfile.read(int(self.headers['Content-Length']))
                    dn_data[dn] = [data]
                    #print(dn_data)  #这个有一个值：show clock

            # output
            for dn in dn_list:
                print_log("    Path => %s" % (dn))
                if g_verbose_2 or g_fulljson:
                    #with open("json.txt", "w") as f:
                    #    out = "%s" % (dn_data[dn])
                    #    f.write(out)
                    #print_log(dn_data[dn])
                    for payload in dn_data[dn]:
                        if ctype == 'multipart/form-data':
                            json_data = json.loads(payload, encoding='UTF-8')
                        elif ctype == 'application/json':
                            json_data = json.loads(payload.decode(), encoding='UTF-8')
                        if not json_data:
                            continue
                        print_log("            node_id_str   : %s" % (json_data['node_id_str']))
                        print_log("            collection_id : %s" % (json_data['collection_id']))
                        print_log("            data_source   : %s" % (json_data['data_source']))
                        if g_fulljson:
                            print_log("            data          : ")
                            print_log(json.dumps(json_data['data'], ensure_ascii=True, indent=2, sort_keys=True))
                            print_log("---------------------------------------------")

                        else:
                            print_log("            data          : %80.80s ..." % (json_data['data']))

        else:
            #
            self.rfile.read(int(self.headers['Content-Length']))

        print_log("")

def run(server_class=HTTPServer, handler_class=S, port=9000, certfile="", keyfile=""):
    server_address = ('', port)  #ip位置为空表示本地
    httpd = server_class(server_address, handler_class)  #参照文档这里为通用固定格式，HTTPServer可以直接使用，BaseHTTPRequestHandler则需要定义里面的所有方法，如do_GET()
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
        httpd.socket = ssl.wrap_socket(httpd.socket, certfile=certfile, keyfile=keyfile, server_side=True) #提供证书认证,每次更换receiver都要重新生成证书
    httpd.serve_forever()  #不中断启动HTTP server监听端口，除非shutdown，所有http的动作都在自定义的BaseHTTPRequestHandler中完成，如get，post等等

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
    g_verbose   = args.verbose  #控制是否读取头部内容中的show命令或者path路径
    g_verbose_2 = args.more_verbose  #控制是否读取POST信息中的payload并显示部分设备基础信息
    g_fulljson  = args.most_verbose #控制是否读取POST信息中的payload并显示部分设备基础信息和全部show命令的输出
    g_cert      = args.certfile
    g_key       = args.keyfile
    g_logfile   = args.logfile  #存储到receiver本地的文件的完整路径

    #most_verbose如果设置为True则more_verbose和verbose都改为True，3个参数以此类推
    if g_fulljson:
        g_verbose_2 = True
    if g_verbose_2:
        g_verbose = True

def main(cmd_args=list()):
    global redirect_to_file

    parse_cmdline_arguments(cmd_args) #解析参数，如果没有参数传入则重新定义参数
    if g_logfile:
        redirect_to_file = open(g_logfile, "w+")
        sys.stderr = redirect_to_file

    run(port=int(g_port), certfile=g_cert, keyfile=g_key)  #传递监听端口（交换机侧可以配置），证书和key

    if g_logfile:
        redirect_to_file.close()
        sys.stderr = sys.__stderr__

if __name__ == "__main__":
    main()
