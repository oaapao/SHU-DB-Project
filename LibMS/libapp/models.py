from django.db import models
from django.contrib.auth import settings
from django.utils import timezone

STATUS_CHOICES = (
    ('0', '未完成'),
    ('1', '已完成'),
    ('2', '已通知')
)


# Create your models here.
class User(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name='读者ID')
    pwd = models.CharField(max_length=256, verbose_name='读者密码')

    class Meta:
        verbose_name = '账号管理'
        verbose_name_plural = '账号管理'

    def __str__(self):
        return str(self.id)


class Reader(models.Model):
    id = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    name = models.CharField(max_length=30, verbose_name='读者姓名')
    phone = models.CharField(max_length=11, null=True, verbose_name='手机号码')
    email = models.EmailField(max_length=254, verbose_name='电子邮箱')
    borrow = models.IntegerField(default=0, verbose_name='已借阅数量')
    limit = models.IntegerField(default=10, verbose_name='借阅上限')
    #photo = models.ImageField(upload_to='imgs')
    class Meta:
        verbose_name = '读者管理'
        verbose_name_plural = '读者管理'

    def __str__(self):
        return '{} {}'.format(self.id_id, self.name)


class CIP(models.Model):
    # 书目
    id = models.CharField(max_length=50, primary_key=True, verbose_name='图书ISBN编号')
    title = models.CharField(max_length=100, verbose_name='图书名称')
    author = models.CharField(max_length=50, verbose_name='图书作者')
    publisher = models.CharField(max_length=100, verbose_name='出版社')
    pdate = models.DateTimeField(verbose_name='出版时间')
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='负责人',
                              on_delete=models.SET_NULL, blank=True, null=True)

    def get_rest_num(self):
        return self.books_set.filter(state='2').count()

    def get_total_num(self):
        return self.books_set.all().count()

    class Meta:
        verbose_name = 'CIP管理'
        verbose_name_plural = 'CIP管理'

    def __str__(self):
        return str(self.id)


class Books(models.Model):
    '''
    图书表
    '''
    POS_CHOICES = (
        ('0', '图书流通室'),
        ('1', '图书阅览室')
    )
    STA_CHOICES = (
        ('0', '已借出'),
        ('1', '不外借'),
        ('2', '未借出'),
        ('3', '已预约'),
    )
    id = models.CharField(max_length=50, primary_key=True, verbose_name='图书ID')
    isbn = models.ForeignKey(CIP, on_delete=models.CASCADE, verbose_name='图书ISBN编号')
    place = models.CharField(max_length=10, choices=POS_CHOICES, default='图书流通室', verbose_name='存放位置')
    state = models.CharField(max_length=10, choices=STA_CHOICES, default='未借出', verbose_name='图书状态')
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='负责人',
                              on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        verbose_name = '图书管理'
        verbose_name_plural = '图书管理'

    def __str__(self):
        return '{} {}'.format(self.isbn, self.id)


class Bookslips(models.Model):
    '''
    读者借阅表
    '''
    id = models.AutoField(primary_key=True)
    book = models.ForeignKey(Books, on_delete=models.CASCADE, verbose_name='图书ID')
    reader = models.ForeignKey(Reader, on_delete=models.CASCADE, verbose_name='读者ID')
    date = models.DateField(default=timezone.now, verbose_name='借阅日期')
    due = models.DateField(verbose_name='截止日期')
    restore = models.DateField(null=True, verbose_name='实际归还时间')
    status = models.CharField(max_length=5, choices=STATUS_CHOICES, default='未完成', verbose_name='当前状态')

    class Meta:
        verbose_name = '借阅管理'
        verbose_name_plural = '借阅管理'

    def __str__(self):
        return '{} --《{}》-- {}'.format(self.reader.name, self.book.isbn.title, self.book.id)


class Reservations(models.Model):
    id = models.AutoField(primary_key=True)
    isbn = models.ForeignKey(CIP, on_delete=models.CASCADE, verbose_name='图书ISBN编号')
    reader = models.ForeignKey(Reader, on_delete=models.CASCADE, verbose_name='读者ID')
    date = models.DateField(default=timezone.now, verbose_name='预约日期')
    due = models.DateField(verbose_name='失效日期')
    status = models.CharField(max_length=5, choices=STATUS_CHOICES, default='未完成', verbose_name='预约状态')

    class Meta:
        verbose_name = '预约管理'
        verbose_name_plural = '预约管理'
        ordering = ['date']  # 以后提取数据时，按照指定字段的排序提取数据


class Fines(models.Model):
    '''
    罚金表
    '''
    id = models.AutoField(primary_key=True)
    borrow = models.ForeignKey(to=Bookslips, on_delete=models.CASCADE, verbose_name='关联的借阅记录')
    date = models.DateField(default=timezone.now, verbose_name='产生时间')
    money = models.IntegerField(verbose_name='金额')
    status = models.CharField(max_length=5, choices=STATUS_CHOICES, default='未完成', verbose_name='支付状态')

    class Meta:
        verbose_name = '罚金管理'
        verbose_name_plural = '罚金管理'

    def __str__(self):
        return str(self.id)
