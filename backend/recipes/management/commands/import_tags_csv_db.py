import csv

from django.core.management.base import BaseCommand
from recipes.models import Tag


class Command(BaseCommand):
    help = 'Импорт тегов из CSV файла'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv_file',
            type=str,
            default='data/tags.csv',
            help='Путь к CSV файлу'
        )

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = row['name']
                slug = row['slug']
                tag, created = Tag.objects.get_or_create(
                    name=name,
                    slug=slug
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'''
                                                         Тег "{name}"
                                                         успешно добавлен.'''))
                else:
                    self.stdout.write(self.style.WARNING(f'''
                                                         Тег "{name}"
                                                         уже существует.'''))
