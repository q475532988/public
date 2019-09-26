import http.client
import ssl
import base64
import json
import urllib3
urllib3.disable_warnings()  #for disable warning when execute "self.ret = self.s.get(self.auth_URL, auth=self.auth,verify=False)"


class Dcnm_ez_fabric:

    def __init__(self, user, password, serverip):
        self.user = user
        self.password = password
        self.serverip = serverip
        ssl._create_default_https_context = ssl._create_unverified_context


    def getRestToken(self):
        self.conn = http.client.HTTPSConnection(self.serverip)
        payload = '{"expirationTime" : 5000000000}\n'  #in milliseconds
        authenStr="%s:%s" % (self.user, self.password)
        base64string = base64.encodebytes(bytes(authenStr,'utf-8'))  #encoding with base64
        tmpstr= "Basic %s" % base64string
        authorizationStr = tmpstr.replace("b\'","").replace("\\n\'","")

        headers = {
            'content-type': "application/json",
            'authorization': authorizationStr,
            'cache-control': "no-cache"
        }

        self.conn.request("POST", "/rest/logon", payload, headers)  #according api-docs using POST method
        res = self.conn.getresponse()  #res IO stream
        data = res.read()
        longstr=data.decode("utf-8")
        strArr=json.loads(longstr)
        return strArr['Dcnm-Token']


    def my_test(self,resttoken):
        headers = {
            'dcnm-token': resttoken,
            'cache-control': "no-cache"
        }
        self.conn.request('GET','/rest/dcnm-version' ,headers=headers)  #headers里面的dcnm-token必须要有，每次新的请求都需要这个token，超时时间是上面设置的5000000000ms
        res = self.conn.getresponse()  #res是一个类似IO流类型的东西
        data = res.read() 
        jsonstr=data.decode("utf-8")
        try:
            decoded = json.loads(jsonstr)
        except (json.decoder.JSONDecodeError):  #当返回值为空或者有byte类型decode后是str，这里就会报错
            decoded = jsonstr
        print(decoded)





if __name__ == '__main__':
    dcnm = Dcnm_ez_fabric('admin','*******','x.x.x.x')
    restToken = dcnm.getRestToken()
    print(restToken)
    dcnm.my_test(restToken)
