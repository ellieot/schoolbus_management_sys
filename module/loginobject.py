'''
Author: Resunoon
Date: 2020-10-18 22:25:30
LastEditTime: 2020-12-06 14:44:32
LastEditors: Resunoon
Description: 最后写亿行
'''
from bs4 import BeautifulSoup as bs
import requests
import execjs


class loginobj():
    def __init__(self, username, password):
        self.head = {
            'Host': 'authserver.nuist.edu.cn',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1',
            'Origin': 'https://authserver.nuist.edu.cn',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Referer': r'https://authserver.nuist.edu.cn/authserver/login?service=https://my.nuist.edu.cn%2Findex.portal',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9'}
        self.url = r'https://authserver.nuist.edu.cn/authserver/login'
        self.param = r'?service=https://my.nuist.edu.cn'
        self.username = username
        self.password = password

    # 检查是否需要验证码,不需要返回False
    def checkcaptcha(self):
        captchaurl = f'https://authserver.nuist.edu.cn/authserver/checkNeedCaptcha.htl?username={self.username}'
        captchapage = requests.get(captchaurl, headers=self.head)
        needcaptcha = captchapage.text.find('false')
        if needcaptcha == -1:
            return True
        else:
            return False

    def login(self):
        sess = requests.sessions.Session()
        loginpage = sess.get(self.url+self.param, headers=self.head)

        # 实例化bs对象
        soup = bs(loginpage.text, 'html.parser')

        # 获得Encryptsalt
        passwordsalt = soup.find('input', id='pwdEncryptSalt')['value']

        # 加密密码
        encrypt = execjs.compile(open(r'./static/js/encrypt.js').read())
        sp = encrypt.call('encryptPassword', self.password, passwordsalt)

        # 获取execution
        execution = soup.find('input', id='execution')['value']

        username = self.username
        # 打包post数据
        payload = {
            'username': username,
            'password': sp,
            'captcha': '',
            '_eventId': 'submit',
            'cllt': 'userNameLogin',
            'lt': '',
            'execution': execution
        }

        # 发送第二次请求
        postpage = sess.post(
            self.url+self.param,
            data=payload,
            headers=self.head,
            allow_redirects=False)

        # 如果没有获得ticket，视为出错
        location = postpage.headers.get('Location')
        if location is None or location.find('ticket') == -1:
            print('error')
            return False

        # 如果获得ticket，说明登录成功
        return True
