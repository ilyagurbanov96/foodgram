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
        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = row['name']
                slug = row['slug']
                tags_to_create.append(Tag(name=name, slug=slug))
        Tag.objects.bulk_create(tags_to_create, ignore_conflicts=True)
        existing_tags = set(Tag.objects.filter(
            slug__in=[tag.slug for tag in tags_to_create]
        ).values_list('slug', flat=True))
        for tag in existing_tags:
            self.stdout.write(self.style.WARNING(f'''Тег с slug "{tag}"
                                                 уже существует.'''))
        for tag in tags_to_create:
            if tag.slug not in existing_tags:
                self.stdout.write(self.style.SUCCESS(f'''Тег "{tag.name}"
                                                     успешно добавлен.'''))
