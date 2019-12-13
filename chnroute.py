import sys
import getopt
import urllib.request
import re
import math
import io
from ipaddress import ip_network
import bisect

mod_expect = 'exp'
mod_contain = 'con'
mod = ''
output = ''
split = 0

country_list = []

ip_internal = ["0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16", "172.16.0.0/12",
               "192.0.0.0/24", "192.0.0.0/29", "192.0.0.8/32", "192.0.0.170/32", "192.0.0.171/32", "192.0.2.0/24",
               "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24", "224.0.0.0/4", "240.0.0.0/4"]

def fetch_ip_data():
    print("Fetching data from apnic.net, it might take a few minutes, please wait...")
    url='http://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest';
    #url = 'http://127.0.0.1/delegated-apnic-latest.txt'
    res = urllib.request.urlopen(url).read().decode('utf-8')
    data = re.findall("""apnic\|..\|ipv4\|[0-9\.]+\|[0-9]+\|[0-9]+\|""", res, re.IGNORECASE)

    results = []
    for line in data:
        unit_items = line.split('|')
        country = unit_items[1]

        if country not in country_list:
            continue

        starting_ip = unit_items[3]
        num_ip = int(unit_items[4])

        # mask in *nix format
        mask = 32-int(math.log(num_ip, 2))

        # ip to bin
        ipbin = ipmask_to_bin(starting_ip, mask)

        results.append((starting_ip, mask, ipbin))

    # 处理完网络获取的数据，如果是排除模式，需要加上保留的内网地址一并排除
    if mod == mod_expect:
        for line in ip_internal:
            unit = line.split('/')
            starting_ip = unit[0]
            mask = int(unit[1])
            ipbin = ipmask_to_bin(starting_ip, mask)
            results.append((starting_ip, mask, ipbin))

    return results


def ipmask_to_bin(ipaddr, mask):
    # ip to bin
    ipbin = 0b0
    singlebyte = ipaddr.split('.')
    for i in range(0, 4):
        tmpbin = int(singlebyte[i])
        ipbin |= tmpbin
        if i < 3:
            ipbin <<= 8
        else:
            break
    ipbin >>= 32 - mask
    return ipbin


def sort_iplist(iplist):
    iplist.sort(key=ipkey)
    return iplist


def ipkey(x):
    ipmask_full = x[2] << (32 - x[1] + 8)
    ipmask_full += x[1]
    return ipmask_full


def merge_ip_data(netlist):
    # 合并ip的函数，从后向前合并
    i = len(netlist) - 2
    while i >= 0:
        ret = merge_ip_data_proc(netlist, i)
        i = ret[1] - 1
        netlist = ret[0]
    return netlist


def merge_ip_data_proc(netlist, curpos):
    if curpos < len(netlist) - 1:
        curnet = netlist[curpos]
        nextnet = netlist[curpos+1]
        if curnet[1] > nextnet[1]:
            bigger_net = curnet[2] >> (curnet[1] - nextnet[1])
            if bigger_net == nextnet[2]:
                del netlist[curpos]
                merge_ip_data_proc(netlist, curpos)

        if (curnet[1] == nextnet[1]) and (nextnet[2] ^ curnet[2] == 1):
            del netlist[curpos + 1]
            newmask = curnet[1] - 1
            newbinnet = curnet[2] >> 1
            newnet = (ip_bin_to_string(newbinnet, newmask), newmask, newbinnet)
            netlist[curpos] = newnet
            merge_ip_data_proc(netlist, curpos)
    return [netlist, curpos]


def ip_bin_to_string(netbin, maskint):
    fullnet = netbin << (32 - maskint)
    fullnet = hex(fullnet)[2:]
    if len(fullnet) == 7:
        fullnet = '0' + fullnet
    strnet = [0]*4
    strnet[0] = fullnet[0:2]
    strnet[1] = fullnet[2:4]
    strnet[2] = fullnet[4:6]
    strnet[3] = fullnet[6:8]
    strnet = [int(i, 16) for i in strnet]
    strnet = "%d.%d.%d.%d" % tuple(strnet)
    return strnet


def show_255_mask(num_ip):
    imask = 0xffffffff << (32 - num_ip)
    imask &= 0xffffffff
    # imask = 0xffffffff ^ (num_ip-1)
    # convert to string
    imask = hex(imask)[2:]
    if len(imask) == 7:
        imask = '0' + imask
    mask = [0]*4
    mask[0] = imask[0:2]
    mask[1] = imask[2:4]
    mask[2] = imask[4:6]
    mask[3] = imask[6:8]

    # convert str to int
    mask = [int(i, 16) for i in mask]
    mask = "%d.%d.%d.%d" % tuple(mask)
    return mask


def print_ip_data(netlist) :
    if(output.lower == "cmd"):
        for line in netlist:
            print(line)
    else:
        if(split!=0):
            file_count = 1
            cur_file = open(output + str(file_count) + '.txt','w+')
            file_count = 2
            rest_split = split
            for line in netlist:
                if(rest_split == 0):
                    cur_file.close()
                    cur_file = open(output + str(file_count) + '.txt','w+')
                    file_count = file_count + 1
                    rest_split = split
                cur_file.write(line.exploded + '\r\n')
                rest_split = rest_split - 1
        else:
            out_file = open(output,'w+')
            for line in netlist:
                out_file.write(line.exploded)
                out_file.write('\r\n')
            out_file.close()
    print('共有'+str(len(netlist))+"条路由表！")


def revert_ip_list(netlist):
    if mod == mod_expect:
        s = [ip_network('0.0.0.0/0')]
        for item in netlist:
            ex_subnet = ip_network(item[0]+"/"+str(item[1]))
            i = bisect.bisect_right(s, ex_subnet) - 1
            while i < len(s):
                subnet = s[i]
                if subnet.overlaps(ex_subnet):
                    # since chnroute.txt is sorted, here we are always operating
                    # the last few objects in s, which is almost O(1)
                    del s[i]
                    sub_subnets = list(subnet.address_exclude(ex_subnet))
                    sub_subnets.sort()
                    for sub_subnet in sub_subnets:
                        s.insert(i, sub_subnet)
                        i += 1
                else:
                    break
    else:
        s = []
        for item in netlist:
            ex_subnet = ip_network(item[0]+"/"+str(item[1]))
            s.append(ex_subnet)
    return s

def cmd_help():
    print('chnroute.py')
    print('A python program written by frankzhang')
    print('https://github.com/zjufrankzhang/ChnRoute')
    print('usage chnroute.py [-m mod] [-c country]')
    print('options and arguments')
    print('-h --help   : Display this help')
    print('-m --mod    : Set mod to contain or expect, default is expect selected country')
    print('-c --country: Add country list, split by \',\' .Only Asia countries applies. Default country is \'CN\'')
    print('-o --output : Use \'cmd\' to output to command line (default). Input other vales will create a local file')
    print('-s --split  : Split the output file to more than one files. The integer tells the max lines in a single file')
    print()
    print('You can use \'chnroute.py -m con -c CN -o chnroute\' to output the CN ip address')
    print('You can use \'chnroute.py -m exp -c CN -o outsideCN\' to output the ip address outside CN')
    return


if __name__ == '__main__':
    mod = mod_expect
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hm:c:o:s:", ["mod=","country=","output=","split="])
    except getopt.GetoptError:
        print('syntex error')
        cmd_help()
        sys.exit(2)
    for opt_name, arg_value in opts:
        if opt_name in ('-h','--help'):
            cmd_help()
            sys.exit()
        elif opt_name in ('-m', '--mod'):
            input_mod = arg_value
            if input_mod.lower == 'con' or input_mod.lower == 'contain':
                mod = mod_contain
            else:
                mod = mod_expect
        elif opt_name in ('-c', '--country'):
            country_list = arg_value.split(',')
        elif opt_name in ('-o', '--output'):
            if arg_value.find("\\") != -1:
                #文件路径包含有\字符，会造成转义问题，强制退出
                print("Please do not contain \\ in output def")
                cmd_help()
                sys.exit()
            else:
                output = arg_value

        elif opt_name in ('-s', '--split'):
            try:
                split = int(arg_value)
            except ValueError:
                print('Please input a integer at -s or --split')
                cmd_help()
                sys.exit()

    if len(country_list) == 0:
        country_list.append('CN')
    if len(output) == 0:
        output = 'cmd'
        

    rawdata = fetch_ip_data()
    sortdata = sort_iplist(rawdata)
    netlist = merge_ip_data(sortdata)
    final_list = revert_ip_list(netlist)
    print_ip_data(final_list)
    pass