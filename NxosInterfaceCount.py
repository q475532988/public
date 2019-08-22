"""
This script run on Nexus switch which support scheduler or eem.
At first you need copy it in bootflash, execute command as the following
help:
    N9K# python bootflash:NxosInterfaceCount.py --h

Deploy periodic job and schedule this script using nexus's Scheduler, configuration guide: https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/6-x/system_management/configuration/guide/b_Cisco_Nexus_9000_Series_NX-OS_System_Management_Configuration_Guide/sm_8scheduler.html
A scene example: check all interfaces counter of CRC whether more than 100, if yes, alert in syslog
    python bootflash:NxosInterfaceCount.py --word=CRC --t_d=threshold --value=100 --action=syslog
    note: since there are some default value, command could just write it as: python bootflash:NxosInterfaceCount.py --value=100
Another example: check the difference of the output error counter of all interfaces within each 30 seconds, if more than 20, shutdown it
    python bootflash:NxosInterfaceCount.py --word=output_error --t_d=discrepancy --value=20 --action=shut
"""


from nxos import *
import collections
import time
import syslog
import re
import sys
import argparse
import json
try:
    from cli import *
except Exception:
    from cisco import *


class NexusInterfaceCount:

    def __init__(self, word, t_d, value, action, command=''):
        self.word=word
        self.t_d=t_d
        self.value=value
        self.action=action
        self.new_word = word.replace('_', ' ')
        self.command = command
        
    #collect info
    def collect_info(self):
        info_dict = collections.OrderedDict() # store interface and counter
        command = "show int e3/2 | in 'Ethernet|port-channel|%s' | exclude Hardware | exclude fifo"%self.new_word
        show = cli(command)
        show_list = show.splitlines()
        for item in show_list:
            item_index = show_list.index(item)
            if re.search('^Ethernet\d{1,3}.*', item) or re.search('^port-channel\d*.*', item):  #match the item if start with 'Ethernet' or 'port-channel'
                key = item.split()[0]
                vaule_line = show_list[item_index+1]
                value = vaule_line.split(' '+self.new_word)[0].split()[-1]  #value is the previous value of self.new_word
                info_dict[key] = int(value)
        return info_dict
    
    #change info_dict format with json and write to '/bootflash/__NexusInterfaceCount[time].txt'
    def write_info_to_bootflash(self, info_dict):
        j_info_dict = json.dumps(info_dict)
        time_value = str(int(time.time()))
        f1 = open('/bootflash/__NexusInterfaceCount_'+time_value+'.txt','w')
        f1.write(j_info_dict)
        f1.close()
    
    #read the file '/bootflash/__NexusInterfaceCount[time].txt'
    def read_info_from_bootflash(self, file_name):
        f1 = open('/bootflash/'+file_name,'r')
        j_old_info = f1.read()
        old_info = json.loads(j_old_info)
        f1.close()
        return old_info
    
    #do alert action
    def do_alert_action(self, new_info, old_info=None):
        if self.t_d == 'threshold':
            for i in new_info:
                if new_info[i] >= self.value:
                    py_syslog(3,"Interface {} {} >= {}, please pay attention on this.".format(i, self.new_word, self.value))
        elif self.t_d == 'discrepancy':
            for i in new_info:
                new_value = new_info[i]
                old_value = old_info[i]
                if new_value - old_value >= self.value:
                    py_syslog(3,"Interface {} {} count 60s difference exceeds the given value {}, please pay attention on this.".format(i, self.new_word, self.value))
    
    #do shut action
    def do_shut_action(self, new_info, old_info=None):
        if self.t_d == 'threshold':
            for i in new_info:
                if new_info[i] >= self.value:
                    if i.startswith('Ethernet'): #only shut physical interface
                        status_show = cli("show int %s | in 'Ethernet' | exclude Hardware"%i) #check if this port already Administratively down
                        if not '(Administratively down)' in status_show:
                            cli("config t ; int %s ; shut" %i)  #if the current value more than the given value, shut this interface
                            py_syslog(3,"Interface {} {} >= {}, shutdown.".format(i, self.new_word, self.value))
                    elif i.startswith('port-channel'): #do nothing for port-channel
                        pass
        elif self.t_d == 'discrepancy':
            for i in new_info:
                new_value = new_info[i]
                old_value = old_info[i]
                if new_value - old_value >= self.value:
                    if i.startswith('Ethernet'): #only shut physical interface
                        status_show = cli("show int %s | in 'Ethernet' | exclude Hardware"%i) #check if this port already Administratively down
                        if not '(Administratively down)' in status_show:
                            cli("config t ; int %s ; shut" %i)
                            py_syslog(3,"Interface {} {} count 60s difference exceeds the given value {}, shutdown.".format(i, self.new_word, self.value))
                    elif i.startswith('port-channel'):
                        pass
    
    #save the output into /bootfalsh/__output_show.txt
    def __save_output(self, output_info):
        file_dir = cli('dir bootflash: | in __output_show')
        file_count = len(file_dir.splitlines())
        if file_count < 1:
            f1 = open('/bootflash/__output_show.txt','w')
            f1.write(output_info)
            f1.write('\n\n@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n\n')
            f1.close()
        elif file_count == 1:
            f1 = open('/bootflash/__output_show.txt','a')
            f1.write(output_info)
            f1.write('\n\n@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n\n')
            f1.close()
        else:
            print("Please delete all files that whose names begin with __output_show in bootflash.")
    
    #execute commands
    def execute_command(self, new_info, old_info=None):
        if self.t_d == 'threshold':
            for i in new_info:
                if new_info[i] >= self.value:
                    show = cli(self.command) #collect info
                    self.__save_output(show)
        elif self.t_d == 'discrepancy':
            for i in new_info:
                new_value = new_info[i]
                old_value = old_info[i]
                if new_value - old_value >= self.value:
                    show = cli(self.command) #collect info
                    self.__save_output(show)






if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--word", type=str, default="CRC", choices=["CRC", "input_discard", "output_discard", "output_error"], help="Input that which counter you want to check. Default=CRC")
    parser.add_argument("--t_d", type=str, default="threshold", choices=["threshold", "discrepancy"], help="Input key word what you want to check, the threshold or the discrepancy. Default=threshold")
    parser.add_argument("--value", type=int, default=0, help="Input the value of threshold/discrepancy. Default=0")
    parser.add_argument("--action", type=str, default="syslog", choices=["shut", "syslog", "execute_command"], help="When the value is reached or exceeded, the interface will to be shutdown or only an alert will issue in syslog. Default=syslog")
    args = parser.parse_args()
    
    if args.action == 'execute_command':
        cli_cmd = input('Type command, when there are space enclose it with ["]:')
        instance = NexusInterfaceCount(args.word, args.t_d, args.value, args.action, cli_cmd)
    else:
        instance = NexusInterfaceCount(args.word, args.t_d, args.value, args.action)
    #control cycles and interval
    for each_time in range(6):
        if args.t_d == 'threshold':
            new_info = instance.collect_info()  #collect info 
            if args.action == 'syslog':
                instance.do_alert_action(new_info) #do alert
            elif args.action == 'shut':
                instance.do_shut_action(new_info) # shut interface
            elif args.action == 'execute_command':
                instance.execute_command(new_info) # execute command
                print('threshold')
        elif args.t_d == 'discrepancy':
            #verify if there is a file '/bootflash/__NexusInterfaceCount[time].txt' in bootflash and how many there are
            file_list = cli("dir bootflash: | in __NexusInterfaceCount").splitlines()    #execute command
            file_count = len(file_list)
            if file_count > 1:  # if there are more than 1 file, we should be delete them
                print('You should delete all TXT files whose files start with "__NexusInterfaceCount".')
            elif file_count == 1: # if there is only one file, we will compare whether the file generation time has exceeded 40s
                file_name = file_list[0].split()[-1]
                file_generate_time = int(file_name.split('_')[-1].strip('.txt'))
                if int(time.time()) - file_generate_time >= 18:  # if more than 15s, delete it and re-collect info then write to new file
                    cli("delete bootflash:"+file_name)  #delete it
                    info_dict = instance.collect_info()  #collect info 
                    instance.write_info_to_bootflash(info_dict)  # generate new file and write new info to it
                else:  # if the file generation time < 15s, we will use the value as old_info and do action
                    old_info = instance.read_info_from_bootflash(file_name) #get old_info from file
                    new_info = instance.collect_info()  #collect info 
                    if args.action == 'syslog':
                        print('syslog d')
                        instance.do_alert_action(new_info, old_info) #do action
                        cli("delete bootflash:"+file_name)  #delete old file
                        instance.write_info_to_bootflash(new_info)  #re-generate file and write new info
                    elif args.action == 'shut':
                        instance.do_shut_action(new_info, old_info) #do action
                        cli("delete bootflash:"+file_name) 
                        instance.write_info_to_bootflash(new_info)
                    elif args.action == 'execute_command':
                        print('discrepancy cli')
                        instance.execute_command(new_info, old_info) #execute command
                        cli("delete bootflash:"+file_name) 
                        instance.write_info_to_bootflash(new_info)
            else:
                info_dict = instance.collect_info()
                instance.write_info_to_bootflash(info_dict)
        time.sleep(10)
