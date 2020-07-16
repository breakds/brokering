#!/usr/bin/env python

from twisted.internet import endpoints
from twisted.internet import protocol
from twisted.internet import defer
from twisted.mail import imap4

from scanner_relay.pipeline import Pipeline
from scanner_relay.authentication import PassStoreFetcher, PlainPasswordFetcher

import logging

# Global configuration for the logging. Note that we set the level to
# INFO so that only DEBUG logging does not get to stdout.
FORMAT = '[%(levelname)s] (%(name)s) %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)

logger = logging.getLogger('run')


class ScannerRelayProtocol(imap4.IMAP4Client):
    def __init__(self, username, password_fetcher, onFinish):
        super().__init__()
        self.pipeline = Pipeline(self, username, password_fetcher, onFinish)
        
    def serverGreeting(self, unused_capabilities):
        """The entry point for the whole program.

        It merely starts the long-running pipeline.
        """
        # NOTE: Although twisted official example suggest using the capabilities
        # returned here to decide what kind of authentication methods to
        # register, I found it to be not true as real capabilities are only
        # returned after the authentication is successful.
        username = self.pipeline.username
        self.registerAuthenticator(imap4.PLAINAuthenticator(username))
        self.registerAuthenticator(imap4.LOGINAuthenticator(username))
        self.registerAuthenticator(
            imap4.CramMD5ClientAuthenticator(username))
        self.pipeline.start()


class ScannerRelayProtocolFactory(protocol.ClientFactory):
    def __init__(self, username, password_fetcher, onFinish):
        super().__init__()
        self.username = username
        self.password_fetcher = password_fetcher
        self.onFinish = onFinish
    

    def buildProtocol(self, addr):
        logger.info('Constructing client protocol to connect to %s:%d', addr.host, addr.port)
        protocol = ScannerRelayProtocol(
            self.username, self.password_fetcher, self.onFinish)
        protocol.factory = self
        return protocol


    def clientConnectionFailed(self, connector, reason):
        print('Connection failed.')


# TODO(breakds): And a more graceful (singal handling) way to terminate the program.
def clean_up(unused):
    from twisted.internet import reactor
    reactor.stop()
    print('All workd done!')


if __name__ == '__main__':
    # FIXME: Make these configurable
    hostname = 'mail.breakds.org'
    username = 'bds@breakds.org'.encode('ascii')
    pass_store_entry = 'mail.breakds.org/bds'
    port = 143

    from twisted.internet import reactor
    endpoint = endpoints.HostnameEndpoint(reactor, hostname, port)

    factory = ScannerRelayProtocolFactory(
        username, PassStoreFetcher(pass_store_entry), clean_up)
    endpoint.connect(factory)
    reactor.run()
