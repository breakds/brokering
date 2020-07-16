import logging
import base64
import pathlib
import time
from functools import reduce

from tqdm import tqdm

from twisted.internet import defer
from twisted.mail import imap4

from scanner_relay.mail_utils import parse_mailboxes, parse_mailbox_info, parse_mail_attachment


logger = logging.getLogger('pipeline')

def _authenticate(pipeline):
    def handle_authentication_error(failure, username):
        failure.trap(imap4.NoSupportedAuthentication)
        logger.error('Cannot login to %s', username)

    password = pipeline.password_fetcher.FetchPassword().encode('ascii')
    logger.info('Authenticating with the host ...')
    return pipeline.protocol.authenticate(password) \
                            .addCallback(_list_mailboxes, pipeline) \
                            .addErrback(handle_authentication_error, pipeline.username)


def _list_mailboxes(auth_result, pipeline):
    def handle_list_mailboxes_error(failure):
        logger.error('Cannot list mailboxes - %s', failure)

    logger.debug('Auth result: %s', auth_result)
    return pipeline.protocol.list('', '*') \
                            .addCallback(_select_mailbox, pipeline) \
                            .addErrback(handle_list_mailboxes_error)


def _select_mailbox(mailboxes, pipeline):
    """Go through the list of returned mailboxes, find the one with an
    identifier (name) that matches the target mailbox defined in the
    pipeline.

    """
    def handle_error(failure):
        logger.error('Failed to select the desired mailbox - %s', failure)
    
    # Now looking for the target mailbox with a name match. The match
    # is NOT case sensitive.
    identifiers = parse_mailboxes(mailboxes)
    chosen = None
    for ident in identifiers:
        if ident.upper() == pipeline.target_mailbox.upper():
            chosen = ident
            break
    if chosen is None:
        logger.error('Cannot find a mailbox that matches "%s". Will abort.',
                     pipeline.target_mailbox)

    return pipeline.protocol.select(chosen) \
                            .addCallback(_poll_qualified_mails, pipeline) \
                            .addErrback(handle_error)


def _poll_qualified_mails(target_mailbox_info, pipeline):
    def handle_error(failure):
        logger.error('IMAP4 search failed because of {}'.format(failure))

    if target_mailbox_info is not None:
        summary = parse_mailbox_info(target_mailbox_info)
        logger.info('  Read-only: {}, Total: {}, Has Unseen: {}'.format(
            summary.read_only, summary.total_count, summary.has_unseen))
    return pipeline.protocol.search(imap4.Query(unseen=True), uid=True) \
                            .addCallback(_fetch_qualified_mails, pipeline) \
                            .addErrback(handle_error)


def _fetch_qualified_mails(uids, pipeline):
    def handle_error(failure):
        logger.error('IMAP4 fetch failed because of {}'.format(failure))

    if len(uids) == 0:
        logger.info('Found no qualified mails.')
        return _next_round(None, pipeline)

    logger.info('Found {} preliminary qualified mails.'.format(len(uids)))

    messages = reduce(lambda x, y: x + imap4.MessageSet(y), uids, imap4.MessageSet())

    # Set peek = True to avoid accidentally flag an irrelevant message.
    return pipeline.protocol.fetchSpecific(messages, uid=True, headerType='TEXT', peek=True) \
                            .addCallback(_process_qualified_mails, pipeline) \
                            .addErrback(handle_error)


def _process_qualified_mails(mail_bodies, pipeline):
    def handle_error(failure):
        logger.error('failed to process qualified mails - {}'.format(failure))
    
    processed = imap4.MessageSet()
    for body in mail_bodies.values():
        uid = int(body[0][1])
        summary = parse_mail_attachment(body[0][4])
        if summary.title.find('CANON') and summary.payload_start_index > 0:
            processed += imap4.MessageSet(uid)
            path = pathlib.Path(pipeline.local_store, summary.filename)
            with open(path, 'wb') as f:
                f.write(base64.urlsafe_b64decode(body[0][4][summary.payload_start_index:]))
            logger.info('Successfully downloaded {}'.format(path))

    logger.info('Processed {} scanned files'.format(len(processed)))

    if len(processed) == 0:
        return _next_round(None, pipeline)

    return pipeline.protocol.addFlags(processed, ['\\Seen'], uid=True) \
                            .addCallback(_next_round, pipeline) \
                            .addErrback(handle_error)


def _next_round(unused, pipeline):
    logger.info('Schedule next poll in {} seconds'.format(pipeline.poll_interval))
    for i in tqdm(range(pipeline.poll_interval)):
        time.sleep(1)
    return _poll_qualified_mails(None, pipeline)

class Pipeline(object):
    def __init__(self, protocol, username, password_fetcher, onFinish):
        def handle_initialize_error(reason):
            logger.error('Failed to initialize mail server authentication due to:\n %s',
                         reason)

        self.protocol = protocol
        self.username = username
        self.password_fetcher = password_fetcher
        # TODO(breakds): Hardcode INBOX for now but in the future may
        # make it configurable if needed.
        self.target_mailbox = 'INBOX'
        # FIXME: make these configurable
        self.local_store = '/home/breakds/Documents'
        self.poll_interval = 10
        self.deferred_chain = defer.Deferred() \
                                   .addCallback(_authenticate) \
                                   .addErrback(handle_initialize_error) \
                                   .addBoth(onFinish)


    def start(self):
        self.deferred_chain.callback(self)


__all__ = ['Pipeline']
