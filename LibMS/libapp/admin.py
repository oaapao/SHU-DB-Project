import datetime

from django.contrib import admin
from django.core.mail import send_mail
from django.db.models import Q, F

from .models import *
from django.utils import timezone

# Register your models here.
admin.site.site_header = '上海大学图书借阅管理系统'
admin.site.site_title = '借阅管理'


@admin.register(CIP)
class CIPAdmin(admin.ModelAdmin):
    # 要显示的字段
    list_display = ('id', 'title', 'author', 'publisher', 'get_rest_num', 'get_total_num')

    def get_rest_num(self, obj):
        return obj.books_set.filter(state='2').count()

    def get_total_num(self, obj):
        return obj.books_set.all().count()

    get_rest_num.short_description = u'可借数量'
    get_total_num.short_description = u'总数量'
    # 需要搜索的字段
    search_fields = ('id', 'title', 'author')
    # 分页显示，一页的数量
    list_per_page = 10
    list_editable = ('title', 'author', 'publisher')
    readonly_fields = ('admin',)
    actions_on_top = True

    def save_model(self, request, obj, form, change):
        obj.admin = request.user
        obj.save()


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    # 要显示的字段
    list_display = ('id',)
    # 需要搜索的字段
    search_fields = ('id',)
    # 分页显示，一页的数量
    list_per_page = 10
    actions_on_top = True


@admin.register(Reader)
class ReaderAdmin(admin.ModelAdmin):
    list_display_links = ('name',)
    # 要显示的字段
    list_display = ('id', 'name', 'phone', 'email', 'borrow', 'limit')
    # 需要搜索的字段
    search_fields = ('id__id', 'name', 'phone', 'email')
    list_editable = ('phone', 'email', 'limit',)
    # 分页显示，一页的数量
    list_per_page = 10

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
    list_per_page = 10
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
            if int(user.borrow) < int(user.limit):  # 未超过上限
                given.status = '1'
                given.save()
                user.borrow = F('borrow') + 1
                user.save()
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
    list_per_page = 10
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
    list_per_page = 10
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
