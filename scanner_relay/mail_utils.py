import re

def parse_mailboxes(imap_mailboxes):
    """Translates the twisted imap4 result of listing mailboxes into a
    list of names of mailboxes.

    """
    return [entry[2] for entry in imap_mailboxes]


class MailboxInfo(object):
    def __init__(self, read_only, total_count, has_unseen):
        self.read_only = read_only
        self.total_count = total_count
        self.has_unseen = has_unseen


def parse_mailbox_info(imap_mailbox_info):
    """Translates the twisted imap4 result of mailbox summary into an
    easier to interpret object.

    The input is actually a dictionary. A sample input looks like:

    {'READ-WRITE': True, 'FLAGS': ('\\Answered', '\\Flagged',
    '\\Deleted', '\\Seen', '\\Draft', '$Forwarded'), 'PERMANENTFLAGS':
    ('\\Answered', '\\Flagged', '\\Deleted', '\\Seen', '\\Draft',
    '$Forwarded', '\\*'), 'EXISTS': 21, 'RECENT': 0, 'UNSEEN': 21,
    'UIDVALIDITY': 1573433320, 'UIDNEXT': 251}

    """
    read_only = not imap_mailbox_info.get('READ-WRITE', False)
    total_count = imap_mailbox_info.get('EXISTS', 0)
    has_unseen = bool(imap_mailbox_info.get('UNSEEN', 0))
    return MailboxInfo(read_only, total_count, has_unseen)


class AttachmentInfo(object):
    def __init__(self, title, filename, encoding, payload_start_index):
        self.title = title
        self.filename = filename
        self.encoding = encoding
        self.payload_start_index = payload_start_index


def parse_mail_attachment(imap_mail_text):
    """Extrat the attachment information from the twisted imap4 result of
    fetching the TEXT part of a message that represents an attachment.

    The input is a binary stream.

    Returns an AttachmentSummary object.

    """

    def get_lines(binary_stream):
        """This generate produces a stream of lines from the input binary stream.

        lines are separated by a '\n' followed by a '\r'.

        Besides the line, it also yields the start index of next line.
        If the index returned is -1, it indicates the end of the stream.
        """
        line = ''
        expect_new_line = False
        for i, char in enumerate(binary_stream):
            if char in ['\n', '\r']:
                if expect_new_line:
                    expect_new_line = False
                else:
                    yield line, i + 2
                    line = ''
                    expect_new_line = True
            else:
                line += char
        yield line, -1

    ATTACHMENT_TITLE_PATTERN = re.compile('\-+(.*)')
    title = ''
    ATTACHMENT_FILENAME_PATTERN = re.compile('\s*filename="(.*)"')
    filename = ''
    ATTACHMENT_ENCODING_PATTERN = re.compile('Content-Transfer-Encoding:\s+(.*)')
    encoding = ''
    payload_start_index = -1

    for line, next_index in get_lines(imap_mail_text):
        if len(line) == 0 or next_index < 0:
            payload_start_index = next_index
            break
        else:
            r = ATTACHMENT_TITLE_PATTERN.fullmatch(line)
            if r is not None:
                title = r.group(1)
                continue
            r = ATTACHMENT_FILENAME_PATTERN.fullmatch(line)
            if r is not None:
                filename = r.group(1)
                continue
            r = ATTACHMENT_ENCODING_PATTERN.fullmatch(line)
            if r is not None:
                encoding = r.group(1)
                continue
    return AttachmentInfo(title, filename, encoding, payload_start_index)


__all__ = ['parse_mailboxes', 'parse_mailbox_info', 'parse_mail_attachment']
