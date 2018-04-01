import wifi
import usocket as socket
import ustruct as struct

class MQTTException(Exception):
    pass

class MQTTClient:

    def __init__(self, client_id, server, port=1883):
        # This will immediately return if we're already connected, otherwise
        # it'll attempt to connect or prompt for a new network. Proceeding
        # without an active network connection will cause the getaddrinfo to
        # fail.
        wifi.connect(
            wait=True,
            show_wait_message=False,
            prompt_on_fail=True,
            dialog_title='TiLDA Wifi'
        )

        self.client_id = client_id
        self.sock = None
        self.addr = socket.getaddrinfo(server, port)[0][-1]
        self.pid = 0
        self.cb = None

    def _send_str(self, s):
        self.sock.send(struct.pack("!H", len(s)))
        self.sock.send(s)

    def _recv_len(self):
        n = 0
        sh = 0
        while 1:
            b = self.sock.recv(1)[0]
            n |= (b & 0x7f) << sh
            if not b & 0x80:
                return n
            sh += 7

    def set_callback(self, f):
        self.cb = f

    def connect(self, clean_session=True):
        self.sock = socket.socket()
        self.sock.connect(self.addr)
        msg = bytearray(b"\x10\0\0\x04MQTT\x04\x02\0\0")
        msg[1] = 10 + 2 + len(self.client_id)
        msg[9] = clean_session << 1
        self.sock.send(msg)
        #print(hex(len(msg)), hexlify(msg, ":"))
        self._send_str(self.client_id)
        resp = self.sock.recv(4)
        assert resp[0] == 0x20 and resp[1] == 0x02
        if resp[3] != 0:
            raise MQTTException(resp[3])
        return resp[2] & 1

    def disconnect(self):
        self.sock.send(b"\xe0\0")
        self.sock.close()

    def ping(self):
        self.sock.send(b"\xc0\0")
        self.sock.close()

    def publish(self, topic, msg, retain=False, qos=0):
        pkt = bytearray(b"\x30\0\0")
        pkt[0] |= qos << 1 | retain
        sz = 2 + len(topic) + len(msg)
        if qos > 0:
            sz += 2
        assert sz <= 16383
        pkt[1] = (sz & 0x7f) | 0x80
        pkt[2] = sz >> 7
        #print(hex(len(pkt)), hexlify(pkt, ":"))
        self.sock.send(pkt)
        self._send_str(topic)
        if qos > 0:
            self.pid += 1
            pid = self.pid
            buf = bytearray(b"\0\0")
            struct.pack_into("!H", buf, 0, pid)
            self.sock.send(buf)
        self.sock.send(msg)
        if qos == 1:
            while 1:
                op = self.wait_msg()
                if op == 0x40:
                    sz = self.sock.recv(1)
                    assert sz == b"\x02"
                    rcv_pid = self.sock.recv(2)
                    rcv_pid = rcv_pid[0] << 8 | rcv_pid[1]
                    if pid == rcv_pid:
                        return
        elif qos == 2:
            assert 0

    def subscribe(self, topic, qos=0):
        assert self.cb is not None, "Subscribe callback is not set"
        pkt = bytearray(b"\x82\0\0\0")
        self.pid += 1
        struct.pack_into("!BH", pkt, 1, 2 + 2 + len(topic) + 1, self.pid)
        #print(hex(len(pkt)), hexlify(pkt, ":"))
        self.sock.send(pkt)
        self._send_str(topic)
        self.sock.send(qos.to_bytes(1))
        resp = self.sock.recv(5)
        #print(resp)
        assert resp[0] == 0x90
        assert resp[2] == pkt[2] and resp[3] == pkt[3]
        if resp[4] == 0x80:
            raise MQTTException(resp[4])

    # Wait for a single incoming MQTT message and process it.
    # Subscribed messages are delivered to a callback previously
    # set by .set_callback() method. Other (internal) MQTT
    # messages processed internally.
    def wait_msg(self):
        res = self.sock.recv(1)
        if res is None:
            return None
        self.sock.setblocking(True)
        if res == b"":
            raise OSError(-1)
        if res == b"\xd0":  # PINGRESP
            sz = self.sock.recv(1)[0]
            assert sz == 0
            return None
        op = res[0]
        if op & 0xf0 != 0x30:
            return op
        sz = self._recv_len()
        topic_len = self.sock.recv(2)
        topic_len = (topic_len[0] << 8) | topic_len[1]
        topic = self.sock.recv(topic_len)
        sz -= topic_len + 2
        if op & 6:
            pid = self.sock.recv(2)
            pid = pid[0] << 8 | pid[1]
            sz -= 2
        msg = self.sock.recv(sz)
        self.cb(topic, msg)
        if op & 6 == 2:
            pkt = bytearray(b"\x40\x02\0\0")
            struct.pack_into("!H", pkt, 2, pid)
            self.sock.send(pkt)
        elif op & 6 == 4:
            assert 0

    # Checks whether a pending message from server is available.
    # If not, returns immediately with None. Otherwise, does
    # the same processing as wait_msg.
    def check_msg(self):
        self.sock.setblocking(False)
        return self.wait_msg()
