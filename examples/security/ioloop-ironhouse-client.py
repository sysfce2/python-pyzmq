#!/usr/bin/env python

'''
Ironhouse extends Stonehouse with client public key authentication.

This is the strongest security model we have today, protecting against every
attack we know about, except end-point attacks (where an attacker plants
spyware on a machine to capture data before it's encrypted, or after it's
decrypted).

This example demonstrates using the IOLoopAuthenticator.

Author: Chris Laws
'''

import datetime
import os
import zmq
import zmq.auth
from zmq.eventloop import ioloop, zmqstream


class IronhouseClient(object):
    ''' Ironhouse Client '''

    def __init__(self, context, client_cert_file, server_cert_file, endpoint='tcp://127.0.0.1:9000'):
        self.context = context
        self.endpoint = endpoint
        self.socket = None
        self.stream = None
        # We need two certificates, one for the client and one for
        # the server. The client must know the server's public key
        # to make a CURVE connection.
        self.public, self.secret = zmq.auth.load_certificate(client_cert_file)
        self.server_public, _ = zmq.auth.load_certificate(server_cert_file)

    def start(self):
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.curve_secretKey = self.secret
        self.socket.curve_publicKey = self.public
        self.socket.curve_serverKey = self.server_public
        self.stream = zmqstream.ZMQStream(self.socket, ioloop.IOLoop.instance())
        self.stream.on_recv(self.on_message)
        self.socket.connect('tcp://127.0.0.1:9000')

        msg = [str(datetime.datetime.now())]
        print "sending request"
        self.socket.send_multipart(msg)

    def stop(self):
        self.stream.close()

    def on_message(self, frames):
        print "received reply"
        # Shutdown on receipt of a message
        ioloop.IOLoop.instance().add_timeout(0.1, ioloop.IOLoop.instance().stop)


if __name__ == '__main__':
    import logging
    import sys

    if zmq.zmq_version_info() < (4,0):
        raise RuntimeError("Security is not supported in libzmq version < 4.0. libzmq version {0}".format(zmq.zmq_version()))

    verbose = False
    if '-v' in sys.argv:
        verbose = True

    if verbose:
        logging.basicConfig(format='%(asctime)-15s %(levelname)s %(message)s',
                            level=logging.DEBUG)

    # These direcotries are generated by the generate_keys script
    base_dir = os.path.dirname(__file__)
    keys_dir = os.path.join(base_dir, 'certificates')
    public_keys_dir = os.path.join(base_dir, 'public_keys')
    secret_keys_dir = os.path.join(base_dir, 'private_keys')

    if not (os.path.exists(keys_dir) and os.path.exists(keys_dir) and os.path.exists(keys_dir)):
        print "Certificates are missing - run generate_certificates script first"
        sys.exit(1)

    ctx = zmq.Context().instance()
    client_cert_file = os.path.join(secret_keys_dir, "client.key_secret")
    server_cert_file = os.path.join(public_keys_dir, "server.key")
    iron_client = IronhouseClient(ctx, client_cert_file, server_cert_file)
    iron_client.start()

    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass
