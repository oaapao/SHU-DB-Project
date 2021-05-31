import datetime
import random

from django.contrib import admin, messages
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q, F
from django.http import JsonResponse
from django.utils.safestring import mark_safe

from .models import *
from django.utils import timezone

# Register your models here.
admin.site.site_header = '上海大学图书借阅管理系统'
admin.site.site_title = '借阅管理'


@admin.register(CIP)
class CIPAdmin(admin.ModelAdmin):
    # 要显示的字段
    list_display = ('id', 'title','image_data', 'author', 'publisher', 'clazz', 'get_rest_num', 'get_total_num')

    def get_rest_num(self, obj):
        return obj.books_set.filter(state='2').count()

    def get_total_num(self, obj):
        return obj.books_set.all().count()

    get_rest_num.short_description = u'可借数量'
    get_total_num.short_description = u'总数量'
    # 需要搜索的字段
    search_fields = ('id', 'title', 'author')
    list_filter = ('publisher', 'clazz')
    # 分页显示，一页的数量
    list_per_page = 20
    list_editable = ('clazz',)
    readonly_fields = ('admin', 'image_data')
    actions_on_top = True

    def image_data(self, obj):
        if obj.cover:
            return mark_safe(u'<img src="%s" width="100px" />' % obj.cover.url)
        return mark_safe(u' ')

    # 页面显示的字段名称
    image_data.short_description = u'图书封面'
    #image_data.allow_tags = True

    def save_model(self, request, obj, form, change):
        obj.admin = request.user
        obj.save()

    def test2(self, request, queryset):
        for iter in queryset:
            id = random.randint(10000000, 99999999)
            while Books.objects.filter(id=id).count() > 0:
                id = random.randint(10000000, 99999999)
            new_book = Books(id=id, isbn=iter, state='1', place='1')
            new_book.save()
        messages.add_message(request, messages.SUCCESS, '添加成功！')

    def test1(self, request, queryset):
        for iter in queryset:
            id = random.randint(10000000, 99999999)
            while Books.objects.filter(id=id).count() > 0:
                id = random.randint(10000000, 99999999)
            new_book = Books(id=id, isbn=iter, state='2', place='0')
            new_book.save()

            # 判断是否有人预约
            given = Reservations.objects.filter(isbn=iter, status='0').first()
            if given:
                user = Reader.objects.get(id_id=given.reader_id)
                if int(user.get_borrow_num()) < int(user.limit):  # 未超过上限
                    given.status = '1'
                    given.save()
                    new_book.state = '0'
                    new_book.save()
                    now = datetime.datetime.now()
                    delta = datetime.timedelta(days=20)
                    n_days = now + delta
                    new_bookslip = Bookslips(book_id=new_book.id, reader_id=given.reader_id, due=n_days)
                    new_bookslip.save()
                    # send email
                    send_mail(
                        subject='上海大学图书借阅系统预约提醒',
                        message=str(user.name) + '同学您好！预约的《' +
                                str(iter.title) + '》有空余，系统已经自动为您借阅！' +
                                '请注意归还时间为：' + str(n_days),
                        from_email='shu_libms@163.com',  # 发件人
                        recipient_list=[str(user.email)],  # 收件人
                        fail_silently=False
                    )
        messages.add_message(request, messages.SUCCESS, '添加成功！')

    actions = ['test1', 'test2']

    test1.short_description = '新增图书(流通室)'
    test1.type = 'default'
    test1.icon = 'el-icon-s-promotion'
    test2.short_description = '新增图书(阅览室)'
    test2.type = 'default'
    test2.icon = 'el-icon-s-promotion'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    # 要显示的字段
    list_display = ('id',)
    # 需要搜索的字段
    search_fields = ('id',)
    # 分页显示，一页的数量
    list_per_page = 20
    actions_on_top = True


@admin.register(Reader)
class ReaderAdmin(admin.ModelAdmin):
    list_display_links = ('name',)

    def borrow(self, obj):
        return u'%s' % obj.get_borrow_num()

    borrow.short_description = u'已借阅书目'
    # 要显示的字段
    list_display = ('id', 'name', 'phone', 'email', 'borrow', 'limit')
    # 需要搜索的字段
    search_fields = ('id__id', 'name', 'phone', 'email')
    list_editable = ('phone', 'email', 'limit',)

    # class BorrowInline(admin.TabularInline):
    #     model = Bookslips
    # inlines = [
    #     BorrowInline,
    # ]

    # 分页显示，一页的数量
    list_per_page = 20

    actions_on_top = True


@admin.register(Books)
class BooksAdmin(admin.ModelAdmin):
    # 要显示的字段
    list_display = ('isbnID', 'title', 'id', 'place', 'state')
    list_editable = ('place', 'state')
    list_filter = ('place', 'state')
    # 需要搜索的字段
    search_fields = ('id', 'isbn__id', 'isbn__title')
    # 分页显示，一页的数量
    list_per_page = 20
    actions_on_top = True
    readonly_fields = ('state', 'admin')

    def isbnID(self, obj):
        return u'%s' % obj.isbn.id

    isbnID.short_description = u'ISBN图书编号'

    def title(self, obj):
        return u'%s' % obj.isbn.title

    title.short_description = u'书名'

    def save_model(self, request, obj, form, change):
        obj.admin = request.user
        if obj.place == '0' or obj.place == '图书流通室':
            obj.state = '2'
        else:
            obj.state = '1'
        obj.save()

        # 判断是否有人预约
        given = Reservations.objects.filter(isbn__id=obj.isbn.id, status='0').first()
        if given:
            user = Reader.objects.get(id_id=given.reader_id)
            if int(user.get_borrow_num()) < int(user.limit):  # 未超过上限
                given.status = '1'
                given.save()
                obj.state = '0'
                obj.save()
                now = datetime.datetime.now()
                delta = datetime.timedelta(days=20)
                n_days = now + delta
                new_bookslip = Bookslips(book_id=obj.id, reader_id=given.reader_id, due=n_days)
                new_bookslip.save()
                # send email
                send_mail(
                    subject='上海大学图书借阅系统预约提醒',
                    message=str(user.name) + '同学您好！预约的《' +
                            str(obj.isbn.title) + '》有空余，系统已经自动为您借阅！' +
                            '请注意归还时间为：' + str(n_days),
                    from_email='shu_libms@163.com',  # 发件人
                    recipient_list=[str(user.email)],  # 收件人
                    fail_silently=False
                )


@admin.register(Bookslips)
class BookslipsAdmin(admin.ModelAdmin):
    # 要显示的字段
    list_display = (
        'isbnID', 'title', 'bookID', 'ReaderID', 'ReaderName', 'date', 'due', 'status', 'restore')
    # 需要搜索的字段
    search_fields = ('book__isbn__title', 'book__isbn__id', 'book__id', 'reader__id__id', 'reader__name')
    list_editable = ('status',)
    list_filter = ('status',)
    # 分页显示，一页的数量
    list_per_page = 20
    actions_on_top = True

    def isbnID(self, obj):
        return u'%s' % obj.book.isbn.id

    isbnID.short_description = u'ISBN编号'

    def title(self, obj):
        return u'%s' % obj.book.isbn.title

    title.short_description = u'图书名'

    def bookID(self, obj):
        return u'%s' % obj.book.id

    bookID.short_description = u'图书号'

    def ReaderID(self, obj):
        return u'%s' % obj.reader.id_id

    ReaderID.short_description = u'读者ID'

    def ReaderName(self, obj):
        return u'%s' % obj.reader.name

    ReaderName.short_description = u'读者姓名'


@admin.register(Reservations)
class ReservationsAdmin(admin.ModelAdmin):
    # 要显示的字段
    list_display = ('isbnID', 'title', 'ReaderID', 'ReaderName', 'date', 'due', 'status')
    # 需要搜索的字段
    search_fields = ('isbn__id', 'isbn__title', 'reader__id__id', 'reader__name')
    list_editable = ('status',)
    list_filter = ('status',)
    # 分页显示，一页的数量
    list_per_page = 20
    actions_on_top = True

    def isbnID(self, obj):
        return u'%s' % obj.isbn.id

    isbnID.short_description = u'ISBN编号'

    def title(self, obj):
        return u'%s' % obj.isbn.title

    title.short_description = u'图书名'

    def ReaderID(self, obj):
        return u'%s' % obj.reader.id_id

    ReaderID.short_description = u'读者ID'

    def ReaderName(self, obj):
        return u'%s' % obj.reader.name

    ReaderName.short_description = u'读者姓名'


@admin.register(Fines)
class FinesAdmin(admin.ModelAdmin):
    # 要显示的字段
    list_display = ('id', 'borrow', 'date', 'money', 'status')
    # 需要搜索的字段
    search_fields = ('id',)
    list_display_links = ('borrow',)
