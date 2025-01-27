from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator, RegexValidator
from django.db import models
from django.forms import ValidationError

from recipes.constants import MAX_LENGTH_20, MAX_LENGTH_150, MAX_LENGTH_256


class User(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name', 'password')
    avatar = models.ImageField('Аватар', upload_to='avatars/',
                               blank=True, null=True, )
    email = models.EmailField('Электронная почта', unique=True,
                              max_length=MAX_LENGTH_256, null=False,
                              validators=(EmailValidator(),),)
    username = models.CharField(
        'Имя пользователя',
        max_length=MAX_LENGTH_150,
        unique=True,
        validators=(
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message='''Введите корректный юзернейм.
                Разрешены буквы, цифры и символы: @ . + - _''',
            ),
        ),
        error_messages={
            'unique': "Пользователь с таким юзернеймом уже существует.",
            'blank': "Это поле обязательно для заполнения.",
        }
    )

    first_name = models.CharField(
        'Имя',
        max_length=MAX_LENGTH_150,
        error_messages={
            'blank': "Это поле обязательно для заполнения.",
        }
    )

    last_name = models.CharField(
        'Фамилия',
        max_length=MAX_LENGTH_150,
        error_messages={
            'blank': "Это поле обязательно для заполнения.",
        }
    )

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username[:MAX_LENGTH_20]


class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='subscription',
                             verbose_name='Пользователь')
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name='subscribers',
                               verbose_name='Автор')

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('author', 'user'),
                name='unique_author_user'
            ),
        )
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'

    def clean(self):
        if self.user == self.author:
            raise ValidationError("Нельзя подписаться на самого себя.")

    def __str__(self):
        return f'{self.user.username} - {self.author.username}'
