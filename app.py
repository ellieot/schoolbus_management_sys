'''
Author: Resunoon
Date: 2020-10-07 18:20:37
LastEditTime: 2020-12-24 18:05:30
LastEditors: Resunoon
Description:
FilePath: \Pycar\app.py
最后写亿行
'''

from common import common
import os
import time
import pymysql
import datetime
import psutil
from flask import Flask, render_template, request, session, make_response, redirect
import module.loginobject as loginobject
import module.config as db
app = Flask(__name__, static_url_path='/',
            static_folder='./static', template_folder='./templates')
app.secret_key = os.urandom(24)

# 路由模块开始 #
###############


# 404页面
@app.errorhandler(404)
def pagenotfound(error):
    return redirect('/')


# 登录页面
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    elif request.method == 'POST':
        # 登录准备
        username = request.form.get('username')
        password = request.form.get('password')
        lgobj = loginobject.loginobj(username, password)
        if username == '' or password == '':
            return redirect('/')
        if username == 'admin' and password == '123':
            session['username'] = 'admin'
            return redirect('/admin')
        # 开始登录, 由于学校奇怪的防御机制, 很多时候不知道为什么会出错, 所以多试几次
        trialtime = 3
        for i in range(0, trialtime):
            # 需要验证码
            if lgobj.checkcaptcha() == True:
                return '''
                    用户认证失败，请去信息门户输入验证码登录一遍, 3秒后跳转
                    <script type="text/javascript">function jump(){
                        window.location.href='https://www.nuist.edu.cn/';}
                        setTimeout(jump,3000);</script>'''
            # endif

            # 登录成功
            if lgobj.login() == True:
                # 自动登录开关打开, 保存永久cookie
                if request.form.get('rememberme') == 'on':
                    session['username'] = username
                    session.permanent = True
                    app.permanent_session_lifetime = datetime.timedelta(
                        days=365*4)
                    return redirect('/index')
                else:
                    # 临时登录保存session 5分钟
                    session['username'] = username
                    session.permanent = True
                    app.permanent_session_lifetime = datetime.timedelta(
                        minutes=5)
                    return redirect('/index')
            time.sleep(1)
    else:
        return '错误的请求方式'

    return '登录失败'


# 二维码页面(主页面)
@app.route('/index', methods=["GET"])
def index():
    if session.get("username") is None:
        return redirect('/')
    # 获取订单号
    code = getcode()
    # 插入订单号
    insertorder(code)
    # 获得学生钱包信息
    money = getstumoney()
    # 获得公告
    cast = getbroadcast()
    return render_template('index.html', secretcode=code, index="active", money=money, cast=cast)


# 二维码页面(主页面)调试界面
@app.route('/index/debug', methods=["GET"])
def indexdebug():
    if session.get("username") is None:
        return redirect('/')
    # 获取订单号
    code = getcode()
    # 插入订单号
    insertorder(code)
    # 获得学生钱包信息
    money = getstumoney()
    return render_template('indexdebug.html', secretcode=code, index="active", money=money)


# 校车页面
@app.route('/map', methods=["GET"])
def map():
    return render_template('map.html', map="active")


# 充值页面
@app.route('/charge')
def charge():
    if session.get("username") is None:
        return redirect('/')

    return render_template('charge.html')

# 查看充值记录


@app.route('/chargehistory')
def chargehistory():
    if session.get("username") is None:
        return redirect('/')
    history = getchargehistory(session.get('username'))
    return render_template("chargehistory.html", my="active", chargeinfo=history)


# 查看乘车记录
@app.route('/takehistory')
def tekehistory():
    if session.get("username") is None:
        return redirect('/')
    takeinfo = gettakehistory(session.get('username'))
    return render_template("takehistory.html", my="active", takeinfo=takeinfo)


# 后台主页面
@app.route('/admin')
def admin():
    if session.get("username") is None:
        return redirect('/')
    if not session.get("username") == 'admin':
        return redirect('/')
    cpu = getcpustat()
    memory = getmemorystat()
    return render_template('admin.html', cpu=cpu, memory=memory, admin="active")


# 后台订单页面
@app.route("/order")
def order():
    if session.get("username") is None:
        return redirect('/')
    if not session.get("username") == 'admin':
        return redirect('/')
    orders = getorder()
    return render_template("order.html", orders=orders, order="active")


# 后台公告查询页面
@app.route("/broadcast")
def broadcast():
    if session.get("username") is None:
        return redirect('/')
    if not session.get("username") == 'admin':
        return redirect('/')
    broad = getbroadcast()
    return render_template("broadcast.html", broadcast="active", broad=broad)


# 后台公告发布页面
@app.route("/addbroadcast")
def addbroadcast():
    if session.get("username") is None:
        return redirect('/')
    if not session.get("username") == 'admin':
        return redirect('/')

    return render_template("addbroadcast.html", broadcast="active")


# 我的
@app.route('/my')
def my():
    if session.get("username") is None:
        return redirect('/')
    return render_template("my.html", my="active")


# 发布公告API
@app.route("/addbroadcastapi", methods=["POST"])
def addbroadcastapi():
    if session.get("username") is None:
        return redirect('/')
    if not session.get("username") == 'admin':
        return redirect('/')

    addcast(request.form.get("title"), request.form.get("content"))
    return render_template("broadcast.html", broadcast="active")


# 充值API
@app.route('/charging', methods=['POST'])
def charging():
    if session.get("username") is None:
        return redirect('/')
    amount = request.form.get('amount')
    if amount is not None and amount.isdigit() and int(amount) > 0:
        conn = connectsql()
        # 连接失败
        if conn is None:
            session['username'] = ''
            return redirect('/')

        c = conn.cursor()
        money = getstumoney()
        sql = f"UPDATE stufinance SET wallet = {money+int(amount)} WHERE username = '{session.get('username')}'"
        c.execute(sql)
        conn.commit()
        timedate = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        sql = f"insert into rechargeinfo (username, rechargevalue, rechargetime) values ('{session.get('username')}', '{amount}', '{timedate}')"
        c.execute(sql)
        conn.commit()
        disconnectsql(conn, c)
        return redirect('/index')
    return redirect('/charge')


# 登录退出API
@app.route("/logout", methods=['GET'])
def logout():
    if session.get('username') is None:
        return redirect('/')
    else:
        session['username'] = None
        return redirect('/')


# debug 扫码
@app.route("/scan", methods=["POST"])
def scan():
    if session.get('username') is None:
        return redirect('/')
    secretcode = request.form.get('secretcode')
    conn = connectsql()
    c = conn.cursor()
    sql = f"select wallet from stufinance where username = {session.get('username')}"
    c.execute(sql)
    money = c.fetchone()[0]
    sql = f"update stufinance set wallet = {money-1} where username = {session.get('username')}"
    c.execute(sql)
    sql = f"UPDATE orderinfo set payid='1' where orderid='{secretcode}'"
    c.execute(sql)
    taketime = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    sql = f"insert into takebushistory (username, taketime) values ({session.get('username')},'{taketime}')"
    c.execute(sql)
    conn.commit()
    disconnectsql(conn, c)
    return redirect("/index/debug")


# 路由模块结束 #
###############
# 模组模块 #
###########
# 连接数据库


def connectsql() -> object:
    try:
        conn = pymysql.connections.Connection(
            host=db.database_host,
            user=db.database_user,
            passwd=db.database_password,
            db=db.database,
            port=db.database_port,
            charset='utf8')
        return conn
    except:
        return None


# 断开数据库
def disconnectsql(conn, c):
    try:
        conn.close()
        c.close()
        return True
    except:
        return False


# 处理的函数 #
#############


# 主页面获得订单号
def getcode() -> str:
    return str(time.time()) + session.get('username')


# 插入订单号
def insertorder(code) -> bool:
    conn = connectsql()
    c = conn.cursor()
    orderid = code
    orderdate = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    payid = 0
    sql = "INSERT INTO orderinfo (orderid,orderdate,payid) VALUES ('%s','%s','%s')" % (
        orderid, orderdate, payid)
    c.execute(sql)
    conn.commit()
    disconnectsql(conn, c)
    return True


# 获得学生钱
def getstumoney() -> int:
    conn = connectsql()
    c = conn.cursor()
    sql = f"SELECT wallet FROM stufinance where username = {session.get('username')}"

    if c.execute(sql) is not 0:
        money = c.fetchone()[0]
    else:
        # 发现没有学生信息
        sql = f"INSERT INTO stufinance(username,takecount,wallet) VALUES('{session.get('username')}', '0', '0')"
        c.execute(sql)
        conn.commit()
        money = 0
    disconnectsql(conn, c)
    return int(money)


# 获得订单
def getorder():
    conn = connectsql()
    c = conn.cursor()
    sql = "select * from orderinfo where payid = 1"
    c.execute(sql)
    result = c.fetchall()
    disconnectsql(conn, c)
    return result


# 获得公告
def getbroadcast():
    conn = connectsql()
    c = conn.cursor()
    sql = "select * from broadcast"
    c.execute(sql)
    result = c.fetchall()
    disconnectsql(conn, c)
    return result


# 添加公告
def addcast(title, content):
    conn = connectsql()
    c = conn.cursor()
    curtime = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    sql = f"insert into broadcast (title, info, date) values ('{title}', '{content}', '{curtime}')"
    c.execute(sql)
    conn.commit()
    disconnectsql(conn, c)
    return True


# 获得充值历史
def getchargehistory(username):
    conn = connectsql()
    c = conn.cursor()
    sql = f"select * from rechargeinfo where username = {username}"
    c.execute(sql)
    disconnectsql(conn, c)
    return c.fetchall()


# 获得乘车信息
def gettakehistory(username):
    conn = connectsql()
    c = conn.cursor()
    sql = f"select * from takebushistory where username = {username}"
    c.execute(sql)
    disconnectsql(conn, c)
    return c.fetchall()


# 获得cpu信息
def getcpustat() -> int:
    data = psutil.virtual_memory()
    return int(data.available/data.total*100)


# 获得内存信息
def getmemorystat() -> int:
    return int(psutil.cpu_percent(interval=1))


if __name__ == '__main__':
    app.run(debug=True, host='localhost')
