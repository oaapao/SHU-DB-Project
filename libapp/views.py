import datetime
import json

from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.http import HttpResponse
from django.shortcuts import render, redirect
import hashlib
from django.urls import reverse
from django.utils.timezone import now

from data.randomData import randomName, randomPhone, randomEmail, randomId
from libapp import models, forms
from libapp.forms import UserForm
from libapp.models import User, Reader, CIP, Books, Bookslips, Reservations, Bookcollections, Fines, Bookcart
from django.db.models import Count


def hash_code(s, salt='login'):
    h = hashlib.sha256()
    s += salt
    h.update(s.encode())
    return h.hexdigest()


def index(request):
    # generateData()
    if not request.session.get('is_login', None):
        return redirect('/login/')
    else:
        uid = request.session['user_id']
        book_lips_num = Bookslips.objects.filter(reader=uid, status='0').count()
        reserve_num = Reservations.objects.filter(reader=uid, status='0').count()
        date = now().date() + datetime.timedelta(days=0)
        overdue_num = Bookslips.objects.filter(reader=uid, due__lte=date).count
        book_lips = Bookslips.objects.filter(reader=uid, status='0')
        coolection_num = Bookcollections.objects.filter(reader=uid).count()
        ranking = Bookcollections.objects.values('reader').annotate(colc_num=Count('reader')).filter(
            colc_num__gt=coolection_num).count()
        violation_num = Fines.objects.filter(borrow_id=uid).count()
        reserve_sec_num = Reservations.objects.filter(reader=uid).count()
        clazz_num = [0, 0, 0, 0, 0, 0]
        for i in book_lips:
            i.date = date - i.date
            if (i.book.isbn.clazz == '0'):
                clazz_num[0] += 1
            elif (i.book.isbn.clazz == '1'):
                clazz_num[1] += 1
            elif (i.book.isbn.clazz == '2'):
                clazz_num[2] += 1
            elif (i.book.isbn.clazz == '3'):
                clazz_num[3] += 1
            elif (i.book.isbn.clazz == '4'):
                clazz_num[4] += 1
            elif (i.book.isbn.clazz == '5'):
                clazz_num[5] += 1
        pie_series1 = {  # 用字典的形式,为什么原来的js里面是列表，而这里却是用字典？？看下去就知道啦！！
            'element': 'donut-example',
            'redraw': 'true',
            'data': [
                {'label': "马列毛邓", 'value': clazz_num[0]},
                {'label': "哲学", 'value': clazz_num[1]},
                {'label': "社会科学", 'value': clazz_num[2]},
                {'label': "自然科学", 'value': clazz_num[3]},
                {'label': "综合类", 'value': clazz_num[4]},
                {'label': "其他", 'value': clazz_num[5]},
            ],
            'colors': ['#448aff', '#ff5252', '#5FBEAA', '#34495E', '#FF9F55', ]
        }
        json_data = json.dumps(pie_series1, separators=(',', ':'))
        context = {
            'book_lips_num': book_lips_num,
            'reserve_num': reserve_num,
            'overdue_num': overdue_num,
            'book_lips': book_lips,
            'coolection_num': coolection_num,
            'ranking': ranking,
            'violation_num': violation_num,
            'reserve_sec_num': reserve_sec_num,
            'series': json_data
        }
    return render(request, 'reader/index.html', context=context)


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
                request.session['name'] = Reader.objects.get(id=user).name
                photo = Reader.objects.get(id=user).photo
                if photo:
                    request.session['photo'] = photo.url
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
                                               phone=phone, email=email)
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


def goCheckIn(request, book):
    # 借书操作
    if request.method == 'GET':
        uid = request.session['user_id']
        abook = Books.objects.filter(isbn__id=book, state='2').first()
        user = Reader.objects.get(id_id=uid)
        message = ""
        if abook:  # 当前有书
            if int(user.get_borrow_num()) < int(user.limit):  # 未超过上限
                abook.state = '0'
                abook.save()
                now = datetime.datetime.now()
                delta = datetime.timedelta(days=20)
                n_days = now + delta
                new_bookslip = Bookslips(book_id=abook.id, reader_id=uid, due=n_days)
                new_bookslip.save()
                messages.success(request, '借阅成功！')
            else:
                messages.error(request, '借阅失败！当前账户借阅数量已达到上限')
        else:
            messages.error(request, '借阅失败！当前图书暂无或不可借阅')
        return redirect('borrowList')


def goCheckOut(request, id):
    # 还书操作
    if request.method == 'GET':
        uid = request.session['user_id']

        temp = Bookslips.objects.get(id=id)
        abook = temp.book
        abook.state = '2'
        abook.save()
        temp.status = '1'
        temp.restore = datetime.datetime.now()
        temp.save()

        messages.success(request, '还书成功！')
        # 判断是否有人预约
        given = Reservations.objects.filter(isbn__id=abook.isbn.id, status='0').filter(~Q(reader_id=uid)).first()
        if given:
            user = Reader.objects.get(id_id=given.reader_id)
            if int(user.get_borrow_num()) < int(user.limit):  # 未超过上限
                given.status = '1'
                given.save()
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

        return redirect('borrowList')


def goReserve(request, book):
    # 预约操作
    if request.method == 'GET':
        uid = request.session['user_id']
        abook = Books.objects.filter(isbn__id=book, state='2').first()
        user = Reader.objects.get(id_id=uid)
        have = Reservations.objects.filter(reader_id=uid, isbn_id=book).count()
        if not abook and have == 0:  # 当前无书且未预约
            if int(user.get_borrow_num()) < int(user.limit):  # 未超过上限
                now = datetime.datetime.now()
                delta = datetime.timedelta(days=10)
                n_days = now + delta
                new_reserve = Reservations(reader_id=uid, due=n_days, status='0', isbn_id=book)
                new_reserve.save()
                messages.success(request, '预约成功！')
        else:
            messages.error(request, '预约失败！您已预约或该书无需预约！')
        return redirect('reserveList')


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
    paginator = Paginator(book_list, 12)  # Show 5 contacts per page
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
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        pwd1 = request.POST.get('pwd1')
        pwd2 = request.POST.get('pwd2')
        file = request.FILES.get('inputfile')
        if file:
            user.photo = file
            user.save()
            request.session['photo'] = user.photo.url
        if name:
            user.name = name
        if phone:
            user.phone = phone
        if email:
            user.email = email
        if pwd1:
            if pwd2:
                print("input re")
            else:
                if pwd1 == pwd2:
                    print(pwd1)
                else:
                    print("Error not equal")
        user.save()
        request.session['name'] = user.name
    context = {
        'user': user,
    }
    return render(request, 'reader/profile.html', context=context)


def bookDetail(request, isbn):
    book = CIP.objects.get(id=isbn)
    return render(request, 'reader/bookDetail.html', locals())


def borrowList(request):
    uid = request.session['user_id']
    book_list = Bookslips.objects.filter(~Q(status='1'), reader_id=uid)
    user = Reader.objects.get(id_id=uid)
    user.save()
    context = {
        'book_list': book_list,
    }
    if request.method == 'POST':
        list = request.POST.getlist('list')
        print(list)
        for i in list:
            temp = Bookslips.objects.get(id=i)
            abook = temp.book
            abook.state = '2'
            abook.save()
            temp.status = '1'
            temp.restore = datetime.datetime.now()
            temp.save()
            messages.success(request, '还书成功！')
            # 判断是否有人预约
            given = Reservations.objects.filter(isbn__id=abook.isbn.id, status='0').filter(~Q(reader_id=uid)).first()
            if given:
                user = Reader.objects.get(id_id=given.reader_id)
                if int(user.get_borrow_num()) < int(user.limit):  # 未超过上限
                    given.status = '1'
                    given.save()
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
    book_list = Bookslips.objects.filter(due__lt=datetime.datetime.now(), reader_id=uid)
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
                    pdate=row[4].value, admin_id=1)
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
            Reader(id_id=id_list[i], name=name_list[i], phone=phone_list[i], email=email_list[i])
        )
    Reader.objects.bulk_create(Reader_list)

    # 批量插入Books
    index = 1000
    CIP_id = CIP.objects.all()
    for iter1 in CIP_id:
        for i in range(20):
            index += 1
            new_book = Books(id=str(index))
            new_book.state = '2'
            new_book.place = '0'
            new_book.admin_id = 1
            new_book.isbn = iter1
            new_book.save()


def dropReserve(request, book):
    uid = request.session['user_id']
    isbn = CIP.objects.get(id=book)
    Reservations.objects.get(reader__id=uid, status='0', isbn=isbn).delete()
    messages.success(request, '取消预约成功！')
    return redirect('reserveList')


def collectionList(request):
    uid = request.session['user_id']
    book_list = Bookcollections.objects.filter(reader_id=uid)
    return render(request, 'reader/collections.html', locals())


def collections(request, book):
    # 收藏操作
    if request.method == 'GET':
        uid = request.session['user_id']
        older = Bookcollections.objects.filter(reader_id=uid, isbn_id=book).count()
        if older == 0:
            new_collect = Bookcollections(reader_id=uid, isbn_id=book)
            new_collect.save()
            messages.success(request, '收藏成功！')
        else:
            messages.success(request, '您已经收藏过这本书！')
        # user = Reader.objects.get(id__id=uid)
        # clist = user.bookcollections_set.all()

    return redirect('collectionList')


def collectionsOut(request, book):
    uid = request.session['user_id']
    Bookcollections.objects.get(reader_id=uid, isbn_id=book).delete()
    messages.success(request, '取消收藏成功！')
    return redirect('collectionList')


def bookCart(request):
    flag = 0
    count = 0
    uid = request.session['user_id']
    book_list = Bookcart.objects.filter(reader_id=uid, status='0')
    user = Reader.objects.get(id_id=uid)
    context = {
        'book_list': book_list,
    }
    if request.method == 'POST':
        list = request.POST.getlist('list')
        print(list)
        for i in list:
            abook = Books.objects.filter(isbn__id=i, state='2').first()
            if abook:  # 当前有书
                if int(user.get_borrow_num()) < int(user.limit):  # 未超过上限
                    abook.state = '0'
                    abook.save()
                    now = datetime.datetime.now()
                    delta = datetime.timedelta(days=20)
                    n_days = now + delta
                    new_bookslip = Bookslips(book_id=abook.id, reader_id=uid, due=n_days)
                    new_bookslip.save()
                    cart = Bookcart.objects.filter(reader_id=uid, isbn_id=i, status='0').first()
                    cart.status = '1'
                    cart.save()
                    count += 1
                else:
                    string = '批量借阅未完成，借书已达上限。仅完成' + str(count) + '本书的批量借阅'
                    flag += 1
                    messages.error(request, string)
                    break
            else:
                flag += 1
                messages.error(request, '借阅失败！当前图书暂无或不可借阅')
        if not list:
            flag += 1
            messages.error(request, '借阅失败！书单中尚无图书！')
        if flag == 0:
            string = '成功完成' + str(count) + '本书的批量借阅'
            messages.success(request, string)
    return render(request, 'reader/bookCart.html', context=context)


def inCart(request, book_id):
    if request.method == 'GET':
        uid = request.session['user_id']
        cart = Bookcart.objects.filter(reader_id=uid, isbn_id=book_id).count()
        if cart == 0:
            new_cart = Bookcart(reader_id=uid, isbn_id=book_id, status='0')
            new_cart.save()
            messages.success(request, '加入书单成功！')
        elif cart.status == '0':
            messages.success(request, '图书已在书单中！')
        else:
            cart.status = '0'
        # user = Reader.objects.get(id__id=uid)
        # clist = user.bookcollections_set.all()
    return redirect('bookCart')


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
                    str(iter.book.isbn.title) + '》将在' + str(iter.due) + '到期，请注意及时归还！',
            from_email='shu_libms@163.com',  # 发件人
            recipient_list=[str(iter.reader.email)],  # 收件人
            fail_silently=False
        )
        iter.status = '2'  # 修改状态为已通知，防止重复发送邮件
        iter.save()
        new_fine = Fines.objects.get_or_create(borrow=iter)
        if not new_fine.status:
            new_fine.money = int((datetime.datetime.now() - iter.due).days)
            new_fine.save()

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


def payMoney(request,bid):
    t = Fines.objects.get(borrow__id=bid)
    t.status = '1'
    t.save()
    temp = Bookslips.objects.get(id=bid)
    abook = temp.book
    abook.state = '2'
    abook.save()
    temp.status = '1'
    temp.restore = datetime.datetime.now()
    temp.save()
    messages.success(request, '还书成功！')
    # 判断是否有人预约
    given = Reservations.objects.filter(isbn__id=abook.isbn.id, status='0').first()
    if given:
        user = Reader.objects.get(id_id=given.reader_id)
        if int(user.get_borrow_num()) < int(user.limit):  # 未超过上限
            given.status = '1'
            given.save()
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

    return redirect('borrowList')




