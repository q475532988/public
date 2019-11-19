import re


#按照执行的命令不同，定义整理数据格式的方法
def show_system_resources_all_modules(arg):  #arg请使用返回数据中data的值
    body = {}
    for i in arg:
        if type(arg[i]) == dict:
            continue
        else:
            if i == "current_memory_status":
                body[i] = arg[i]
            else:
                body[i] = float(arg[i])
    for item in arg["TABLE_cpu_usage"]["ROW_cpu_usage"]:
        body["cpu%d.user"%arg["TABLE_cpu_usage"]["ROW_cpu_usage"].index(item)] = float(item['user'])
        body["cpu%d.kernel"%arg["TABLE_cpu_usage"]["ROW_cpu_usage"].index(item)] = float(item['kernel'])
        body["cpu%d.idle"%arg["TABLE_cpu_usage"]["ROW_cpu_usage"].index(item)] = float(item['idle'])
    return body

def show_interface_ethernet_1_1_54(arg):
    body = {}
    for i in arg['TABLE_interface']['ROW_interface']:
        interface_id = i['interface']
        for j in i:
            if j == 'interface':
                continue
            else:
                try:
                    body['%s_%s'%(interface_id,j)] = int(i[j])
                except (ValueError):
                    if re.search('^\d*(\.?\d*)?\s{1}\D+ps$',i[j]):  #匹配所有的以bps、pps、Kbps等结尾的数据
                        body['%s_%s'%(interface_id,j)] = float(re.search('^\d*(\.?\d*)?',i[j]).group())  #去掉尾部的bps、pps、Kbps等，但是这个并不能监控速率，建议使用eth_inrate1_bits的值，这个不用翻译
                    else:
                        body['%s_%s'%(interface_id,j)] = i[j]
    return body



#key使用telemetry path后面接的show命令，建议不要简写，没有测试过简写
fun_dict = {
    'show system resources all-modules':show_system_resources_all_modules,
    'show interface ethernet 1/1-54':show_interface_ethernet_1_1_54,
}
