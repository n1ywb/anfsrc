#!/usr/bin/env python
"""Describe file"""


import pytest

from mailparser.imap import ImapHelper, logouting
from mailparser.mailparser import parse_mail


class FakePF(dict):
    auto_convert = False


def test_one(mocker, construction_report_emails, imapkwargs):
    pf = FakePF(
        Handlers=[dict(
            handler='anfconstruction',
            sender='.*',
            subject='.*')],
        imap=dict(
            host='192.168.56.101',
            username='imaptest',
            password='imaptest',
            port='imap',
            mailbox='test',
        ),
    )
    mocker.patch('mailparser.mailparser.pfread').return_value = pf
    parse_mail(mocker.Mock())
    del pf['imap']['mailbox']
    h = ImapHelper(**pf['imap']).login()
    with logouting(h):
        new = list(h.getnew())
        assert len(new) == 1
        print new
        n, flags, msg = new[0]
        h.store(n, '+FLAGS', '\\Deleted')

