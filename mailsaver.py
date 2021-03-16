import base64

from requests import Session
from bs4 import BeautifulSoup

from izonemail import Mail


MAIL_HEADER = """
<header>
    <div style="display: flex; align-items: center; padding: 10px 16px;">
        <img src="{{MEMBER_IMAGE}}" style="border-radius: 50%; width: 50px; margin-right: 10px;">
        <div style="width: 100%; display: flex; flex-direction: column;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 2px">
                <span style="font-weight: bold;">{{SENDER}}</span>
                <div style="color: #ccc;">{{RECEIVED}}</div>
            </div>
            <div style="font-size: 0.9em;">
                <span>To: </span>
                <span style="color: #888;">{{USERNAME}}</span>
            </div>

        </div>
    </div>
    <hr style="margin: 0; border: 0; border-top: 1px solid #eee;">
    <div style="padding: 16px 16px; font-size: 1.2em; font-weight: bold;">{{MAILTITLE}}</div>
    <hr style="margin: 0; border: 0; border-top: 1px solid #eee;">
</header>
"""


class MailSaver:
    def __init__(self, username):
        self._s = Session()
        self._username = username

    def dump(self, fp, mail: Mail, mail_detail: bytes):
        # replace all tokens and build a soup
        header = MAIL_HEADER.replace('{{MEMBER_IMAGE}}', mail.member.image_url, 1) \
                            .replace('{{SENDER}}', mail.member.name, 1) \
                            .replace('{{RECEIVED}}', mail.received.strftime('%Y/%m/%d %H:%M'), 1) \
                            .replace('{{USERNAME}}', self._username, 1) \
                            .replace('{{MAILTITLE}}', mail.subject, 1)
        header = BeautifulSoup(header, 'lxml').header

        # parse markup of the mail and inserts header just before the main content
        markup = BeautifulSoup(mail_detail, 'lxml')
        markup.select_one('#mail-detail').insert_before(header)

        # remove unnessesary scripts
        for e in markup.find_all('script'):
            e.decompose()

        # replace all images to base64
        for e in markup.find_all('img'):
            res = self._s.get(e['src'])
            content_type = res.headers['content-type']
            encoded_body = base64.b64encode(res.content)
            e['src'] = f'data:{content_type};base64,{encoded_body.decode()}'

        # save the markup to the given fp
        fp.write(str(markup))
