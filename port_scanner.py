import socket
import subprocess
import sys
from datetime import datetime
import netifaces
import threading
import re
import logging
logging.getLogger('scapy.runtime').setLevel(logging.ERROR)
from scapy.all import sr1, IP, UDP
import argparse
import os
import copy
import netaddr
import yaml
import io

MAX_SIMULTANEOUS_THREADS = 10
SERVICES_FILE = '/etc/services'
TCP_TIMEOUT = 0.01
UDP_TIMEOUT = 0.01
YAML_FILE = 'scanning_results.yaml'


class PortScanner:

    def __init__(self, ip, port, with_udp, verbose, yaml_printout):
        self.with_upd = with_udp
        self.verbose = verbose
        self.yaml_printout = yaml_printout
        self.semaphore = threading.Semaphore(MAX_SIMULTANEOUS_THREADS)
        self.concurrent_threads_lock = threading.Lock()
        self.concurrent_threads = set()
        self.ip_list = []
        self.port_list = []
        self.parse_port(port)
        self.parse_ip(ip)
        self.collect_dict = {'tcp': []}
        if self.with_upd:
            self.collect_dict.update({'udp': []})

    def parse_port(self, port):
        """ parsing port list and range values and create
            a port list out of it:
            -port 1,1001,34-45
            PORT LIST:  [1, 34, 35, 36, 37, 38, 39, 40,
                         41, 42, 43, 44, 45, 1001]
        """
        port_set = set()
        port_list = []
        if ',' in port:
            port_list.extend(port.split(','))
        else:
            port_list.append(port)
        for port in port_list:
            if '-' in port:
                port = port.split('-')
                port_set = port_set.union(
                    set(range(int(port[0]), int(port[1])+1)))
            else:
                port_set.add(int(port))
        self.port_list = sorted(list(port_set))

    def parse_ip(self, ip):
        """ parsing ip list, subnets and range values and create
            an ip list out of it:
            -ip 192.168.0.1,192.168.0.2,192.168.1.0/28,172.16.0.7-8
            IP LIST:  ['172.16.0.7', '172.16.0.8', '192.168.0.1',
                       '192.168.0.2', '192.168.1.1', '192.168.1.2',
                       '192.168.1.3', '192.168.1.4', '192.168.1.5',
                       '192.168.1.6', '192.168.1.7', '192.168.1.8',
                       '192.168.1.9', '192.168.1.10', '192.168.1.11',
                       '192.168.1.12', '192.168.1.13', '192.168.1.14']
        """
        if not ip:
            return
        ip_set = set()
        ip_list = []
        if ',' in ip:
            ip_list.extend(ip.split(','))
        else:
            ip_list.append(ip)

        for ip in ip_list:
            if '/' in ip:
                ip_set = ip_set.union(
                    set([str(i) for i in list(netaddr.IPNetwork(ip))[1:-1]]))
            elif '-' in ip:
                ip_digits = ip.split('.')
                if '-' in ip_digits[-1]:
                    last_ip_digit = ip_digits[-1].split('-')
                    ip_range_list = range(
                        int(last_ip_digit[0]), int(last_ip_digit[-1]) + 1)
                    for i in ip_range_list:
                        ip_digits[-1] = i
                        ip_set.add('.'.join([str(i) for i in ip_digits]))
            else:
                ip_set.add(ip)
        self.ip_list = [
            str(i) for i in sorted(
                [netaddr.IPAddress(i) for i in list(ip_set)])]

    def thread_monitoring(self):
        print ('%s CURRENTLY WORKING THREADS %s' %
               (len(self.concurrent_threads), self.concurrent_threads))
        print 'PORT DICT: %s\n\n' % self.scan_dict

    def port_scan(self, protocol, ip, port_list):
        self.semaphore.acquire()
        with self.concurrent_threads_lock:
            self.concurrent_threads.add(threading.currentThread().getName())
        if self.verbose:
            self.thread_monitoring()

        for port in self.port_list:
            if protocol == 'tcp':
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(TCP_TIMEOUT)
                    result = s.connect_ex((ip, port))
                    if result == 0:
                        port_data = (
                            '%s/%s' % (port, self.services_dict[port])
                            if port in self.services_dict else port)
                        port_list.append(port_data)
                except socket.error:
                    pass
                finally:
                    s.close()
            elif protocol == 'udp':
                udp_scan_resp = sr1(IP(dst=ip)/UDP(dport=port),
                                    timeout=TCP_TIMEOUT, verbose=False)
                if udp_scan_resp and udp_scan_resp.haslayer(UDP):
                    port_data = (
                        '%s/%s' % (port, self.services_dict[port])
                        if port in self.services_dict else port)
                    port_list.append(port_data)

        with self.concurrent_threads_lock:
            self.concurrent_threads.remove(threading.currentThread().getName())
        self.semaphore.release()
        if self.verbose:
            self.thread_monitoring()

    def parse(self, data):
        parsed_list = []
        for l in data.splitlines():
            parsed = []
            if '/tcp' in l or '/udp' in l:
                cluttered = [e.strip() for e in re.split(r'(\t| )', l.strip())]
                for p in cluttered:
                    if p:
                        parsed.append(p)
                parsed_list.append(parsed[:2])
        return parsed_list

    def dictionarize(self, service_list):
        service_dict = {}
        for service in service_list:
            service_dict[int(service[1].split('/')[0])] = service[0]
        return service_dict

    def scan_ips_from_list(self, threads):
        """ Scan IP addresses from the lists, ranges and blocks which have
            been given at startup using input parameter -ip
        """
        print 'PORT LIST:', self.port_list
        print 'IP LIST:', self.ip_list
        for ip in self.ip_list:
            self.scan_dict.update({ip: copy.deepcopy(self.collect_dict)})
        for ip, proto_dict in self.scan_dict.iteritems():
            for protocol, port_list in proto_dict.iteritems():
                thread = threading.Thread(
                    target=self.port_scan,
                    args=(protocol, ip, port_list),)
                thread.setName('SCAN_IP_%s_%s' % (ip, protocol.upper()))
                threads.append(thread)
                thread.start()

    def scan_local_interface_ips(self, threads):
        """ Scan IP addresses of local interfaces
        """
        ip_set = set()
        for iface_name in netifaces.interfaces():
            if_addresses = netifaces.ifaddresses(
                iface_name).setdefault(netifaces.AF_INET)
            if if_addresses:
                ip_addr_list = [i['addr'] for i in if_addresses]
                for ip in ip_addr_list:
                    ip_set.add(ip)
        self.ip_list = [str(i) for i in sorted(
            [netaddr.IPAddress(i) for i in list(ip_set)])]
        self.scan_ips_from_list(threads)

    def printout_scanning_results(self):
        printout_list = []
        printout_dict = {}
        ip_list = []
        for ip in self.ip_list:
            for proto in ['tcp', 'udp']:
                if proto in self.scan_dict[ip] and self.scan_dict[ip][proto]:
                    if ip not in printout_dict:
                        ip_list.append(ip)
                        printout_dict.update({ip: {proto: self.scan_dict[ip][proto]}})
                    else:
                        printout_dict[ip].update({proto: self.scan_dict[ip][proto]})
        for ip in ip_list:
            printout_list.append({ip: printout_dict[ip]})

        if self.yaml_printout:
            with io.open(YAML_FILE, 'w') as stream:
                yaml.dump(printout_list, stream, default_flow_style=False)
            print 'SCANNING RESULTS dumped to', YAML_FILE
        else:
            print 'SCANNING RESULTS:'
            print 30 * '='
            for elem in printout_list:
                ip = elem.keys()[0]
                proto_dict = elem.values()[0]
                print ip
                for proto, port_list in proto_dict.iteritems():
                    print ' ' * 3, proto
                    for port in port_list:
                        print ' ' * 6, port
                print

    def run_scan(self):
        """ Start the scanning process"""
        start_time = datetime.now()
        self.scan_dict = {}
        threads = []

        with open(SERVICES_FILE) as f:
            data= f.read()
        services = self.parse(data)
        self.services_dict = self.dictionarize(services)

        if self.ip_list:
            self.scan_ips_from_list(threads)
        else:
            self.scan_local_interface_ips(threads)

        for thread in threads:
            thread.join()

        # Checking the time again
        end_time = datetime.now()

        # Calculates the difference of time, to see how long it took to run the script
        total =  end_time - start_time

        # Printing the information to screen
        print 'Scanning Completed in: ', total

        self.printout_scanning_results()


def parse_arguments():
    parser = argparse.ArgumentParser(prog='python %s' % __file__)
    parser.add_argument('-ip', dest='ip', action='store',
                        help='ip, ip range, '
                             'by default will take all interface'
                             ' ip addresses on the host')
    parser.add_argument('-port', dest='port', action='store',
                        default='1-65535', nargs='?',
                        help='port, port range')
    parser.add_argument('-u', dest='with_udp', action='store_true',
                        default=False, help='scan UDP ports')
    parser.add_argument('-v', dest='verbose', action='store_true',
                        default=False, help='set verbosity')
    parser.add_argument('-yaml', dest='yaml_printout', action='store_true',
                        default=False, help='Print scanning results '
                                            'to a yaml file')
    args = parser.parse_args()
    print args
    kwargs = {'ip': args.ip, 'port': args.port, 'with_udp': args.with_udp,
              'verbose': args.verbose, 'yaml_printout': args.yaml_printout}
    return kwargs

def main():
    if os.getuid() != 0:
        exit('You need to be root or sudo user to be able to run this application!')
    kwargs = parse_arguments()
    port_scanner = PortScanner(**kwargs)
    port_scanner.run_scan()

if __name__ == '__main__':
    main()

