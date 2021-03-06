#!/usr/bin/env python
"""Describe file"""


from mailparser.mailparser import parse_mail


class magicdict(dict):pass


def test_parse_mail(mocker):
    pf = magicdict(
        imap=magicdict(
            host='',
            username='',
            password='',
            port='',
        ),
        logging=dict(version=1),
        Handlers=[magicdict(handler='handler', sender='sender', subject='subject')],
    )
    mocker.patch('mailparser.mailparser.pfread').return_value = pf
    mocker.patch('mailparser.mailparser.import_module')
    h = mocker.patch('mailparser.mailparser.ImapHelper').login()
    h.get_new.return_value = [{'from': 'from', 'subject': 'subject'}]
    parse_mail(None)
