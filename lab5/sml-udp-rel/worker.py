from ipaddress import IPv4Address
from scapy.all import Packet
from scapy.config import conf
from scapy.fields import ByteField
from scapy.packet import Raw
from socket import AF_INET
from socket import SOCK_DGRAM
from socket import socket
from socket import timeout
from struct import iter_unpack
from struct import pack
from lib.comm import unreliable_receive
from lib.comm import unreliable_send
from lib.gen import GenInts
from lib.gen import GenMultipleOfInRange
from lib.test import CreateTestData
from lib.test import RunIntTest
from lib.worker import GetRankOrExit
from lib.worker import ip
from lib.worker import Log
from config import NUM_WORKERS

NUM_ITER = 1
CHUNK_SIZE = 32

SRC_IP_ADDR = ip()
DST_IP_ADDR = ""
for route in conf.route.routes:
    if SRC_IP_ADDR in route:
        DST_IP_ADDR = str(IPv4Address(route[0]))
        break

SRC_PORT = 38787
DST_PORT = 38787

IP_HEADER_LEN = 20
UDP_HEADER_LEN = 8
SWITCH_ML_HEADER_LEN = 2
UDP_TOTAL_LEN = UDP_HEADER_LEN + SWITCH_ML_HEADER_LEN + CHUNK_SIZE * 4
IP_TOTAL_LEN = IP_HEADER_LEN + UDP_TOTAL_LEN


class SwitchML(Packet):
    name = "SwitchMLPacket"
    fields_desc = [
        ByteField("rank", 0),
        ByteField("num_workers", 1),
        ByteField("chunk_id", 0)  # even or odd
    ]


def AllReduce(soc, rank, data, result):
    """
    Perform reliable in-network all-reduce over UDP

    :param str    soc: the socket used for all-reduce
    :param int   rank: the worker's rank
    :param [int] data: the input vector for this worker
    :param [int]  res: the output vector

    This function is blocking, i.e. only returns with a result or error
    """

    for i in range(len(data) // CHUNK_SIZE):
        payload = bytearray()
        for num in data[CHUNK_SIZE*i:CHUNK_SIZE*(i+1)]:
            payload.extend(pack("!I", num))
        pkt_snd = bytes(
            SwitchML(rank=rank, num_workers=NUM_WORKERS, chunk_id=i & 0x1) /
            Raw(payload)
        )
        while 1:
            unreliable_send(soc, pkt_snd, (DST_IP_ADDR, DST_PORT), 0)
            soc.settimeout(0.04)
            try:
                pkt_recv, _ = unreliable_receive(soc, len(pkt_snd))
                # chunk id match
                if SwitchML(pkt_snd).chunk_id == SwitchML(pkt_recv).chunk_id:
                    byte_data = SwitchML(pkt_recv).payload.load
                    for j, num in enumerate(iter_unpack("!I", byte_data)):
                        result[i * CHUNK_SIZE + j] = num[0]
                    break
            except timeout:
                pass


def main():
    rank = GetRankOrExit()

    s = socket(family=AF_INET, type=SOCK_DGRAM)
    s.bind((SRC_IP_ADDR, SRC_PORT))

    Log("Started...")
    for i in range(NUM_ITER):
        # You may want to 'fix' num_elem for debugging
        num_elem = GenMultipleOfInRange(2, 2048, 2 * CHUNK_SIZE)
        data_out = GenInts(num_elem)
        data_in = GenInts(num_elem, 0)
        CreateTestData(f"udp-rel-iter-{i}", rank, data_out)
        AllReduce(s, rank, data_out, data_in)
        RunIntTest(f"udp-rel-iter-{i}", rank, data_in, True)
    Log("Done")
    s.close()


if __name__ == "__main__":
    main()
