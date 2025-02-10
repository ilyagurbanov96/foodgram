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
        tags_to_create = []
        existing_tags = set(Tag.objects.values_list('slug', flat=True))

        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = row['name']
                slug = row['slug']

                if slug not in existing_tags:
                    tags_to_create.append(Tag(name=name, slug=slug))
                else:
                    self.stdout.write(self.style.WARNING(
                        f'Тег с slug "{slug}" уже существует.')
                    )

        if tags_to_create:
            Tag.objects.bulk_create(tags_to_create, ignore_conflicts=True)
            for tag in tags_to_create:
                self.stdout.write(self.style.SUCCESS(
                    f'Тег "{tag.name}" успешно добавлен.')
                )
        else:
            self.stdout.write(self.style.NOTICE(
                'Нет новых тегов для добавления.')
            )
