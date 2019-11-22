#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from threading import *
import random
import time

def drop(percent):
    return random.randrange(100) < percent

def delay(mean, std):
    delay =random.gauss(mean, std)
    print(delay)
    if delay > 0:
        time.sleep(delay/1000)

def get_file_info(key):
    f = open("forwarding_table.txt", "r")
    key = "-"+key
    for line in f:
        line_list = line.split(" ")
        key_index = line_list.index(key)
        if key_index < line_list.len():
            return line_list[key_index + 1]
        else:
            return ""

def switchy_main(net):

    my_intf = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_intf]
    myips = [intf.ipaddr for intf in my_intf]

    random_seed = get_file_info("s")
    random.seed(random_seed) #Extract random seed from params file
    
    probability_of_drop = get_file_info("p")
    mean_delay = get_file_info("dm")
    stand_dev = get_file_info("dstd")


    #blaster on eth0
    #blastee on eth1
    for intf in my_intf:
        if intf.name == "middlebox-eth0":
            blaster_intf = intf
        elif intf.name == "middlebox-eth1":
            blastee.intf = intf

    blaster_mac_addr = "10:00:00:00:00:01"
    blastee_mac_addr = "20:00:00:00:00:01"

    while True:
        gotpkt = True
        try:
            timestamp,dev,pkt = net.recv_packet()
            log_debug("Device is {}".format(dev))
        except NoPackets:
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            log_debug("I got a packet {}".format(pkt))

        if dev == "middlebox-eth0":
            log_debug("Received from blaster")
            '''
            Received data packet 
            Should I drop it?
            If not, modify headers, add a delay & send to blastee
            '''
            if not drop(probability_of_drop):
                delay(mean_delay,stand_dev)
                #TODO not sure which is source
                pkt[0].src = blastee_intf.ethaddr
                pkt[0].dst = blastee_mac_addr
                net.send_packet("middlebox-eth1", pkt)
        elif dev == "middlebox-eth1":
            log_debug("Received from blastee")
            '''
            Received ACK
            Modify headers & send to blaster. Not dropping ACK packets!
            Don't add any delay as well
            '''
            pkt[0].src = blaster_intf.ethaddr
            pkt[0].dst = blaster_mac_addr
            net.send_packet("middlebox-eth0", pkt)
        else:
            log_debug("Oops :))")

    net.shutdown()
