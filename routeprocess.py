import sys
import getopt
from ipaddress import ip_network
from IPy import IP, IPSet
from tqdm import tqdm

mod_expect = 'expect'
mod_union = 'union'
mod = 'expect'
ipversion_v4only = 'ipv4'
ipversion_v6only = 'ipv6'
ipversion_all = 'all'
ipversion = 'all'

split = 0


def read_ip_data_from_file(input_file_path, input_ip_set=IPSet(), mod=mod_union):
    try:
        f = open(input_file_path)
        lines = f.readlines()
        output_ipset = input_ip_set
        progressBar = tqdm(total=len(lines))
        progressBar.set_description('Processing:')
        for line in lines:
            progressBar.update(1)
            if(line.replace('\n', '').replace('\r', '').strip() == ''):
                continue
            temp_ip = IP(line)
            if(ipversion == ipversion_v4only):
                if(temp_ip._ipversion == 6):
                    continue
            if(ipversion == ipversion_v6only):
                if(temp_ip._ipversion == 4):
                    continue
            if(mod == mod_expect):
                output_ipset.discard(temp_ip)
            else:
                output_ipset.add(temp_ip)
        f.close()
        progressBar.close()
    except IOError:
        print("File ", input_file_path, "is not accessible.")
        sys.exit()
    return output_ipset



def print_ip_data(input_ip_set:IPSet, output_path) :
    if(output_path == 'cmd'):
        for ip in input_ip_set:
            print(ip.strNormal(1))
        return
    if(output_path.strip() != ''):
        try:
            f = open(output_path,'w')
            for ip in input_ip_set:
                strprint = ip.strNormal(1)
                if(ip.prefixlen()==32):
                    strprint += '/32'
                print(strprint,file=f)
            f.close()
        except IOError:
            print("File ", output_path, "is not accessible.")
            sys.exit()

    return



def cmd_help():
    print('routeprocess.py')
    print('A python program written by frankzhang')
    print('https://github.com/zjufrankzhang/ChnRoute')
    print('options and arguments')
    print('-h --help   : Display this help')
    print('-i --input1 : Set input file location')
    print('-j --input2 : Set the second input file location')
    print('-u --union  : Set mod to Union')
    print('-e --expect : Set mod to Expect (Default), this will output the network address in input but not in input2 ([input1] - [input2]), if input1 is missing, "0.0.0.0/0" and "::" will instead')
    print('--v4only    : output only IPV4 data')
    print('--v6only    : output only IPV6 data')
    print('--allversion: output all ip version data (default)')
    print('-o --output : Use \'cmd\' to output to command line (default). Input other vales will create a local file')
    print()
    print('You can use \'chnroute.py -e -j cn.txt -o outsideCN.txt\' to output the ip network not in cn.txt')
    print('You can use \'chnroute.py -u -i all.txt -o all_renew.txt\' to sort and union the ip addresses in all.txt')
    return


if __name__ == '__main__':
    mod = mod_expect
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hi:j:meo:s:", ["input1=","input2=","output=","split=","union","expect","v4only","v6only","allversion"])
    except getopt.GetoptError:
        print('syntex error')
        cmd_help()
        sys.exit(2)
    
    output_path = ''
    input1_file_path = ''
    input2_file_path = ''

    for opt_name, arg_value in opts:
        if opt_name in ('-h','--help'):
            cmd_help()
            sys.exit()
        elif opt_name in ('-u', '--union'):
            mod = mod_union
        elif opt_name in ('-e', '--expect'):
            mod = mod_expect
        elif opt_name in ('--v4only'):
            ipversion=ipversion_v4only
        elif opt_name in ('--v6only'):
            ipversion=ipversion_v6only
        elif opt_name in ('--allversion'):
            ipversion=ipversion_all
        elif opt_name in ('-i', '--input1'):
            input1_file_path = arg_value
        elif opt_name in ('-j', '--input2'):
            input2_file_path = arg_value
        elif opt_name in ('-o', '--output'):
            #if arg_value.find("\\") != -1:
                #文件路径包含有\字符，会造成转义问题，强制退出
            #    print("Please do not contain \\ in output def")
            #    cmd_help()
            #    sys.exit()
            #else:
            output_path = arg_value

        elif opt_name in ('-s', '--split'):
            try:
                split = int(arg_value)
            except ValueError:
                print('Please input a integer at -s or --split')
                cmd_help()
                sys.exit()

    if  len(output_path) == 0:
        output_path = 'cmd'
        
    if mod == mod_union:
        if input1_file_path.strip() == '':
            print('Please set input1 file location in union mod')
            cmd_help()
            sys.exit(2)
    
    if mod == mod_expect:
        if input2_file_path.strip() == '':
            print('Please set input2 file location in expect mod')
            cmd_help()
            sys.exit(2)
    
    if(mod == mod_union):
        if(input1_file_path.strip() != ''):
            final_ipset = read_ip_data_from_file(input1_file_path)
        if(input2_file_path.strip() != ''):
            final_ipset = read_ip_data_from_file(input2_file_path, final_ipset)

    if(mod == mod_expect):
        if(input1_file_path.strip() != ''):
            final_ipset = read_ip_data_from_file(input1_file_path)
        else:
            final_ipset = IPSet([IP("0.0.0.0/0"),IP("::/0")])
            if(ipversion == ipversion_v4only):
                final_ipset = IPSet(IP("0.0.0.0/0"))
            if(ipversion == ipversion_v6only):
                final_ipset = IPSet(IP("::/0"))
        final_ipset = read_ip_data_from_file(input2_file_path, final_ipset, mod)
    
    print_ip_data(final_ipset, output_path)
    
    pass