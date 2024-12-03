from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator, RegexValidator


class User(AbstractUser):
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    email = models.EmailField('Электронная почта', unique=True,
                              max_length=254, blank=False,
                              null=False, validators=[EmailValidator()],)
    username = models.CharField(
        'Имя пользователя',
        max_length=150,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message='''Введите корректный юзернейм.
                Разрешены буквы, цифры и символы: @ . + - _''',
            )
        ],
        error_messages={
            'unique': "Пользователь с таким юзернеймом уже существует.",
            'blank': "Это поле обязательно для заполнения.",
        }
    )

    first_name = models.CharField(
        'Имя',
        max_length=150,
        error_messages={
            'blank': "Это поле обязательно для заполнения.",
        }
    )

    last_name = models.CharField(
        'Фамилия',
        max_length=150,
        error_messages={
            'blank': "Это поле обязательно для заполнения.",
        }
    )
    password = models.CharField(
        'Пароль',
        max_length=150,
        blank=False,
        null=False,
    )

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username
