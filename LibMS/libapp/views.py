import datetime
from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.http import HttpResponse
from django.shortcuts import render, redirect
import hashlib
from django.urls import reverse
from data.randomData import randomName, randomPhone, randomEmail, randomId
from libapp import models, forms
from libapp.forms import UserForm
from libapp.models import User, Reader, CIP, Books, Bookslips, Reservations


def hash_code(s, salt='login'):
    h = hashlib.sha256()
    s += salt
    h.update(s.encode())
    return h.hexdigest()


def index(request):
    # generateData()
    if not request.session.get('is_login', None):
        return redirect('/login/')
    return render(request, 'reader/index.html')


def login(request):
    if request.session.get('is_login', None):
        return redirect('/index/')
    if request.method == "POST":
        login_form = UserForm(request.POST)
        message = '请检查填写的内容！'
        if login_form.is_valid():  # 确保用户名和密码都不为空
            id = login_form.cleaned_data['idcard']
            password = login_form.cleaned_data['password']
            try:
                user = models.User.objects.get(id=id)
            except:
                message = '用户不存在！'
                return render(request, 'login.html', {'message': message})
            if user.pwd == hash_code(password):
                request.session['is_login'] = True
                request.session['user_id'] = user.id
                request.session['name'] = Reader.objects.get(id_id=id).name
                return redirect('/index/')
            else:
                message = '用户名或密码不正确！'
                return render(request, 'login.html', {'message': message})
        else:
            return render(request, 'login.html', {'message': message})
    return render(request, 'login.html')


def register(request):
    if request.session.get('is_login', None):
        return redirect('/index/')

    if request.method == 'POST':
        register_form = forms.RegisterForm(request.POST)
        message = "请检查填写的内容！"
        if register_form.is_valid():
            username = register_form.cleaned_data.get('username')
            idcard = register_form.cleaned_data.get('idcard')
            password1 = register_form.cleaned_data.get('password1')
            password2 = register_form.cleaned_data.get('password2')
            email = register_form.cleaned_data.get('email')
            phone = register_form.cleaned_data.get('phone')
            if password1 != password2:
                message = '两次输入的密码不同！'
                return render(request, 'register.html', locals())
            else:
                same_name_user = models.User.objects.filter(id=idcard)
                if same_name_user:
                    message = '用户已经存在'
                    return render(request, 'register.html', locals())
            new_user = User.objects.create(id=idcard, pwd=hash_code(password1))
            new_user.save()
            new_reader = Reader.objects.create(id_id=new_user.id, name=username,
                                               phone=phone, email=email, borrow=0)
            new_reader.save()
            return redirect('/login/')
        else:
            return render(request, 'register.html', locals())
    register_form = forms.RegisterForm()
    return render(request, 'register.html', locals())


def logout(request):
    if not request.session.get('is_login', None):
        # 如果本来就未登录，也就没有登出一说
        return redirect("/login/")
    request.session.flush()
    return redirect("/login/")


def checkOut(request):
    if request.method == 'GET':
        return render(request, 'reader/checkOut.html')


def goCheckIn(request, book):
    # 借书操作
    if request.method == 'GET':
        uid = request.session['user_id']
        abook = Books.objects.filter(isbn__id=book, state='2').first()
        user = Reader.objects.get(id_id=uid)
        message = ""
        if abook:  # 当前有书
            if int(user.borrow) < int(user.limit):  # 未超过上限
                user.borrow = F('borrow') + 1
                user.save()
                abook.state = '0'
                abook.save()
                now = datetime.datetime.now()
                delta = datetime.timedelta(days=20)
                n_days = now + delta
                new_bookslip = Bookslips(book_id=abook.id, reader_id=uid, due=n_days)
                new_bookslip.save()
                message = "借阅成功！"
            else:
                message = '借阅失败！当前账户借阅数量已达到上限'
        else:

            message = '借阅失败！当前图书暂无或不可借阅'
        return render(request, 'reader/index.html', {'message': message})


def goCheckOut(request, book, num):
    # 还书操作
    if request.method == 'GET':
        uid = request.session['user_id']
        user = Reader.objects.get(id_id=uid)
        user.borrow = F('borrow') - 1
        user.save()

        abook = Books.objects.get(isbn__id=book, id=num)
        abook.state = '2'
        abook.save()

        temp = Bookslips.objects.get(reader_id=uid, book_id=num)
        temp.status = '1'
        temp.restore = datetime.datetime.now()
        temp.save()

        message = "还书成功！"
        # 判断是否有人预约
        given = Reservations.objects.filter(isbn__id=book, status='0').filter(~Q(reader_id=uid)).first()
        if given:
            user = Reader.objects.get(id_id=given.reader_id)
            if int(user.borrow) < int(user.limit):  # 未超过上限
                given.status = '1'
                given.save()
                user.borrow = F('borrow') + 1
                user.save()
                abook.state = '0'
                abook.save()
                now = datetime.datetime.now()
                delta = datetime.timedelta(days=20)
                n_days = now + delta
                new_bookslip = Bookslips(book_id=abook.id, reader_id=given.reader_id, due=n_days)
                new_bookslip.save()
                # send email
                send_mail(
                    subject='上海大学图书借阅系统预约提醒',
                    message=str(user.name) + '同学您好！预约的《' +
                            str(abook.isbn.title) + '》有空余，系统已经自动为您借阅！' +
                            '请注意归还时间为：' + str(n_days),
                    from_email='shu_libms@163.com',  # 发件人
                    recipient_list=[str(user.email)],  # 收件人
                    fail_silently=False
                )

        book_list = Books.objects.filter(id__in=Bookslips.objects.filter(reader_id=uid).values('book_id'))
        num = book_list.count()
        context = {
            'book_list': book_list,
            'num': num,
            'message': message
        }
        return render(request, 'reader/borrowList.html', context=context)


def goReserve(request, book):
    # 预约操作
    if request.method == 'GET':
        uid = request.session['user_id']
        abook = Books.objects.filter(isbn__id=book, state='2').first()
        user = Reader.objects.get(id_id=uid)
        have = Reservations.objects.filter(reader_id=uid, isbn_id=book).count()
        if not abook and have == 0:  # 当前无书且未预约
            if int(user.borrow) < int(user.limit):  # 未超过上限
                now = datetime.datetime.now()
                delta = datetime.timedelta(days=10)
                n_days = now + delta
                new_reserve = Reservations(reader_id=uid, due=n_days, status='0', isbn_id=book)
                new_reserve.save()
        return render(request, 'reader/index.html')


def reserve(request):
    return render(request, 'reader/index.html')


def checkIn(request):
    return render(request, 'reader/checkIn.html')


def getKeyword(request):
    request.session['keyStr'] = request.GET.get('key')  # 获取到用户提交的搜索关键词
    if request.session['keyStr'] is not None:
        return redirect(reverse("search"))
    return render(request, 'reader/index.html')


def search(request):
    content = request.session['keyStr']
    if not content:
        return redirect('/index/')
    book_list = CIP.objects.filter(Q(title__icontains=content) | Q(author__icontains=content) |
                                   Q(publisher__icontains=content) | Q(id__icontains=content))
    num = book_list.count()
    paginator = Paginator(book_list, 5)  # Show 5 contacts per page
    page = request.GET.get('page')
    book_list = paginator.get_page(page)
    context = {
        'book_list': book_list,
        'search': content,
        'num': num
    }
    return render(request, 'reader/searchResult.html', context=context)


def profile(request):
    uid = request.session['user_id']
    user = Reader.objects.get(id_id=uid)
    if request.method == 'POST':
        name=request.POST.get('name')
        phone=request.POST.get('phone')
        email=request.POST.get('email')
        pwd1=request.POST.get('pwd1')
        pwd2=request.POST.get('pwd2')

        if name:
            user.name=name
        if phone:
            user.phone=phone
            print("phone update")
        if email:
            user.email=email
        if pwd1:
            if pwd2:
                print("input re")
            else:
                if pwd1==pwd2:
                    print(pwd1)
                else:
                    print("Error not equal")
        user.save()
        request.session['name']=user.name
    context = {
        'user' : user,
    }
    return render(request, 'reader/profile.html', context=context)


def collections(request):
    return render(request, 'reader/collections.html')


def bookDetail(request):
    return render(request, 'reader/bookDetail.html')


def borrowList(request):
    uid = request.session['user_id']
    book_list = Books.objects.filter(id__in=
                                     Bookslips.objects.filter(~Q(status='1'), reader_id=uid).values('book_id'))
    context = {
        'book_list': book_list,
    }
    return render(request, 'reader/borrowList.html', context=context)


def reserveList(request):
    uid = request.session['user_id']
    cip_list = CIP.objects.filter(id__in=
                                     Reservations.objects.filter(~Q(status='1'), reader_id=uid).values('isbn__id'))
    context = {
        'book_list': cip_list,
    }
    return render(request, 'reader/reserveList.html', context=context)


def overdueList(request):
    uid = request.session['user_id']
    book_list = Books.objects.filter(id__in=
                                     Bookslips.objects.filter(due__lt=datetime.datetime.now(), reader_id=uid).values('book_id'))
    context = {
        'book_list': book_list,
    }
    return render(request, 'reader/overdueList.html', context=context)

def generateData():
    import openpyxl
    # 批量插入CIP
    CIP_workbook = openpyxl.load_workbook('data/CIP.xlsx')
    CIP_worksheet = CIP_workbook.worksheets[0]
    CIP_list = []
    CIP_iter = iter(CIP_worksheet)
    next(CIP_iter)
    for row in CIP_iter:
        if row[0].value and CIP.objects.filter(id=row[0].value).count() == 0:
            CIP_list.append(
                CIP(id=row[0].value, title=row[1].value, author=row[2].value, publisher=row[3].value,
                    pdate=row[4].value, total=row[5].value, rest=row[6].value, admin_id=1)
            )
    CIP.objects.bulk_create(CIP_list)

    # 批量插入Reader
    id_list = randomId(100)
    pwd = '896c59fd9105ccf5f2eef965b65fb8eb6006fc93bc643a4af0a3021f7ed865c9'  # 默认密码123456
    name_list = randomName(100)
    phone_list = randomPhone(100)
    email_list = randomEmail(100)
    User_list = []
    Reader_list = []
    for i in range(100):
        User_list.append(
            User(id=id_list[i], pwd=pwd)
        )
    User.objects.bulk_create(User_list)
    for i in range(100):
        Reader_list.append(
            Reader(id_id=id_list[i], name=name_list[i], phone=phone_list[i], email=email_list[i],
                   borrow=0)
        )
    Reader.objects.bulk_create(Reader_list)

    # 批量插入Books
    index = 1000
    CIP_id = CIP.objects.all()
    for iter in CIP_id:
        for i in range(20):
            index += 1
            new_book = Books(id=str(index))
            new_book.state = '2'
            new_book.place = '0'
            new_book.admin_id = 1
            new_book.isbn = iter
            new_book.save()


def timingTask():
    '''
    定时任务，定期检查是否有读者借书逾期未还&预约单超期，并进行相应的通知
    :return: 发送邮件&数据库处理
    '''

    # 检查读者借阅逾期情况
    overdue_borrow = Bookslips.objects.filter(status='0', due__lt=datetime.datetime.now())
    for iter in overdue_borrow:
        send_mail(
            subject='上海大学图书借阅系统图书归还提醒',
            message=str(iter.reader.name) + '同学您好！您正在借阅的《' +
                    str(iter.book.isbn.title) + '》将在'+ str(iter.due)+'到期，请注意及时归还！',
            from_email='shu_libms@163.com',  # 发件人
            recipient_list=[str(iter.reader.email)],  # 收件人
            fail_silently=False
        )
        iter.status = '2' # 修改状态为已通知，防止重复发送邮件
        iter.save()

    # 检查借阅单超期失效情况
    overdue_reserve = Reservations.objects.filter(status='0', due__lt=datetime.datetime.now())
    for iter in overdue_reserve:
        send_mail(
            subject='上海大学图书借阅系统图书归还提醒',
            message=str(iter.reader.name) + '同学您好！您的图书预约《' +
                    str(iter.book.isbn.title) + '》超期未到，预约失败！',
            from_email='shu_libms@163.com',  # 发件人
            recipient_list=[str(iter.reader.email)],  # 收件人
            fail_silently=False
        )
        iter.status = '1'  # 修改预约状态为已完成（但是失败）
        iter.save()


def dropReserve(request, book):
    uid = request.session['user_id']
    isbn = CIP.objects.get(id=book)
    Reservations.objects.get(reader__id=uid, status='0', isbn=isbn).delete()

    cip_list = CIP.objects.filter(id__in=
                                  Reservations.objects.filter(~Q(status='1'), reader_id=uid).values('isbn__id'))
    context = {
        'book_list': cip_list,
    }
    return render(request, 'reader/reserveList.html', context=context)